"""Top-level dashboard: Ollama status, live system/pipeline metrics, running
agents, monitored project selection, and recent activity."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.dashboard_metrics import build_snapshot
from app.core.events import FileChangeEvent, PipelineEvent, bus
from app.ui.widgets.project_selector import ProjectSelectorWidget

_METRICS_REFRESH_MS = 2000

_ACTIVITY_ICONS = {
    "created": "🆕",
    "modified": "✏️",
    "renamed": "🔀",
    "deleted": "🗑️",
    "git_changed": "🔧",
    "build_output_changed": "📦",
}

_PIPELINE_LABELS = {"harness": "Harness Engineering", "loop": "Loop Engineering", "graph": "Graph Engineering"}
_HEALTH_ROLE = {"Good": "banner-ok", "Warning": "banner-error", "Critical": "banner-error", "Unknown": ""}


class DashboardWidget(QWidget):
    def __init__(self, settings, pipeline_controller=None, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._pipeline_controller = pipeline_controller
        self._active_runs: dict[tuple[str, str], str] = {}  # (pipeline, project_path) -> status

        self._description_label = QLabel(
            "Add a project folder below to start monitoring it. Every save automatically runs "
            "Harness Engineering, then Graph Engineering if it passes. Loop Engineering (it edits "
            "your files) only runs automatically — and only auto-applies its fixes — when Auto Run "
            "is on below."
        )
        self._description_label.setWordWrap(True)

        auto_run_box = QGroupBox("Auto Run")
        self._auto_run_check = QCheckBox(
            "OFF: review/Accept every fix yourself.  ON: fully hands-off "
            "(auto-fix, auto-test, auto-chain into Graph Engineering) — "
            "you'll only see a final \"100% clean\" notification."
        )
        font = self._auto_run_check.font()
        font.setBold(True)
        self._auto_run_check.setFont(font)
        self._auto_run_check.setChecked(settings.auto_run_enabled)
        self._auto_run_check.toggled.connect(self._on_auto_run_toggled)
        bus.auto_run_changed.connect(self._on_auto_run_changed_elsewhere)
        auto_run_layout = QVBoxLayout()
        auto_run_layout.addWidget(self._auto_run_check)
        auto_run_box.setLayout(auto_run_layout)

        self._release_banner = QLabel("No fully clean run yet for any monitored project.")
        self._release_banner.setWordWrap(True)

        self._ollama_banner = QLabel("Ollama: checking…")
        self._ollama_banner.setProperty("role", "banner-error")

        self._web_banner = QLabel(
            f"Live browser mirror: http://127.0.0.1:{settings.web_dashboard_port}"
            if settings.web_dashboard_enabled else "Live browser mirror is disabled in Settings."
        )
        open_browser_btn = QPushButton("Open in Browser")
        open_browser_btn.clicked.connect(self._open_web_dashboard)
        web_row = QHBoxLayout()
        web_row.addWidget(self._web_banner, 1)
        web_row.addWidget(open_browser_btn)

        metrics_box = QGroupBox("Live Metrics")
        metrics_form = QFormLayout()
        self._cpu_label = QLabel("—")
        self._mem_label = QLabel("—")
        self._queue_label = QLabel("—")
        self._running_label = QLabel("—")
        self._completed_label = QLabel("—")
        self._failed_label = QLabel("—")
        self._security_score_label = QLabel("—")
        self._quality_score_label = QLabel("—")
        self._build_status_label = QLabel("—")
        self._test_status_label = QLabel("—")
        self._health_label = QLabel("—")
        metrics_form.addRow("CPU usage", self._cpu_label)
        metrics_form.addRow("Memory usage", self._mem_label)
        metrics_form.addRow("Queue size", self._queue_label)
        metrics_form.addRow("Running jobs", self._running_label)
        metrics_form.addRow("Completed jobs", self._completed_label)
        metrics_form.addRow("Failed jobs", self._failed_label)
        metrics_form.addRow("Security score", self._security_score_label)
        metrics_form.addRow("Code quality score", self._quality_score_label)
        metrics_form.addRow("Latest build status", self._build_status_label)
        metrics_form.addRow("Latest test status", self._test_status_label)
        metrics_form.addRow("Overall engineering health", self._health_label)
        metrics_box.setLayout(metrics_form)

        running_box = QGroupBox("Currently Running")
        self._running_list = QListWidget()
        running_layout = QVBoxLayout()
        running_layout.addWidget(self._running_list)
        running_box.setLayout(running_layout)

        ai_box = QGroupBox("Latest AI Decision")
        self._ai_decision_label = QLabel("—")
        self._ai_decision_label.setWordWrap(True)
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(self._ai_decision_label)
        ai_box.setLayout(ai_layout)

        projects_box = QGroupBox("Monitored Projects")
        self.project_selector = ProjectSelectorWidget(settings.projects)
        projects_layout = QVBoxLayout()
        projects_layout.addWidget(self.project_selector)
        projects_box.setLayout(projects_layout)

        activity_box = QGroupBox("Recent Activity")
        self._activity_list = QListWidget()
        activity_layout = QVBoxLayout()
        activity_layout.addWidget(self._activity_list)
        activity_box.setLayout(activity_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(self._description_label)
        layout.addWidget(auto_run_box)
        layout.addWidget(self._release_banner)
        layout.addWidget(self._ollama_banner)
        layout.addLayout(web_row)
        layout.addWidget(metrics_box)
        layout.addWidget(running_box)
        layout.addWidget(ai_box)
        layout.addWidget(projects_box)
        layout.addWidget(activity_box)

        bus.ollama_status_changed.connect(self._on_ollama_status)
        bus.file_changed.connect(self._on_file_changed)
        bus.pipeline_updated.connect(self._on_pipeline_updated)

        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._refresh_metrics)
        self._metrics_timer.start(_METRICS_REFRESH_MS)
        self._refresh_metrics()

    def set_pipeline_controller(self, pipeline_controller) -> None:
        self._pipeline_controller = pipeline_controller

    def _on_auto_run_toggled(self, checked: bool) -> None:
        self._settings.set_auto_run(checked)
        bus.auto_run_changed.emit(checked)

    def _on_auto_run_changed_elsewhere(self, checked: bool) -> None:
        self._auto_run_check.blockSignals(True)
        self._auto_run_check.setChecked(checked)
        self._auto_run_check.blockSignals(False)

    def _open_web_dashboard(self) -> None:
        if not self._settings.web_dashboard_enabled:
            self._web_banner.setText("Live browser mirror is disabled in Settings — enable it and restart to use this.")
            return
        webbrowser.open(f"http://127.0.0.1:{self._settings.web_dashboard_port}")

    def _on_ollama_status(self, available: bool, models: list[str]) -> None:
        if available:
            self._ollama_banner.setText(f"Ollama: connected ({len(models)} models available)")
            self._ollama_banner.setProperty("role", "banner-ok")
        else:
            self._ollama_banner.setText("Ollama: not detected — start Ollama locally to enable AI features")
            self._ollama_banner.setProperty("role", "banner-error")
        self._ollama_banner.style().unpolish(self._ollama_banner)
        self._ollama_banner.style().polish(self._ollama_banner)

    def _on_file_changed(self, event: FileChangeEvent) -> None:
        icon = _ACTIVITY_ICONS.get(event.change_type, "•")
        self._activity_list.insertItem(0, f"{icon} [{event.change_type}] {event.file_path}")
        while self._activity_list.count() > 200:
            self._activity_list.takeItem(self._activity_list.count() - 1)

    def _on_pipeline_updated(self, event: PipelineEvent) -> None:
        if event.pipeline == "release" and event.status == "completed":
            self._release_banner.setText(f"✅ 100% PASSED — {event.project_path}: {event.summary}")
            self._release_banner.setProperty("role", "banner-ok")
            self._release_banner.style().unpolish(self._release_banner)
            self._release_banner.style().polish(self._release_banner)
            return

        key = (event.pipeline, event.project_path)
        if event.status == "started":
            self._active_runs[key] = event.status
        else:
            self._active_runs.pop(key, None)
        self._refresh_running_list()

    def _refresh_running_list(self) -> None:
        self._running_list.clear()
        for (pipeline, project_path) in self._active_runs:
            label = _PIPELINE_LABELS.get(pipeline, pipeline)
            self._running_list.addItem(f"▶ {label} — {project_path}")
        if not self._active_runs:
            self._running_list.addItem("(idle)")

    def _refresh_metrics(self) -> None:
        snapshot = build_snapshot(self._pipeline_controller)
        self._cpu_label.setText(f"{snapshot.cpu_percent:.0f}%")
        self._mem_label.setText(f"{snapshot.memory_percent:.0f}%")
        self._queue_label.setText(str(snapshot.queue_size))
        self._running_label.setText(str(snapshot.running_count))
        self._completed_label.setText(str(snapshot.completed_jobs))
        self._failed_label.setText(str(snapshot.failed_jobs))
        self._security_score_label.setText(f"{snapshot.security_score}%" if snapshot.security_score is not None else "—")
        self._quality_score_label.setText(f"{snapshot.quality_score}%" if snapshot.quality_score is not None else "—")
        self._build_status_label.setText(snapshot.build_status)
        self._test_status_label.setText(snapshot.test_status)
        self._ai_decision_label.setText(snapshot.latest_ai_decision or "—")

        self._health_label.setText(snapshot.overall_health)
        role = _HEALTH_ROLE.get(snapshot.overall_health, "")
        self._health_label.setProperty("role", role)
        self._health_label.style().unpolish(self._health_label)
        self._health_label.style().polish(self._health_label)
