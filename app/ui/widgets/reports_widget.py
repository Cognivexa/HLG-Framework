"""Reports tab: browse past run reports (JSON/HTML/PDF) and open their folder."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.core.events import bus
from app.core.logging_setup import get_logger
from app.reports.history import list_runs

logger = get_logger(__name__)


class ReportsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = QListWidget()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        open_btn = QPushButton("Open Report Folder")
        open_btn.clicked.connect(self._open_selected)

        header = QHBoxLayout()
        header.addWidget(QLabel("Past runs (newest first):"))
        header.addStretch(1)
        header.addWidget(refresh_btn)
        header.addWidget(open_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._list)

        bus.report_ready.connect(lambda *_args: self._refresh())
        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        for run in list_runs():
            text = (
                f"[{run.get('pipeline', '?').upper()}] {run.get('overall_status', '?')} — "
                f"{run.get('project_path', '')} — {run.get('generated_at', '')} "
                f"({run.get('passed', 0)} passed / {run.get('failed', 0)} failed / {run.get('skipped', 0)} skipped)"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, run.get("report_dir", ""))
            self._list.addItem(item)

    def _open_selected(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        report_dir = item.data(Qt.ItemDataRole.UserRole)
        if report_dir and os.path.isdir(report_dir):
            try:
                os.startfile(report_dir)  # Windows-only app; opens a folder this app created itself
            except OSError as exc:
                logger.warning("Could not open report folder %s: %s", report_dir, exc)
