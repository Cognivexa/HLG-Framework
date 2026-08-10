"""Code Review tab: the final multi-model regression check. Runs
automatically after Graph Engineering passes (see pipeline_controller.py) —
comparing the current code against the last-known-good baseline for each
project, using every model configured in the panel below. A real regression
found here restarts the whole Harness -> Loop -> Graph chain automatically
when Auto Run is on; a clean pass here is what finally exports a clean copy
and says the code is ready to deploy.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.core.events import PipelineEvent, StepEvent, bus
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.core.project_context import build_project_context
from app.pipelines.code_review.code_review_pipeline import run_code_review_pipeline
from app.ui.widgets.code_review_panel_widget import CodeReviewPanelWidget
from app.ui.widgets.issue_sidebar import IssueSidebarWidget
from app.ui.widgets.pipeline_step_list import PipelineStepListWidget

logger = get_logger(__name__)


class CodeReviewWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client

        self._project_combo = QComboBox()
        self._project_combo.addItems(settings.projects)

        self._run_btn = QPushButton("Run Code Review Now")
        self._run_btn.clicked.connect(self._run_now)

        self._description_label = QLabel(
            "Runs automatically once Graph Engineering passes: every model in the panel below "
            "independently compares the current code against the last known-good version, looking "
            "for anything that was accidentally removed, broken, or silently changed. A real "
            "regression restarts Harness -> Loop -> Graph automatically (with Auto Run on); a clean "
            "pass exports the project as a clean copy and marks it ready to deploy."
        )
        self._description_label.setWordWrap(True)

        self._status_label = QLabel("Waiting for Graph Engineering to pass…")

        header = QHBoxLayout()
        header.addWidget(QLabel("Project:"))
        header.addWidget(self._project_combo, 1)
        header.addWidget(self._run_btn)

        self._panel_widget = CodeReviewPanelWidget(settings, llm_client)

        self._step_list = PipelineStepListWidget("code_review")
        self._sidebar = IssueSidebarWidget()
        self._step_list.step_selected.connect(self._sidebar.show_step)

        splitter = QSplitter()
        splitter.addWidget(self._step_list)
        splitter.addWidget(self._sidebar)
        splitter.setSizes([700, 400])

        layout = QVBoxLayout(self)
        layout.addWidget(self._description_label)
        layout.addLayout(header)
        layout.addWidget(self._panel_widget)
        layout.addWidget(self._status_label)
        layout.addWidget(splitter)

        bus.step_updated.connect(self._on_step)
        bus.pipeline_updated.connect(self._on_pipeline)

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
            return run_code_review_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(_result) -> None:
            self._run_btn.setEnabled(True)

        def failed(message: str) -> None:
            logger.error("Manual Code Review run crashed: %s", message)
            self._status_label.setText(f"Code Review run crashed: {message}")
            self._run_btn.setEnabled(True)

        run_in_background(work, on_finished=done, on_failed=failed)

    def _on_step(self, event: StepEvent) -> None:
        self._step_list.on_step_event(event)

    def _on_pipeline(self, event: PipelineEvent) -> None:
        if event.pipeline != "code_review":
            return
        idx = self._project_combo.findText(event.project_path)
        if idx >= 0:
            self._project_combo.setCurrentIndex(idx)

        if event.status == "started":
            self._status_label.setText(f"Running Code Review for {event.project_path} …")
        elif event.status == "completed":
            self._status_label.setText(f"Code Review Status: ✔ {event.summary} — {event.project_path}")
        elif event.status == "failed":
            self._status_label.setText(f"Code Review Status: ✘ REGRESSION FOUND — {event.summary} — {event.project_path}")
        elif event.status == "blocked":
            self._status_label.setText(f"Code Review Status: ⛔ {event.summary} — {event.project_path}")
