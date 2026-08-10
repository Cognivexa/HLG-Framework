"""Wires FileChangeEvents to Harness pipeline runs, and auto-chains
Harness -> (Loop, if opted in and needed) -> Graph -> Code Review -> Clean-Copy export.

Chain rules:
- Harness passes -> Graph runs automatically next (read-only, always safe).
- Harness fails on ANYTHING (build/test/lint/quality/architecture/docs, or a
  secret/PII/password/PHI finding) and "auto_loop_on_failure" is OFF -> the
  chain stops here; the Loop and Graph tabs are told they're blocked pending
  a manual fix. For a secret/PII finding specifically, the block message
  names exactly what was found (file/line) — see `_secret_block_message`.
- Same failure, "auto_loop_on_failure" ON -> Loop attempts a fix, then
  Harness is re-checked fresh (Loop only tracks its own narrower check set,
  so a full re-check is the only authoritative way to know if *everything*
  actually passes now, not just the subset Loop was watching). If it's still
  failing, the whole Harness -> Loop round repeats — for as long as the
  total failure count keeps trending down. It only gives up once a round
  fails to improve on the previous one `harness_auto_retry_limit` times in a
  row (a *stall*, not a fixed total-attempts budget) — leaving a stale
  "Failed" status as the last thing recorded while Auto Run is still
  actively working on it would be worse than keeps trying as long as it's
  making genuine progress.
- If Graph then passes, Code Review runs: a multi-model panel compares the
  current code against the last-known-good baseline (see app.pipelines.code_review).
  If it finds a real regression and Auto Run is on, the whole
  Harness -> Loop -> Graph round repeats (same stall tracking as above)
  rather than exporting code that just regressed; with Auto Run off, it
  blocks for manual review instead.
- If Graph itself fails (its Final Verification Agent rejects the run), same
  contract as a Harness failure, secret findings included — retried through
  Loop when Auto Run is on, or blocked immediately (with the specific
  file/line detail for a secret finding) when it's off.
- If Code Review then passes (or has no panel configured — a no-op, not a
  block), the project is exported as a clean copy to Downloads (see
  app.export.clean_copy), and a "release" event fires — the single signal
  that Harness, Loop, Graph, and Code Review are ALL green for this change.

Batches rapid file changes within a short window into a single Harness run
per project (a second layer of debounce on top of file_watcher's per-file
debounce) and avoids overlapping runs for the same project — new changes
that arrive while a run is in flight are queued and picked up as soon as it
finishes. "In flight" now spans the *entire* auto-retry chain above, not
just the first Harness call — see `on_settled` threaded through every
stage below, called exactly once when the chain has truly finished
(passed, blocked, or given up), never before.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QTimer

from app.core.events import FileChangeEvent, PipelineEvent, bus
from app.core.file_watcher import ANALYSIS_CHANGE_TYPES
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.pipelines.code_review.code_review_pipeline import run_code_review_pipeline
from app.pipelines.graph.graph_pipeline import run_graph_pipeline
from app.pipelines.harness.harness_pipeline import run_harness_pipeline
from app.pipelines.loop.loop_pipeline import run_loop_pipeline

logger = get_logger(__name__)

# Harness steps (and Graph's combined node) that are Loop-fixable when Auto
# Run is on. Secret/PII/password/PHI findings ARE included here — with Auto
# Run on, Loop attempts them via a specialized "move it to an environment
# variable" fix (see loop_pipeline._FIX_SYSTEM_PROMPT), never a mask/rename
# that would just dodge the scanner. With Auto Run off, the same findings
# still hard-block with a message naming exactly what was found, same as
# every other manual-mode block below — a human decides whether to let Loop
# touch it or fix it by hand.
_LOOP_TRIGGER_STEPS = {
    "build_verification", "unit_tests", "security_scan", "static_analysis", "architecture_validation",
    "documentation_check", "code_quality",
    "scan_api_keys", "scan_secrets", "detect_passwords", "detect_private_keys", "detect_pii", "detect_phi",
}

# Graph Engineering's decision steps (see app/pipelines/steps/graph_steps.py
# _DECISION_STEP_IDS) that mirror the same Loop-fixable categories above —
# used to decide whether a Graph failure is worth retrying through Loop.
_GRAPH_LOOP_RELEVANT_STEPS = {
    "security_scan", "static_analysis", "build_verification", "unit_tests", "documentation_check",
    "architecture_validation", "secret_detection",
}

# Harness's six secret/PII/PHI step ids, and Graph's single combined node —
# used only to build the specific, actionable message naming what was found
# (file/line); NOT to exclude them from Loop's remit (see _LOOP_TRIGGER_STEPS
# above).
_HARNESS_SECRET_STEPS = (
    "scan_api_keys", "scan_secrets", "detect_passwords", "detect_private_keys", "detect_pii", "detect_phi",
)
_GRAPH_SECRET_STEP = "secret_detection"


def _secret_block_message(results: dict, step_ids: tuple[str, ...]) -> str | None:
    """Builds a human-readable, actionable message naming exactly what was
    found and where, or returns None if none of the given steps failed. Used
    for the manual-mode (Auto Run off) block message — with Auto Run on, the
    same finding instead flows into Loop's fix attempt."""
    locations = []
    for step_id in step_ids:
        result = results.get(step_id)
        if result and result.status == "failed":
            locations.extend(result.data.get("locations", []))
    if not locations:
        return None
    described = "; ".join(
        f"{loc.get('category', 'secret')} in {Path(loc['file']).name}:{loc.get('line', '?')}"
        for loc in locations[:5]
    )
    if len(locations) > 5:
        described += f" (+{len(locations) - 5} more)"
    return (
        f"Blocked — potential {described}. Enable Auto Run to have Loop Engineering fix this "
        "automatically (moved to an environment variable, never masked), or rename/remove it by "
        "hand, or confirm it's a false positive, then re-save."
    )


