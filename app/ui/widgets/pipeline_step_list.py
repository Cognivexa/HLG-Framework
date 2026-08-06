"""Reusable live checklist: shows an ordered list of pipeline steps with status
icons, updated in real time from StepEvents on the bus. Clicking a row emits
`step_selected` with that step's latest StepEvent, for the issue sidebar."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from app.core.events import StepEvent

_ICONS = {
    "pending": "⏳",
    "running": "▶",
    "success": "✅",
    "failed": "❌",
    "skipped": "⏭",
}


class PipelineStepListWidget(QListWidget):
    step_selected = Signal(object)  # StepEvent

    def __init__(self, pipeline_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.pipeline_name = pipeline_name
        self._current_run_id: str | None = None
        self._rows: dict[str, int] = {}
        self._events: dict[str, StepEvent] = {}
        self.itemClicked.connect(self._on_item_clicked)

    def on_step_event(self, event: StepEvent) -> None:
        if event.pipeline != self.pipeline_name:
            return
        if event.run_id != self._current_run_id:
            self._start_new_run(event.run_id)

        self._events[event.step_id] = event
        icon = _ICONS.get(event.status, "•")
        label = f"{icon} {event.step_name}"
        if event.detail:
            label += f" — {event.detail}"

        row = self._rows.get(event.step_id)
        if row is None:
            self.addItem(QListWidgetItem(label))
            self._rows[event.step_id] = self.count() - 1
        else:
            self.item(row).setText(label)

    def _start_new_run(self, run_id: str) -> None:
        self._current_run_id = run_id
        self.clear()
        self._rows.clear()
        self._events.clear()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        for step_id, r in self._rows.items():
            if r == row:
                event = self._events.get(step_id)
                if event:
                    self.step_selected.emit(event)
                return
