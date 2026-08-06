"""Harness Engineering tab: run status banner + live 18-step checklist."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSplitter, QVBoxLayout, QWidget

from app.core.events import PipelineEvent, StepEvent, bus
from app.ui.widgets.issue_sidebar import IssueSidebarWidget
from app.ui.widgets.pipeline_step_list import PipelineStepListWidget
from app.ui.widgets.provider_model_selector import ProviderModelSelectorWidget


class HarnessWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings

        self._project_combo = QComboBox()
        self._project_combo.addItems(settings.projects)

        self._description_label = QLabel(
            "Runs automatically whenever you save a file in a monitored project: an 18-step "
            "sequential check covering secrets, security, dependencies, static analysis, build, "
            "tests, an AI code review, RAG lookup, and an architecture check. If it passes, "
            "Graph Engineering runs next automatically."
        )
        self._description_label.setWordWrap(True)

        self._status_label = QLabel("Waiting for file changes…")

        header = QHBoxLayout()
        header.addWidget(QLabel("Last active project:"))
        header.addWidget(self._project_combo, 1)

        self._model_selector = ProviderModelSelectorWidget(
            "Review model", settings, llm_client, "harness_review_provider", "harness_review_model"
        )

        self._step_list = PipelineStepListWidget("harness")
        self._sidebar = IssueSidebarWidget()
        self._step_list.step_selected.connect(self._sidebar.show_step)

        splitter = QSplitter()
        splitter.addWidget(self._step_list)
        splitter.addWidget(self._sidebar)
        splitter.setSizes([700, 400])

        layout = QVBoxLayout(self)
        layout.addWidget(self._description_label)
        layout.addLayout(header)
        layout.addWidget(self._model_selector)
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

    def _on_step(self, event: StepEvent) -> None:
        self._step_list.on_step_event(event)

    def _on_pipeline(self, event: PipelineEvent) -> None:
        if event.pipeline != "harness":
            return
        idx = self._project_combo.findText(event.project_path)
        if idx >= 0:
            self._project_combo.setCurrentIndex(idx)

        if event.status == "started":
            self._status_label.setText(f"Running Harness Engineering for {event.project_path} …")
        elif event.status == "completed":
            self._status_label.setText(f"Harness Engineering Status: ✔ Completed Successfully — {event.project_path}")
        elif event.status == "failed":
            self._status_label.setText(f"Harness Engineering Status: ✘ {event.summary} — {event.project_path}")
