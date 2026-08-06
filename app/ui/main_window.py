"""Main application window: tabbed dashboard for Harness/Loop/Graph engineering."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from app.config.constants import APP_DISPLAY_NAME
from app.core.autostart import set_autostart
from app.ui.theme import stylesheet_for
from app.ui.widgets.clean_copy_widget import CleanCopyWidget
from app.ui.widgets.dashboard_widget import DashboardWidget
from app.ui.widgets.eval_widget import EvalWidget
from app.ui.widgets.graph_widget import GraphWidget
from app.ui.widgets.harness_widget import HarnessWidget
from app.ui.widgets.log_viewer import LogViewerWidget
from app.ui.widgets.loop_widget import LoopWidget
from app.ui.widgets.memory_widget import MemoryWidget
from app.ui.widgets.rag_widget import RagWidget
from app.ui.widgets.reports_widget import ReportsWidget
from app.ui.widgets.settings_widget import SettingsWidget


class MainWindow(QMainWindow):
    def __init__(self, settings, ollama_client, llm_client, watcher_manager, pipeline_controller=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._ollama_client = ollama_client
        self._llm_client = llm_client
        self._watcher_manager = watcher_manager

        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1200, 800)

        self._tabs = QTabWidget()
        self.dashboard = DashboardWidget(settings, pipeline_controller)
        self.harness_widget = HarnessWidget(settings, llm_client)
        self.loop_widget = LoopWidget(settings, llm_client)
        self.graph_widget = GraphWidget(settings, llm_client)
        self.rag_widget = RagWidget(settings, llm_client)
        self.memory_widget = MemoryWidget()
        self.eval_widget = EvalWidget()
        self.reports_widget = ReportsWidget()
        self.clean_copy_widget = CleanCopyWidget()
        self.settings_widget = SettingsWidget(settings)
        self.log_viewer = LogViewerWidget()

        self._tabs.addTab(self.dashboard, "Dashboard")
        self._tabs.addTab(self.harness_widget, "Harness Engineering")
        self._tabs.addTab(self.loop_widget, "Loop Engineering")
        self._tabs.addTab(self.graph_widget, "Graph Engineering")
        self._tabs.addTab(self.rag_widget, "RAG")
        self._tabs.addTab(self.memory_widget, "Memory")
        self._tabs.addTab(self.eval_widget, "Eval")
        self._tabs.addTab(self.reports_widget, "Reports")
        self._tabs.addTab(self.clean_copy_widget, "Copy Clean Project")
        self._tabs.addTab(self.log_viewer, "Logs")
        self._tabs.addTab(self.settings_widget, "Settings")

        self.setCentralWidget(self._tabs)

        self.dashboard.project_selector.projects_changed.connect(self._on_projects_changed)
        self.settings_widget.settings_changed.connect(self._on_settings_changed)

        self._apply_theme()

    def _on_projects_changed(self, projects: list[str]) -> None:
        self._settings.projects = projects
        self._settings.save()
        self._watcher_manager.set_projects(projects, self._settings.debounce_seconds)
        self.harness_widget.set_projects(projects)
        self.loop_widget.set_projects(projects)
        self.graph_widget.set_projects(projects)

    def _on_settings_changed(self) -> None:
        self._ollama_client.host = self._settings.ollama_host
        self._watcher_manager.set_projects(self._settings.projects, self._settings.debounce_seconds)
        self._apply_theme()
        set_autostart(self._settings.autostart)

    def _apply_theme(self) -> None:
        self.setStyleSheet(stylesheet_for(self._settings.theme))

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
