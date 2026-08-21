"""Loop Engineering: an iterative generator/evaluator retry loop built on the
Harness pipeline's own step implementations (build_steps, test_steps,
quality_steps, secrets_steps) — the same real checks, just re-run after each
candidate fix.

Safety model: every file this loop is about to overwrite is backed up first
(see app.pipelines.loop.backup). After each attempted fix, the same checks
that failed are re-run; if the result is not strictly better than before, the
file(s) touched this iteration are rolled back from backup. The loop stops
when all checks pass, or once it *stalls* — `retry_limit` consecutive
iterations in a row with no improvement over the one before (not a fixed
total number of iterations: as long as each attempt is fixing at least one
more failing check than the last, it keeps going).

Secret/PII/PHI findings are included in this loop's remit — the fix prompt is
specifically instructed to move a hardcoded value to an environment variable
(never to mask/rename it just to dodge the scanner), and the same
compare-and-rollback safety net applies: a "fix" that doesn't actually reduce
the failure count is rolled back like any other. This loop only ever sees a
secret finding at all when Auto Run is on (see pipeline_controller.py) — with
Auto Run off, the same finding hard-blocks before Loop is triggered, for a
human to review or explicitly enable Auto Run for.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from app.core.agent_catalog import format_selection_summary, select_for_changed_files, with_specialist_guidance
from app.core.events import PipelineEvent, StepEvent, bus
from app.core.llm.base import ProviderError
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.core.project_context import ProjectContext, build_project_context
from app.core.skills import with_skills
from app.pipelines.base import PipelineContext, StepResult, new_run_id
from app.pipelines.loop.architecture_fix import write_missing_scaffolding
from app.pipelines.loop.backup import backup_file, restore_file
from app.pipelines.loop.fix_approval import FixProposal, request_approval
from app.pipelines.loop.memory_gate import run_memory_gate
from app.pipelines.steps import ai_steps, build_steps, doc_steps, quality_steps, secrets_steps, test_steps
from app.reports.report_generator import generate_and_save_reports

logger = get_logger(__name__)

# Loop Engineering IS the debug-and-fix loop, so its fix generation always
# pulls in the debugging-methodology skill regardless of which files
# changed — on top of whatever specialist(s) the changed files themselves
# route to (see app.core.agent_catalog).
_LOOP_ALWAYS_SPECIALISTS = ("debug-like-an-expert",)

_CHECK_STEPS = (
    ("build_verification", build_steps.build_verification),
    ("unit_tests", test_steps.unit_test_execution),
    ("security_scan", quality_steps.security_vulnerability_scan),
    ("static_analysis", quality_steps.static_code_analysis),
    ("code_quality", quality_steps.code_quality_inspection),
    ("architecture_validation", ai_steps.architecture_validation),
    ("documentation_check", doc_steps.documentation_check),
    # Secret/PII/PHI findings — only reached here at all when Auto Run is on
    # (see pipeline_controller.py); with Auto Run off these still hard-block
    # for manual review before Loop ever runs.
    ("secret_detection", secrets_steps.combined_secret_detection),
)

_FIX_BLOCK_RE = re.compile(r"```FILE:\s*(?P<path>[^\n]+?)\s*\n(?P<content>.*?)```", re.DOTALL)

_FIX_SYSTEM_PROMPT = (
    "You are an autonomous code-fixing agent. You will be given the current content of one or "
    "more Python files and a description of build/test/lint/documentation/secret-detection "
    "failures affecting them. If a failure describes low docstring coverage, add clear, accurate "
    "docstrings to the undocumented module(s)/class(es)/function(s) rather than skipping it. If a "
    "failure describes a hardcoded secret/API key/password/PII/PHI finding, fix it by replacing "
    "the literal value with a read from an environment variable (e.g. `os.environ[\"NAME\"]` or "
    "`os.getenv(\"NAME\")`, adding `import os` if it's missing) using a clear, descriptive "
    "variable name — never rename, mask, obfuscate, or delete the literal in a way that only "
    "dodges the scanner without actually removing the hardcoded value, and never invent a "
    "different hardcoded value to replace it with. Return ONLY corrected full file contents, one "
    "per file, using EXACTLY this format for each file you change (and omit any file you are not "
    "changing):\n\n"
    "```FILE: <the exact file path given to you>\n"
    "<the complete corrected file content>\n"
    "```\n\n"
    "Do not include any explanation outside these blocks."
)


def _emit_step(run_id: str, step_id: str, name: str, status: str, detail: str = "") -> None:
    bus.step_updated.emit(
        StepEvent(pipeline="loop", run_id=run_id, step_id=step_id, step_name=name, status=status, detail=detail)
    )


_STREAM_PREVIEW_CHARS = 1500
_STREAM_THROTTLE_SECONDS = 0.15


def _make_stream_emitter(run_id: str, step_id: str, step_name: str):
    """Returns an on_token callback that emits throttled "running" StepEvents
    with the growing response so far — this is what makes Ollama's fix
    generation appear to "type" live in the Loop tab."""
    state = {"chars": [], "last_emit": 0.0}

    def on_token(chunk: str) -> None:
        state["chars"].append(chunk)
        now = time.monotonic()
        if now - state["last_emit"] < _STREAM_THROTTLE_SECONDS:
            return
        state["last_emit"] = now
        text = "".join(state["chars"])
        preview = text if len(text) <= _STREAM_PREVIEW_CHARS else text[:_STREAM_PREVIEW_CHARS] + "…"
        _emit_step(run_id, step_id, step_name, "running", preview)

    return on_token


def _run_checks(project: ProjectContext, changed_files: list[str], settings, llm_client: LLMClient) -> dict[str, StepResult]:
    ctx = PipelineContext(
        run_id="loop-check",
        project_path=str(project.root),
        project=project,
        changed_files=changed_files,
        settings=settings,
        llm_client=llm_client,
    )
    results: dict[str, StepResult] = {}
    for step_id, fn in _CHECK_STEPS:
        try:
            results[step_id] = fn(ctx)
        except Exception as exc:  # noqa: BLE001 - a check must never crash the loop
            results[step_id] = StepResult(step_id=step_id, step_name=step_id, status="failed", detail=str(exc))
    return results


def _failure_count(results: dict[str, StepResult]) -> int:
    return sum(1 for r in results.values() if r.status == "failed")


def _failure_summary(results: dict[str, StepResult]) -> str:
    lines = [f"{step_id}: {r.status} — {r.detail}" for step_id, r in results.items() if r.status == "failed"]
    return "\n".join(lines) or "No failures."


def _parse_fix_blocks(response_text: str) -> dict[str, str]:
    fixes: dict[str, str] = {}
    for match in _FIX_BLOCK_RE.finditer(response_text):
        path = match.group("path").strip()
        content = match.group("content")
        if content.endswith("\n"):
            content = content[:-1]
        fixes[path] = content
    return fixes


def _resolve_target_file(path_hint: str, changed_files: list[str]) -> str | None:
    hint_name = Path(path_hint).name
    for f in changed_files:
        if Path(f).name == hint_name:
            return f
    return None


def _save_loop_report(
    run_id: str,
    project_path: str,
    project: ProjectContext,
    changed_files: list[str],
    settings,
    llm_client: LLMClient,
    results: dict[str, StepResult],
    verdict: StepResult,
) -> None:
    report_ctx = PipelineContext(
        run_id=run_id,
        project_path=project_path,
        project=project,
        changed_files=changed_files,
        settings=settings,
        llm_client=llm_client,
        results={**results, "loop_verdict": verdict},
    )
    generate_and_save_reports("loop", report_ctx)


def run_loop_pipeline(
    project_path: str,
    changed_files: list[str],
    settings,
    llm_client: LLMClient,
    project: ProjectContext | None = None,
) -> dict:
    run_id = new_run_id()
    project = project or build_project_context(project_path)
    stall_limit = max(0, settings.retry_limit)

    bus.pipeline_updated.emit(PipelineEvent(pipeline="loop", run_id=run_id, project_path=project_path, status="started"))
    logger.info("Loop run %s started for %s (%d file(s), stall_limit=%d)", run_id, project_path, len(changed_files), stall_limit)

    _emit_step(run_id, "detect_changed_code", "Detect changed code", "success", f"{len(changed_files)} file(s) in scope.")

    selected_agents = select_for_changed_files(changed_files, always=_LOOP_ALWAYS_SPECIALISTS)
    _emit_step(
        run_id, "select_specialist_agents", "Select specialist agents/skills", "success",
        format_selection_summary(selected_agents, len(changed_files)),
    )

    baseline = _run_checks(project, changed_files, settings, llm_client)

    # Architecture validation (missing tests/, requirements.txt, README) isn't
    # a build/test/lint failure an LLM fix loop can meaningfully reason about
    # — it's missing standard scaffolding. Without this, it would fail the
    # exact same way on every single retry forever, even after every other
    # check goes green. Generate what's missing deterministically, no model
    # call or approval needed since it only ever creates new files.
    arch_result = baseline.get("architecture_validation")
    if arch_result and arch_result.status == "failed":
        created = write_missing_scaffolding(project)
        if created:
            _emit_step(
                run_id, "architecture_scaffolding", "Generate missing project scaffolding", "success",
                f"Created: {', '.join(created)}",
            )
            # has_tests_dir/build_files are snapshotted once at construction,
            # not re-checked live — reusing the stale context here would
            # have every downstream check (this run's and future ones) keep
            # reporting the files we just created as still missing.
            project = build_project_context(project.root)
            baseline = _run_checks(project, changed_files, settings, llm_client)

    baseline_failures = _failure_count(baseline)
    _emit_step(
        run_id, "baseline_summary", "Baseline check results",
        "success" if baseline_failures == 0 else "failed", _failure_summary(baseline),
    )

    if baseline_failures == 0:
        verdict = StepResult(step_id="loop_verdict", step_name="Loop Engineering verdict", status="success", detail="No failures to fix — checks already pass.")
        _emit_step(run_id, verdict.step_id, verdict.step_name, verdict.status, verdict.detail)
        bus.pipeline_updated.emit(
            PipelineEvent(pipeline="loop", run_id=run_id, project_path=project_path, status="completed", summary="Nothing to fix.")
        )
        _save_loop_report(run_id, project_path, project, changed_files, settings, llm_client, baseline, verdict)
        return {"run_id": run_id, "iterations": 0, "final_failures": 0}

    fix_model = settings.models.loop_fix_model
    if not fix_model:
        verdict = StepResult(step_id="loop_verdict", step_name="Loop Engineering verdict", status="skipped", detail="No Loop fix model selected in Settings.")
        _emit_step(run_id, verdict.step_id, verdict.step_name, verdict.status, verdict.detail)
        bus.pipeline_updated.emit(
            PipelineEvent(pipeline="loop", run_id=run_id, project_path=project_path, status="failed", summary="No fix model configured.")
        )
        _save_loop_report(run_id, project_path, project, changed_files, settings, llm_client, baseline, verdict)
        return {"run_id": run_id, "iterations": 0, "final_failures": baseline_failures}

    current_results = baseline
    current_failures = baseline_failures
    iteration = 0
    stall = 0
    previous_note = ""

    while current_failures > 0 and stall < stall_limit:
        iteration += 1
        i = iteration

        build_detail = current_results.get("build_verification")
        _emit_step(run_id, f"analyze_build_errors_{i}", f"[Iteration {i}] Analyze build errors", "success", build_detail.detail if build_detail else "n/a")

        test_detail = current_results.get("unit_tests")
        _emit_step(run_id, f"analyze_test_failures_{i}", f"[Iteration {i}] Analyze test failures", "success", test_detail.detail if test_detail else "n/a")

        send_step_id = f"send_to_ollama_{i}"
        send_step_name = f"[Iteration {i}] Send failures to Ollama"
        _emit_step(run_id, send_step_id, send_step_name, "running", "Waiting for the model to start responding…")
        sources = []
        for f in changed_files:
            path = Path(f)
            if path.suffix == ".py" and path.exists():
                sources.append(f"FILE: {f}\n{path.read_text(encoding='utf-8', errors='ignore')}")
        prompt = (
            f"Failures:\n{_failure_summary(current_results)}\n\n"
            + (f"Note: {previous_note}\n\n" if previous_note else "")
            + "Current file contents:\n\n" + "\n\n".join(sources)
        )
        try:
            response = llm_client.chat(
                provider_id=settings.models.loop_fix_provider, model=fix_model, prompt=prompt,
                system=with_skills(with_specialist_guidance(_FIX_SYSTEM_PROMPT, selected_agents), project.root),
                temperature=settings.temperature,
                on_token=_make_stream_emitter(run_id, send_step_id, send_step_name),
                label=f"Loop Fix Generation (iteration {i})", run_id=run_id,
                settings_attrs=("loop_fix_provider", "loop_fix_model"),
            )
            _emit_step(run_id, send_step_id, send_step_name, "success", "Received a candidate fix.")
        except ProviderError as exc:
            _emit_step(run_id, send_step_id, send_step_name, "failed", str(exc))
            break

        fixes = _parse_fix_blocks(response)
        resolved = {}
        for hint, content in fixes.items():
            target = _resolve_target_file(hint, changed_files)
            if target:
                resolved[target] = content

        if not resolved:
            _emit_step(
                run_id, f"generate_fix_{i}", f"[Iteration {i}] Generate improved implementation", "failed",
                "Model returned no usable fix for the changed files.",
            )
            previous_note = "Your previous response didn't use the required ```FILE: <path> block format. Please follow it exactly."
            continue
        _emit_step(run_id, f"generate_fix_{i}", f"[Iteration {i}] Generate improved implementation", "success", f"{len(resolved)} file(s) proposed.")

        proposal_files = {}
        for target, content in resolved.items():
            target_path = Path(target)
            old_content = target_path.read_text(encoding="utf-8", errors="ignore") if target_path.exists() else ""
            proposal_files[target] = {"old": old_content, "new": content}

        auto_apply = settings.auto_apply_fixes
        if auto_apply:
            _emit_step(
                run_id, f"apply_fix_{i}", f"[Iteration {i}] Auto-applying fix", "running",
                "Auto Run is enabled — applying this candidate fix without manual review.",
            )
        else:
            _emit_step(
                run_id, f"apply_fix_{i}", f"[Iteration {i}] Waiting for your review…", "running",
                "A candidate fix is ready — review each file below and Accept or Reject it individually "
                "in the panel that opened.",
            )
        # Per-file, not all-or-nothing: with Auto Run off, the user decides
        # file by file which of this iteration's proposed changes to write —
        # e.g. accept a source-code fix but reject an accompanying test
        # change, or vice versa — instead of one blanket Accept/Reject
        # covering everything the model touched this round.
        approved_files = request_approval(
            FixProposal(run_id=run_id, step_id=f"apply_fix_{i}", iteration=i, files=proposal_files),
            auto_apply=auto_apply,
        )
        accepted_targets = [target for target in resolved if approved_files.get(target)]
        rejected_targets = [target for target in resolved if not approved_files.get(target)]

        if not accepted_targets:
            _emit_step(
                run_id, f"apply_fix_{i}", f"[Iteration {i}] Apply fixes safely", "skipped",
                "Fix rejected during review — asking the model to try a different approach.",
            )
            previous_note = "Your previous fix was rejected during human review. Try a meaningfully different approach."
            continue

        backed_up = []
        for target in accepted_targets:
            backup_file(project.root, run_id, Path(target))
            Path(target).write_text(resolved[target], encoding="utf-8")
            backed_up.append(target)

        apply_detail = f"Applied to {len(backed_up)} file(s) (backed up first)."
        rejection_note = ""
        if rejected_targets:
            rejected_names = ", ".join(Path(t).name for t in rejected_targets)
            apply_detail += f" Skipped (rejected): {rejected_names}."
            rejection_note = (
                f" The user rejected your proposed changes to: {rejected_names} — "
                "consider a different approach for those if they're still relevant."
            )
        _emit_step(run_id, f"apply_fix_{i}", f"[Iteration {i}] Apply fixes safely", "success", apply_detail)

        new_results = _run_checks(project, changed_files, settings, llm_client)
        _emit_step(run_id, f"rebuild_{i}", f"[Iteration {i}] Build project again", new_results["build_verification"].status, new_results["build_verification"].detail)
        _emit_step(run_id, f"retest_{i}", f"[Iteration {i}] Run unit tests again", new_results["unit_tests"].status, new_results["unit_tests"].detail)
        _emit_step(run_id, f"security_rescan_{i}", f"[Iteration {i}] Run security scans again", new_results["security_scan"].status, new_results["security_scan"].detail)
        _emit_step(run_id, f"static_rescan_{i}", f"[Iteration {i}] Run static analysis again", new_results["static_analysis"].status, new_results["static_analysis"].detail)
        _emit_step(run_id, f"quality_rescan_{i}", f"[Iteration {i}] Run code quality inspection again", new_results["code_quality"].status, new_results["code_quality"].detail)
        _emit_step(run_id, f"secret_rescan_{i}", f"[Iteration {i}] Scan for secrets/PII again", new_results["secret_detection"].status, new_results["secret_detection"].detail)

        new_failures = _failure_count(new_results)
        if new_failures < current_failures:
            _emit_step(
                run_id, f"compare_results_{i}", f"[Iteration {i}] Compare previous and new results", "success",
                f"Improved: {current_failures} -> {new_failures} failing check(s). Keeping this fix.",
            )
            current_results = new_results
            current_failures = new_failures
            previous_note = ""
            stall = 0
        else:
            for target in backed_up:
                restore_file(project.root, run_id, Path(target))
            stall += 1
            _emit_step(
                run_id, f"compare_results_{i}", f"[Iteration {i}] Compare previous and new results", "failed",
                f"Not improved ({current_failures} -> {new_failures}). Rolled back this iteration's changes. "
                f"({stall}/{stall_limit} attempt(s) in a row with no improvement.)",
            )
            previous_note = "Your previous fix did not improve results and was rolled back. Try a different approach."

        if rejection_note:
            previous_note = (previous_note + rejection_note) if previous_note else rejection_note.strip()

    if current_failures == 0:
        verdict = StepResult(
            step_id="loop_verdict", step_name="Loop Engineering verdict", status="success",
            detail=f"All checks passed after {iteration} iteration(s).",
        )
        status, summary = "completed", f"Fixed after {iteration} iteration(s)."
        if iteration > 0:
            try:
                gate = run_memory_gate(run_id, project_path, _failure_summary(baseline), changed_files, settings, llm_client)
            except Exception as exc:  # noqa: BLE001 - the gate must never take down an otherwise-successful run
                logger.exception("Memory gate crashed for run %s", run_id)
                gate = None
                gate_status, gate_detail = "skipped", f"Memory gate crashed: {exc}"
            if gate is not None:
                gate_status = "success" if gate.remember else "skipped"
                gate_detail = gate.lesson if gate.remember else (gate.reason or "Not generalizable enough to remember.")
            _emit_step(run_id, "memory_gate", "Memory gate: remember this fix?", gate_status, gate_detail)
    else:
        verdict = StepResult(
            step_id="loop_verdict", step_name="Loop Engineering verdict", status="failed",
            detail=f"{current_failures} check(s) still failing after {iteration} iteration(s) — stalled "
            f"({stall} in a row with no improvement).",
        )
        status, summary = "failed", f"{current_failures} check(s) still failing — stalled after {stall} non-improving attempt(s) in a row."
    _emit_step(run_id, verdict.step_id, verdict.step_name, verdict.status, verdict.detail)

    bus.pipeline_updated.emit(PipelineEvent(pipeline="loop", run_id=run_id, project_path=project_path, status=status, summary=summary))
    logger.info("Loop run %s %s: %s", run_id, status, summary)
    _save_loop_report(run_id, project_path, project, changed_files, settings, llm_client, current_results, verdict)
    return {"run_id": run_id, "iterations": iteration, "final_failures": current_failures}
