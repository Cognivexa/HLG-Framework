"""Harness Engineering tab: run status banner + live 21-step checklist."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.core.events import PipelineEvent, StepEvent, bus
from app.core.logging_setup import get_logger
from app.core.skills import ensure_starter_skills_file
from app.ui.widgets.issue_sidebar import IssueSidebarWidget
from app.ui.widgets.pipeline_step_list import PipelineStepListWidget
from app.ui.widgets.provider_model_selector import ProviderModelSelectorWidget

logger = get_logger(__name__)


class HarnessWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings

        self._project_combo = QComboBox()
        self._project_combo.addItems(settings.projects)

        self._description_label = QLabel(
            "Runs automatically whenever you save a file in a monitored project: a 21-step "
            "sequential check covering secrets, PII/PHI, security, dependencies, static analysis, "
            "build, tests, an AI code review, RAG lookup, and an architecture check. If it passes, "
            "Graph Engineering runs next automatically."
        )
        self._description_label.setWordWrap(True)

        self._status_label = QLabel("Waiting for file changes…")

        self._skills_btn = QPushButton("Open/Create HARNESS.md")
        self._skills_btn.setToolTip(
            "Project-specific standards and context, automatically included in every AI "
            "review and fix prompt for this project — see docs/HARNESS_LOOP_GRAPH_DEFINITIONS.md. "
            "Creates a starter file with guidance if one doesn't exist yet."
        )
        self._skills_btn.clicked.connect(self._open_skills_file)

        header = QHBoxLayout()
        header.addWidget(QLabel("Last active project:"))
        header.addWidget(self._project_combo, 1)
        header.addWidget(self._skills_btn)

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

    def _open_skills_file(self) -> None:
        project_path = self._project_combo.currentText().strip()
        if not project_path:
            self._status_label.setText("Select a monitored project first.")
            return
        path = ensure_starter_skills_file(Path(project_path))
        try:
            subprocess.run(["code", "-g", str(path)], check=False)
        except FileNotFoundError:
            try:
                os.startfile(str(path))  # noqa: S606 - opening a file with its default app is the intended action
            except OSError:
                logger.warning("Could not open %s with any editor.", path)
                self._status_label.setText(f"Created {path} — open it manually to edit.")

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