def _stall_step(prev_failures: int | None, current_failures: int, stall: int) -> tuple[int, bool]:
    """Compares this round's failure count to the previous round's. Returns
    (new_stall_streak, improved). A strictly lower count (or no previous
    round yet) resets the streak to 0; anything else extends it. Callers
    give up only once the streak reaches `harness_auto_retry_limit` — i.e.
    that many consecutive rounds in a row with no improvement, not a fixed
    total number of attempts."""
    if prev_failures is None or current_failures < prev_failures:
        return 0, True
    return stall + 1, False


class PipelineController(QObject):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client
        self._pending: dict[str, set[str]] = {}
        self._running: set[str] = set()
        self._timers: dict[str, QTimer] = {}

        bus.file_changed.connect(self._on_file_changed)

    def pending_count(self) -> int:
        return sum(len(files) for files in self._pending.values())

    def running_count(self) -> int:
        return len(self._running)

    def _on_file_changed(self, event: FileChangeEvent) -> None:
        if not self._settings.monitoring_enabled:
            return
        if event.change_type not in ANALYSIS_CHANGE_TYPES:
            return  # deletes/git/build-output events are informational-only (see Dashboard activity feed)
        self._pending.setdefault(event.project_path, set()).add(event.file_path)

        timer = self._timers.get(event.project_path)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda p=event.project_path: self._maybe_run(p))
            self._timers[event.project_path] = timer
        timer.start(self._settings.pipeline_batch_window_ms)

    def _maybe_run(self, project_path: str) -> None:
        if project_path in self._running:
            return  # a run is already in flight; it will pick up newly pending files when done
        files = sorted(self._pending.pop(project_path, set()))
        if not files:
            return
        self._running.add(project_path)

        def on_settled() -> None:
            self._running.discard(project_path)
            if self._pending.get(project_path):
                self._maybe_run(project_path)

        self._run_harness_round(project_path, files, attempt=1, on_settled=on_settled)

    def _run_harness_round(
        self, project_path: str, files: list[str], attempt: int, on_settled: Callable[[], None],
        stall: int = 0, prev_failures: int | None = None, cr_stall: int = 0,
    ) -> None:
        logger.info("Triggering Harness pipeline for %s (%d file(s), attempt %d)", project_path, len(files), attempt)

        def work():
            return run_harness_pipeline(project_path, files, self._settings, self._llm_client)

        def done(harness_ctx) -> None:
            self._continue_chain(project_path, files, harness_ctx, attempt, on_settled, stall, prev_failures, cr_stall)

        def failed(message: str) -> None:
            logger.error("Harness pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=done, on_failed=failed)

    @staticmethod
    def _harness_has_loop_relevant_failure(harness_ctx) -> bool:
        return any(
            harness_ctx.results.get(step_id) and harness_ctx.results[step_id].status == "failed"
            for step_id in _LOOP_TRIGGER_STEPS
        )

    @staticmethod
    def _loop_relevant_failure_count(results: dict) -> int:
        return sum(
            1 for step_id in _LOOP_TRIGGER_STEPS if results.get(step_id) and results[step_id].status == "failed"
        )

    def _continue_chain(
        self, project_path: str, files: list[str], harness_ctx, attempt: int, on_settled: Callable[[], None],
        stall: int = 0, prev_failures: int | None = None, cr_stall: int = 0,
    ) -> None:
        if not self._harness_has_loop_relevant_failure(harness_ctx):
            logger.info("Harness passed for %s — auto-chaining into Graph Engineering", project_path)
            self._run_graph(project_path, files, harness_ctx.project, attempt, on_settled, cr_stall=cr_stall)
            return

        if not self._settings.auto_loop_on_failure:
            logger.info("Harness failed for %s — Loop Engineering blocked (auto-loop is off)", project_path)
            secret_message = _secret_block_message(harness_ctx.results, _HARNESS_SECRET_STEPS)
            loop_summary = secret_message or (
                "Harness Engineering failed — Loop Engineering blocked. Enable Auto Run (Dashboard or "
                "Settings), or fix and re-save to try again."
            )
            bus.pipeline_updated.emit(
                PipelineEvent(pipeline="loop", run_id=harness_ctx.run_id, project_path=project_path, status="blocked", summary=loop_summary)
            )
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="graph", run_id=harness_ctx.run_id, project_path=project_path, status="blocked",
                    summary=secret_message or "Graph Engineering blocked — Harness Engineering must pass first.",
                )
            )
            on_settled()
            return

        current_failures = self._loop_relevant_failure_count(harness_ctx.results)
        new_stall, improved = _stall_step(prev_failures, current_failures, stall)
        if new_stall >= self._settings.harness_auto_retry_limit:
            logger.info(
                "Harness still failing for %s after %d attempt(s), %d consecutive round(s) with no improvement — giving up",
                project_path, attempt, new_stall,
            )
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="graph", run_id=harness_ctx.run_id, project_path=project_path, status="blocked",
                    summary=f"Graph Engineering blocked — still failing after {attempt} attempt(s), "
                    f"{new_stall} in a row with no improvement (Auto Run give-up threshold reached).",
                )
            )
            on_settled()
            return

        logger.info(
            "Auto-triggering Loop Engineering for %s after failed Harness checks (attempt %d, %d failing, stall %d%s)",
            project_path, attempt, current_failures, new_stall, ", improved" if improved else "",
        )

        def work():
            return run_loop_pipeline(project_path, files, self._settings, self._llm_client, project=harness_ctx.project)

        def loop_done(_loop_result) -> None:
            # Re-check with the full Harness step set regardless of what
            # Loop itself believes it resolved — see module docstring.
            self._run_harness_round(
                project_path, files, attempt=attempt + 1, on_settled=on_settled,
                stall=new_stall, prev_failures=current_failures, cr_stall=cr_stall,
            )

        def loop_failed(message: str) -> None:
            logger.error("Loop pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=loop_done, on_failed=loop_failed)

    def _run_graph(
        self, project_path: str, files: list[str], project, attempt: int, on_settled: Callable[[], None],
        stall: int = 0, prev_failures: int | None = None, cr_stall: int = 0,
    ) -> None:
        def work():
            return run_graph_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(graph_ctx) -> None:
            final = graph_ctx.results.get("final_verification")
            if final and final.status == "success":
                self._run_code_review(project_path, files, graph_ctx.project, attempt, on_settled, cr_stall=cr_stall)
                return

            failed_decisions = [
                step_id for step_id in _GRAPH_LOOP_RELEVANT_STEPS
                if graph_ctx.results.get(step_id) and graph_ctx.results[step_id].status == "failed"
            ]
            detail = final.detail if final else "No final verification result."

            if not self._settings.auto_loop_on_failure:
                secret_message = _secret_block_message(graph_ctx.results, (_GRAPH_SECRET_STEP,))
                bus.pipeline_updated.emit(
                    PipelineEvent(
                        pipeline="graph", run_id=graph_ctx.run_id, project_path=project_path, status="blocked",
                        summary=secret_message or f"Graph Engineering blocked — {detail}. Enable Auto Run to retry automatically, or fix and re-save.",
                    )
                )
                on_settled()
                return

            current_failures = len(failed_decisions) or 1  # at least 1: final_verification itself rejected the run
            new_stall, _improved = _stall_step(prev_failures, current_failures, stall)
            if new_stall >= self._settings.harness_auto_retry_limit:
                logger.info(
                    "Graph Engineering still failing for %s, %d consecutive round(s) with no improvement — giving up",
                    project_path, new_stall,
                )
                bus.pipeline_updated.emit(
                    PipelineEvent(
                        pipeline="graph", run_id=graph_ctx.run_id, project_path=project_path, status="blocked",
                        summary=f"Graph Engineering blocked — {detail} ({new_stall} round(s) in a row with no improvement).",
                    )
                )
                on_settled()
                return

            logger.info("Graph Engineering failed for %s — retrying through Harness/Loop (attempt %d)", project_path, attempt + 1)
            self._run_harness_round(
                project_path, files, attempt=attempt + 1, on_settled=on_settled,
                stall=new_stall, prev_failures=current_failures, cr_stall=cr_stall,
            )

        def failed(message: str) -> None:
            logger.error("Graph pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=done, on_failed=failed)

    def _run_code_review(
        self, project_path: str, files: list[str], project, attempt: int, on_settled: Callable[[], None],
        cr_stall: int = 0,
    ) -> None:
        def work():
            return run_code_review_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(cr_result: dict) -> None:
            if cr_result.get("status") in ("success", "skipped"):
                self._export_clean_copy(project_path, on_settled)
                return

            # A real regression was flagged. Same retry contract as a
            # failed Harness check: restart the whole round automatically
            # only if Auto Run is on and it isn't stuck. There's no partial
            # signal here (a regression is binary, not a count that can
            # trend down), so every regression round simply extends this
            # streak by one — this is the one place the streak is still,
            # in effect, a fixed attempt budget rather than true stall
            # detection, because there's nothing gradual to detect.
            if not self._settings.auto_loop_on_failure:
                bus.pipeline_updated.emit(
                    PipelineEvent(
                        pipeline="code_review", run_id=cr_result.get("run_id", ""), project_path=project_path,
                        status="blocked",
                        summary=f"Code Review found a regression: {cr_result.get('detail', '')} — "
                        "enable Auto Run to retry automatically, or fix and re-save.",
                    )
                )
                on_settled()
                return

            new_cr_stall = cr_stall + 1
            if new_cr_stall >= self._settings.harness_auto_retry_limit:
                logger.info(
                    "Code Review still finding regressions for %s, %d consecutive round(s) — giving up",
                    project_path, new_cr_stall,
                )
                bus.pipeline_updated.emit(
                    PipelineEvent(
                        pipeline="code_review", run_id=cr_result.get("run_id", ""), project_path=project_path,
                        status="blocked",
                        summary=f"Code Review still finding regressions after {new_cr_stall} round(s) in a row "
                        "(Auto Run give-up threshold reached).",
                    )
                )
                on_settled()
                return

            logger.info("Code Review found a regression for %s — restarting the chain (attempt %d)", project_path, attempt)
            self._run_harness_round(project_path, files, attempt=attempt + 1, on_settled=on_settled, cr_stall=new_cr_stall)

        def failed(message: str) -> None:
            logger.error("Code Review pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=done, on_failed=failed)

    def _export_clean_copy(self, project_path: str, on_settled: Callable[[], None]) -> None:
        from app.export.clean_copy import export_clean_copy

        def done(result) -> None:
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="release", run_id="", project_path=project_path, status="completed",
                    summary=f"100% passed — Harness, Loop, Graph, and Code Review all green. "
                    f"Clean copy exported to {result.destination} ({result.file_count} file(s)).",
                )
            )
            on_settled()

        def failed(message: str) -> None:
            logger.error("Clean-copy export crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(lambda: export_clean_copy(project_path), on_finished=done, on_failed=failed)
