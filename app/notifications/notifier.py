"""Desktop notifications for pipeline lifecycle events and key check results.

Only a small set of step IDs trigger a toast (not all 18+ Harness steps) to
avoid spamming the user on every run — one aggregate security-relevant step
per pipeline, plus build/test outcomes.
"""
from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon

from app.core.events import PipelineEvent, StepEvent, bus
from app.ui.tray import TrayIcon

_PIPELINE_LABELS = {"harness": "Harness Engineering", "loop": "Loop Engineering", "graph": "Graph Engineering"}

# "security_scan" (ruff-based) and "secret_detection" (Graph's combined
# aggregator) cover the security-relevant signal without also firing once per
# Harness sub-step (scan_api_keys/scan_secrets/detect_passwords/detect_private_keys).
_SECURITY_STEP_IDS = {"security_scan", "secret_detection"}
_BUILD_STEP_IDS = {"build_verification"}
_TEST_STEP_IDS = {"unit_tests"}


class Notifier:
    def __init__(self, tray: TrayIcon):
        self._tray = tray
        bus.pipeline_updated.connect(self._on_pipeline)
        bus.step_updated.connect(self._on_step)
        bus.clean_copy_ready.connect(self._on_clean_copy_ready)

    def _on_pipeline(self, event: PipelineEvent) -> None:
        label = _PIPELINE_LABELS.get(event.pipeline, event.pipeline)
        if event.status == "started":
            self._tray.notify(f"{label} started", event.project_path)
        elif event.status == "completed":
            self._tray.notify(f"{label} completed", event.summary or "Completed successfully.")
        elif event.status == "failed":
            self._tray.notify(
                f"{label} failed", event.summary or "One or more checks failed.",
                icon=QSystemTrayIcon.MessageIcon.Warning,
            )
        elif event.status == "blocked":
            self._tray.notify(
                f"{label} blocked", event.summary or "Blocked pending a prior stage.",
                icon=QSystemTrayIcon.MessageIcon.Warning,
            )

    def _on_step(self, event: StepEvent) -> None:
        if event.status not in ("success", "failed"):
            return

        if event.step_id in _SECURITY_STEP_IDS and event.status == "failed":
            self._tray.notify("Security issue found", f"{event.step_name}: {event.detail}"[:200], icon=QSystemTrayIcon.MessageIcon.Warning)
        elif event.step_id in _BUILD_STEP_IDS:
            if event.status == "success":
                self._tray.notify("Build succeeded", event.detail[:200])
            else:
                self._tray.notify("Build failed", event.detail[:200], icon=QSystemTrayIcon.MessageIcon.Critical)
        elif event.step_id in _TEST_STEP_IDS:
            if event.status == "success":
                self._tray.notify("Tests passed", event.detail[:200])
            else:
                self._tray.notify("Tests failed", event.detail[:200], icon=QSystemTrayIcon.MessageIcon.Warning)

    def _on_clean_copy_ready(self, source: str, destination: str, file_count: int) -> None:
        # A clean copy only ever gets exported once the full Harness -> (Loop,
        # if it ran) -> Graph chain has passed — this is the definitive
        # "everything is done" signal, regardless of whether Auto Run drove
        # the whole thing hands-off or the user approved each step manually.
        self._tray.notify(
            "100% Clean — Ready to Deploy",
            f"No errors, no security issues, all tests passing. {file_count} file(s) exported to {destination}"[:200],
        )
