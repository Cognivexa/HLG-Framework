"""Searchable, level-filterable live log viewer backed by the shared log ring buffer."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from app.core.events import LogEvent, bus
from app.core.logging_setup import LOG_RING_BUFFER

LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs…")
        self._search.textChanged.connect(self._refresh)

        self._level = QComboBox()
        self._level.addItems(LEVELS)
        self._level.currentTextChanged.connect(self._refresh)

        controls = QHBoxLayout()
        controls.addWidget(self._search, 1)
        controls.addWidget(self._level)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self._text)

        bus.log_emitted.connect(self._on_log)
        self._refresh()

    def _matches(self, event: LogEvent) -> bool:
        level_ok = self._level.currentText() == "ALL" or event.level == self._level.currentText()
        query = self._search.text().lower()
        text_ok = query in event.message.lower() if query else True
        return level_ok and text_ok

    def _refresh(self) -> None:
        lines = [f"{e.timestamp} [{e.level}] {e.message}" for e in LOG_RING_BUFFER if self._matches(e)]
        self._text.setPlainText("\n".join(lines))
        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_log(self, event: LogEvent) -> None:
        if self._matches(event):
            self._text.appendPlainText(f"{event.timestamp} [{event.level}] {event.message}")
