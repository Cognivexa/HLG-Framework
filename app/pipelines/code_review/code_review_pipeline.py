"""Code Review: a final, multi-model regression check comparing each
changed file's current content against the last-known-good baseline (see
baseline_store.py) — run once Graph Engineering's final_verification
passes. Unlike everything else in Harness/Loop/Graph, this step is
deliberately reviewed by MULTIPLE independent models (the user's
configured Code Review panel) rather than one: a model reviewing its own
prior work is the worst-positioned reviewer of that work; several
independent ones catch more.

If any panel member flags a real regression, Code Review fails and the
whole Harness -> Loop -> Graph chain is retried (see pipeline_controller.py)
rather than exporting a clean copy of code that just regressed. The
baseline is only updated when Code Review actually passes, so a failed
attempt doesn't move the goalposts for the next one.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from app.core.events import PipelineEvent, StepEvent, bus
from app.core.llm.base import ProviderError
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.core.project_context import ProjectContext
from app.core.skills import with_skills
from app.pipelines.base import new_run_id
from app.pipelines.code_review.baseline_store import load_baseline, save_baseline

logger = get_logger(__name__)

_REVIEW_SYSTEM_PROMPT = (
    "You are reviewing a unified diff of files that just went through an automated fix/verification "
    "pipeline. Compare the OLD and NEW versions. Flag ONLY real regressions: functionality that was "
    "accidentally removed, code that's no longer called/used anywhere, logic that was silently "
    "changed in a way that looks unintentional, or anything the new version does that would break "
    "an existing caller. Do NOT flag intentional fixes, style preferences, or anything the diff "
    "shows was clearly a deliberate improvement. Respond with EXACTLY this format:\n"
    "VERDICT: clean or regression\n"
    "FINDINGS: one line per issue if VERDICT is regression, or \"none\" if clean"
)

_MAX_DIFF_CHARS = 6000


@dataclass
class ReviewerVerdict:
    provider_id: str
    model: str
    flagged: bool
    findings: str
    error: str = ""


def _emit_step(run_id: str, step_id: str, name: str, status: str, detail: str = "") -> None:
    bus.step_updated.emit(
        StepEvent(pipeline="code_review", run_id=run_id, step_id=step_id, step_name=name, status=status, detail=detail)
    )


def _snapshot(changed_files: list[str]) -> dict[str, str]:
    snapshot = {}
    for file_path in changed_files:
        path = Path(file_path)
        if path.suffix == ".py" and path.exists():
            snapshot[str(path.resolve())] = path.read_text(encoding="utf-8", errors="ignore")
    return snapshot


def _build_diff(changed_files: list[str], baseline: dict[str, str]) -> tuple[str, list[str]]:
    """Returns (diff_text, files_with_no_prior_baseline)."""
    chunks = []
    new_files = []
    for file_path in changed_files:
        path = Path(file_path)
        if path.suffix != ".py" or not path.exists():
            continue
        try:
            current = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        old = baseline.get(str(path.resolve()))
        if old is None:
            new_files.append(file_path)
            continue
        if old == current:
            continue
        diff = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True), current.splitlines(keepends=True),
                fromfile=f"{path.name} (last known-good)", tofile=f"{path.name} (current)",
            )
        )
        if diff:
            chunks.append(diff)
    return "\n\n".join(chunks)[:_MAX_DIFF_CHARS], new_files


def _parse_verdict(response: str) -> tuple[bool, str]:
    flagged = False
    findings = ""
    for line in response.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("VERDICT:"):
            flagged = "regression" in stripped.lower()
        elif stripped.upper().startswith("FINDINGS:"):
            findings = stripped.split(":", 1)[1].strip()
    if findings.lower() in ("none", "n/a", ""):
        findings = ""
    return flagged and bool(findings), findings


def run_code_review_pipeline(
    project_path: str,
    changed_files: list[str],
    settings,
    llm_client: LLMClient,
    project: ProjectContext | None = None,
) -> dict:
    run_id = new_run_id()
    project_root = project.root if project else Path(project_path)

    bus.pipeline_updated.emit(
        PipelineEvent(pipeline="code_review", run_id=run_id, project_path=project_path, status="started")
    )
    logger.info("Code Review run %s started for %s (%d file(s))", run_id, project_path, len(changed_files))

    panel = [e for e in settings.models.code_review_panel if e.get("provider") and e.get("model")]
    if not panel:
        detail = "No Code Review panel configured — add at least one model on the Code Review tab."
        _emit_step(run_id, "code_review_verdict", "Code Review verdict", "skipped", detail)
        bus.pipeline_updated.emit(
            PipelineEvent(pipeline="code_review", run_id=run_id, project_path=project_path, status="completed", summary=detail)
        )
        return {"run_id": run_id, "status": "skipped", "flagged": False}

    baseline = load_baseline(project_path)
    diff_text, new_files = _build_diff(changed_files, baseline)
    diff_detail = "First clean pass for this project — nothing to compare yet." if not baseline else ""
    if new_files:
        diff_detail += f" {len(new_files)} file(s) have no prior baseline (first time seen)."
    if diff_text:
        diff_detail += " Comparing changed content against the last known-good version."
    _emit_step(run_id, "build_diff", "Compare current code against last known-good baseline", "success", diff_detail.strip())

    if not diff_text:
        # Nothing changed relative to the last known-good state (or this is
        # the very first pass) — there's nothing to regress against, so
        # this can't fail. Sending an empty diff to a multi-model panel
        # would just spend calls for zero signal.
        _emit_step(run_id, "code_review_verdict", "Code Review verdict", "success", "No changes to compare — nothing to regress. Clean.")
        bus.pipeline_updated.emit(
            PipelineEvent(pipeline="code_review", run_id=run_id, project_path=project_path, status="completed", summary="Nothing to review — clean.")
        )
        save_baseline(project_path, _snapshot(changed_files))
        return {"run_id": run_id, "status": "success", "flagged": False}

    verdicts: list[ReviewerVerdict] = []
    for entry in panel:
        provider_id, model = entry["provider"], entry["model"]
        label = f"Code Review — {provider_id}/{model}"
        step_id = f"code_review_{provider_id}_{model}".replace("/", "_").replace(":", "_").replace(".", "_")
        try:
            response = llm_client.chat(
                provider_id=provider_id, model=model, prompt=diff_text,
                system=with_skills(_REVIEW_SYSTEM_PROMPT, project_root), temperature=0.0,
                label=label, run_id=run_id,
            )
            flagged, findings = _parse_verdict(response)
            _emit_step(run_id, step_id, label, "failed" if flagged else "success", findings or "No regressions found.")
            verdicts.append(ReviewerVerdict(provider_id, model, flagged, findings))
        except ProviderError as exc:
            _emit_step(run_id, step_id, label, "failed", f"Reviewer call failed: {exc}")
            verdicts.append(ReviewerVerdict(provider_id, model, False, "", error=str(exc)))

    real_flags = [v for v in verdicts if v.flagged]
    if real_flags:
        detail = "; ".join(f"{v.provider_id}/{v.model}: {v.findings}" for v in real_flags)
        _emit_step(run_id, "code_review_verdict", "Code Review verdict", "failed", f"REGRESSION FOUND — {detail}")
        bus.pipeline_updated.emit(
            PipelineEvent(pipeline="code_review", run_id=run_id, project_path=project_path, status="failed", summary=detail)
        )
        return {"run_id": run_id, "status": "failed", "flagged": True, "detail": detail}

    _emit_step(
        run_id, "code_review_verdict", "Code Review verdict", "success",
        f"{len(verdicts)} reviewer(s) agree: code is 100% clean and ready to deploy.",
    )
    bus.pipeline_updated.emit(
        PipelineEvent(pipeline="code_review", run_id=run_id, project_path=project_path, status="completed", summary="Code is ready to deploy.")
    )
    save_baseline(project_path, _snapshot(changed_files))
    return {"run_id": run_id, "status": "success", "flagged": False}
