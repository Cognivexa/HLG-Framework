"""Graph Engineering tab: manual trigger + live DAG view + step detail list."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.core.events import GraphNodeEvent, PipelineEvent, StepEvent, bus
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background
from app.core.project_context import build_project_context
from app.pipelines.graph.graph_pipeline import run_graph_pipeline
from app.pipelines.graph.orchestrator import route
from app.ui.widgets.graph_view_widget import GraphViewWidget
from app.ui.widgets.issue_sidebar import IssueSidebarWidget
from app.ui.widgets.pipeline_step_list import PipelineStepListWidget
from app.ui.widgets.provider_model_selector import ProviderModelSelectorWidget

logger = get_logger(__name__)


class GraphWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client

        self._project_combo = QComboBox()
        self._project_combo.addItems(settings.projects)

        self._run_btn = QPushButton("Run Graph Engineering Now")
        self._run_btn.clicked.connect(self._run_now)

        self._status_label = QLabel("Routes the same checks Harness Engineering runs as a concurrent agent DAG.")

        header = QHBoxLayout()
        header.addWidget(QLabel("Project:"))
        header.addWidget(self._project_combo, 1)
        header.addWidget(self._run_btn)

        self._model_selector = ProviderModelSelectorWidget(
            "Review model", settings, llm_client, "graph_review_provider", "graph_review_model"
        )

        self._graph_view = GraphViewWidget()
        self._step_list = PipelineStepListWidget("graph")
        self._sidebar = IssueSidebarWidget()
        self._step_list.step_selected.connect(self._sidebar.show_step)

        splitter = QSplitter()
        splitter.addWidget(self._graph_view)
        splitter.addWidget(self._step_list)
        splitter.addWidget(self._sidebar)
        splitter.setSizes([500, 350, 350])

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._model_selector)
        layout.addWidget(self._status_label)
        layout.addWidget(splitter)

        bus.step_updated.connect(self._on_step)
        bus.pipeline_updated.connect(self._on_pipeline)
        bus.graph_node_updated.connect(self._on_node)

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
            return run_graph_pipeline(project_path, files, self._settings, self._llm_client, project=project)

        def done(_ctx) -> None:
            self._run_btn.setEnabled(True)

        def failed(message: str) -> None:
            logger.error("Manual Graph Engineering run crashed: %s", message)
            self._status_label.setText(f"Graph run crashed: {message}")
            self._run_btn.setEnabled(True)

        run_in_background(work, on_finished=done, on_failed=failed)

    def _on_step(self, event: StepEvent) -> None:
        self._step_list.on_step_event(event)

    def _on_node(self, event: GraphNodeEvent) -> None:
        self._graph_view.on_node_event(event)

    def _on_pipeline(self, event: PipelineEvent) -> None:
        if event.pipeline != "graph":
            return
        if event.status == "started":
            self._graph_view.build_layout(event.run_id, route())
            self._status_label.setText(f"Running Graph Engineering for {event.project_path} …")
        elif event.status == "completed":
            self._status_label.setText(f"Graph Engineering Status: ✔ Completed Successfully — {event.summary}")
        elif event.status == "failed":
            self._status_label.setText(f"Graph Engineering Status: ✘ {event.summary}")
        elif event.status == "blocked":
            self._status_label.setText(f"Graph Engineering Status: ⛔ {event.summary}")
