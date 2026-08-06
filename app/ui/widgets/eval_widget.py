"""Eval tab: the "Eval/LLM-Ops" pillar — deterministic checks (pytest,
ruff, pip-audit; the same result every time for the same code) shown
side by side with LLM-as-judge calls (the AI code review, architecture
validation, and Graph's final verification — a model's opinion, which can
vary), plus the release gate those verdicts feed into.

This deliberately doesn't introduce a second, separate scoring pipeline —
every row here is a real Harness/Loop/Graph step result already flowing
over the event bus and saved in reports/history.py. The Eval tab's job is
just to present the deterministic/judged split explicitly, since that
split is exactly what decides whether a project is safe to auto-export as
a clean copy.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget

from app.core.dashboard_metrics import DETERMINISTIC_STEP_IDS, LLM_JUDGE_STEP_IDS, read_latest_report_steps
from app.core.events import PipelineEvent, bus

_REFRESH_MS = 2000
_STATUS_ICON = {"success": "✅", "failed": "❌", "skipped": "⏭️", "running": "▶", "pending": "•"}


class EvalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        description = QLabel(
            "Deterministic checks (pytest/ruff/pip-audit) and LLM-as-judge calls (AI code review, "
            "architecture validation, Graph's final verification) shown side by side for the most "
            "recent Harness run, plus whether the release gate — Graph Engineering approving the "
            "result — has been reached yet for the current run."
        )
        description.setWordWrap(True)

        columns = QHBoxLayout()
        det_box = QGroupBox("Deterministic checks")
        self._det_list = QListWidget()
        det_layout = QVBoxLayout()
        det_layout.addWidget(self._det_list)
        det_box.setLayout(det_layout)

        judge_box = QGroupBox("LLM-as-judge")
        self._judge_list = QListWidget()
        judge_layout = QVBoxLayout()
        judge_layout.addWidget(self._judge_list)
        judge_box.setLayout(judge_layout)

        columns.addWidget(det_box)
        columns.addWidget(judge_box)

        gate_box = QGroupBox("Release gate")
        self._gate_label = QLabel("Not yet reached — waiting for a Graph Engineering run.")
        self._gate_label.setWordWrap(True)
        gate_layout = QVBoxLayout()
        gate_layout.addWidget(self._gate_label)
        gate_box.setLayout(gate_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addLayout(columns)
        layout.addWidget(gate_box)

        bus.pipeline_updated.connect(self._on_pipeline_updated)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(_REFRESH_MS)
        self._refresh()

    def _on_pipeline_updated(self, event: PipelineEvent) -> None:
        if event.pipeline != "graph":
            return
        if event.status == "completed":
            self._gate_label.setText("PASSED — Graph Engineering approved this run; a clean copy is being exported.")
            self._gate_label.setProperty("role", "banner-ok")
        elif event.status in ("failed", "blocked"):
            self._gate_label.setText(f"BLOCKED — {event.summary or 'Graph Engineering did not approve this run.'}")
            self._gate_label.setProperty("role", "banner-error")
        self._gate_label.style().unpolish(self._gate_label)
        self._gate_label.style().polish(self._gate_label)

    def _refresh(self) -> None:
        steps = read_latest_report_steps("harness")
        self._det_list.clear()
        self._judge_list.clear()
        for step in steps:
            icon = _STATUS_ICON.get(step.get("status"), "•")
            text = f"{icon} {step.get('step_name', step.get('step_id'))}"
            if step.get("step_id") in DETERMINISTIC_STEP_IDS:
                self._det_list.addItem(text)
            elif step.get("step_id") in LLM_JUDGE_STEP_IDS:
                self._judge_list.addItem(text)
        if not steps:
            self._det_list.addItem("(no Harness run yet)")
            self._judge_list.addItem("(no Harness run yet)")
