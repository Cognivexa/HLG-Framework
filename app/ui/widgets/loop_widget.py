"""Loop Engineering tab: manual trigger + live iterative retry checklist.

Loop Engineering can also fire automatically after a failed Harness run, and
skip the Accept/Reject review entirely, when "Auto Run" is on (Dashboard or
Settings) — this tab is always available for an explicit, on-demand run
regardless of that setting.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.core.events import PipelineEvent, StepEvent, bus
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.core.project_context import build_project_context
from app.pipelines.loop.fix_approval import resolve_approval
from app.pipelines.loop.loop_pipeline import run_loop_pipeline
from app.ui.widgets.fix_review_dialog import FixReviewDialog
from app.ui.widgets.issue_sidebar import IssueSidebarWidget
from app.ui.widgets.pipeline_step_list import PipelineStepListWidget
from app.ui.widgets.provider_model_selector import ProviderModelSelectorWidget

logger = get_logger(__name__)


class LoopWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client

        self._project_combo = QComboBox()
        self._project_combo.addItems(settings.projects)

        self._run_btn = QPushButton("Run Loop Engineering Now")
        self._run_btn.clicked.connect(self._run_now)

        self._status_label = QLabel(
            "Runs the current build/test/lint checks and, on failure, asks the fix model for a "
            "correction. With Auto Run off, you'll be shown a diff to Accept or Reject before "
            "anything is written; with Auto Run on, fixes apply automatically. Either way, every "
            "change is backed up first and it retries until checks pass or the retry limit is reached."
        )
        self._status_label.setWordWrap(True)

        header = QHBoxLayout()
        header.addWidget(QLabel("Project:"))
        header.addWidget(self._project_combo, 1)
        header.addWidget(self._run_btn)

        self._model_selector = ProviderModelSelectorWidget(
            "Fix model", settings, llm_client, "loop_fix_provider", "loop_fix_model"
        )

        self._step_list = PipelineStepListWidget("loop")
        self._sidebar = IssueSidebarWidget()
        self._step_list.step_selected.connect(self._sidebar.show_step)

        splitter = QSplitter()
        splitter.addWidget(self._step_list)
        splitter.addWidget(self._sidebar)
        splitter.setSizes([700, 400])

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._model_selector)
        layout.addWidget(self._status_label)
        layout.addWidget(splitter)

        bus.step_updated.connect(self._on_step)
        bus.pipeline_updated.connect(self._on_pipeline)
        bus.fix_proposed.connect(self._on_fix_proposed)

    def set_projects(self, projects: list[str]) -> None:
        current = self._project_combo.currentText()
        self._project_combo.clear()
        self._project_combo.addItems(projects)
        if current:
            idx = self._project_combo.findText(current)
            if idx >= 0:
                self._project_combo.setCurrentIndex(idx)

    def _run_now(self) -> None:
        project_path = self._project_combo.currentText().strip()
        if not project_path:
            self._status_label.setText("Select a monitored project first.")
            return
        self._run_btn.setEnabled(False)

        def work():
            project = build_project_context(project_path)
            files = [str(f) for f in project.source_files if f.suffix == ".py"]
            return run_loop_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(_result) -> None:
            self._run_btn.setEnabled(True)

        def failed(message: str) -> None:
            logger.error("Manual Loop Engineering run crashed: %s", message)
            self._status_label.setText(f"Loop run crashed: {message}")
            self._run_btn.setEnabled(True)

        run_in_background(work, on_finished=done, on_failed=failed)

    def _on_fix_proposed(self, proposal) -> None:
        # Make sure the window is actually visible for this — the app may be
        # minimized to the tray, or the auto-chain may have triggered this
        # while the user is on a different tab.
        window = self.window()
        window.show()
        window.raise_()
        window.activateWindow()

        dialog = FixReviewDialog(proposal.files, proposal.iteration, parent=self)
        dialog.exec()
        resolve_approval(proposal.run_id, proposal.step_id, dialog.approved_files())

    def _on_step(self, event: StepEvent) -> None:
        self._step_list.on_step_event(event)

    def _on_pipeline(self, event: PipelineEvent) -> None:
        if event.pipeline != "loop":
            return
        if event.status == "started":
            self._status_label.setText(f"Running Loop Engineering for {event.project_path} …")
        elif event.status == "completed":
            self._status_label.setText(f"Loop Engineering Status: ✔ Completed Successfully — {event.summary}")
        elif event.status == "failed":
            self._status_label.setText(f"Loop Engineering Status: ✘ {event.summary}")
        elif event.status == "blocked":
            self._status_label.setText(f"Loop Engineering Status: ⛔ {event.summary}")
