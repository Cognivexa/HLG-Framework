"""Wires FileChangeEvents to Harness pipeline runs, and auto-chains
Harness -> (Loop, if opted in and needed) -> Graph -> Clean-Copy export.

Chain rules:
- Harness passes -> Graph runs automatically next (read-only, always safe).
- Harness fails, "auto_loop_on_failure" is OFF -> the chain stops here; the
  Loop and Graph tabs are told they're blocked pending a manual fix.
- Harness fails, "auto_loop_on_failure" is ON -> Loop attempts a fix, then
  Harness is re-checked fresh (Loop only tracks its own narrower check set —
  build/test/security/static/architecture — so a full re-check is the only
  authoritative way to know if *everything* actually passes now, not just
  the subset Loop was watching). If it's still failing, the whole
  Harness -> Loop round repeats — up to `harness_auto_retry_limit` rounds
  total for one triggered change — rather than leaving a stale "Failed"
  status as the last thing recorded while Auto Run is still actively
  working on it. Only once that round limit is exhausted does the chain
  stop and mark Graph blocked.
- If Graph then passes, the project is exported as a clean copy to
  Downloads (see app.export.clean_copy).

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

from typing import Callable

from PySide6.QtCore import QObject, QTimer

from app.core.events import FileChangeEvent, PipelineEvent, bus
from app.core.file_watcher import ANALYSIS_CHANGE_TYPES
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.pipelines.graph.graph_pipeline import run_graph_pipeline
from app.pipelines.harness.harness_pipeline import run_harness_pipeline
from app.pipelines.loop.loop_pipeline import run_loop_pipeline

logger = get_logger(__name__)

# Only these Harness steps' failures are within Loop Engineering's remit to
# attempt an autonomous fix for (build/test/lint/scaffolding) — a failed
# secret scan or a flagged AI code review should never trigger an
# auto-generated code "fix", and Harness is otherwise considered to have
# passed for chaining purposes.
_LOOP_TRIGGER_STEPS = {"build_verification", "unit_tests", "security_scan", "static_analysis", "architecture_validation"}


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

    def _run_harness_round(self, project_path: str, files: list[str], attempt: int, on_settled: Callable[[], None]) -> None:
        logger.info("Triggering Harness pipeline for %s (%d file(s), attempt %d)", project_path, len(files), attempt)

        def work():
            return run_harness_pipeline(project_path, files, self._settings, self._llm_client)

        def done(harness_ctx) -> None:
            self._continue_chain(project_path, files, harness_ctx, attempt, on_settled)

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

    def _continue_chain(
        self, project_path: str, files: list[str], harness_ctx, attempt: int, on_settled: Callable[[], None]
    ) -> None:
        if not self._harness_has_loop_relevant_failure(harness_ctx):
            logger.info("Harness passed for %s — auto-chaining into Graph Engineering", project_path)
            self._run_graph(project_path, files, harness_ctx.project, on_settled)
            return

        if not self._settings.auto_loop_on_failure:
            logger.info("Harness failed for %s — Loop Engineering blocked (auto-loop is off)", project_path)
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="loop", run_id=harness_ctx.run_id, project_path=project_path, status="blocked",
                    summary="Harness Engineering failed — Loop Engineering blocked. Enable Auto Run (Dashboard or Settings), or fix and re-save to try again.",
                )
            )
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="graph", run_id=harness_ctx.run_id, project_path=project_path, status="blocked",
                    summary="Graph Engineering blocked — Harness Engineering must pass first.",
                )
            )
            on_settled()
            return

        if attempt >= self._settings.harness_auto_retry_limit:
            logger.info(
                "Harness still failing for %s after %d attempt(s) — giving up (Auto Run retry limit reached)",
                project_path, attempt,
            )
            bus.pipeline_updated.emit(
                PipelineEvent(
                    pipeline="graph", run_id=harness_ctx.run_id, project_path=project_path, status="blocked",
                    summary=f"Graph Engineering blocked — still failing after {attempt} attempt(s) (Auto Run retry limit reached).",
                )
            )
            on_settled()
            return

        logger.info("Auto-triggering Loop Engineering for %s after failed Harness checks (attempt %d)", project_path, attempt)

        def work():
            return run_loop_pipeline(project_path, files, self._settings, self._llm_client, project=harness_ctx.project)

        def loop_done(_loop_result) -> None:
            # Re-check with the full Harness step set regardless of what
            # Loop itself believes it resolved — see module docstring.
            self._run_harness_round(project_path, files, attempt=attempt + 1, on_settled=on_settled)

        def loop_failed(message: str) -> None:
            logger.error("Loop pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=loop_done, on_failed=loop_failed)

    def _run_graph(self, project_path: str, files: list[str], project, on_settled: Callable[[], None]) -> None:
        def work():
            return run_graph_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(graph_ctx) -> None:
            final = graph_ctx.results.get("final_verification")
            if final and final.status == "success":
                self._export_clean_copy(project_path, on_settled)
            else:
                on_settled()

        def failed(message: str) -> None:
            logger.error("Graph pipeline crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(work, on_finished=done, on_failed=failed)

    def _export_clean_copy(self, project_path: str, on_settled: Callable[[], None]) -> None:
        from app.export.clean_copy import export_clean_copy

        def done(_result) -> None:
            on_settled()

        def failed(message: str) -> None:
            logger.error("Clean-copy export crashed for %s: %s", project_path, message)
            on_settled()

        run_in_background(lambda: export_clean_copy(project_path), on_finished=done, on_failed=failed)
