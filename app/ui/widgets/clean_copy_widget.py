"""Copy Clean Project tab: shows clean copies auto-exported to Downloads
once a project's full Harness -> (Loop) -> Graph chain passes
(see app.export.clean_copy)."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.core.events import bus
from app.core.logging_setup import get_logger

logger = get_logger(__name__)


class CleanCopyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = QListWidget()

        open_btn = QPushButton("Open Folder")
        open_btn.clicked.connect(self._open_selected)

        header = QHBoxLayout()
        header.addWidget(QLabel("Clean, tested project copies (auto-exported to Downloads once the full chain passes):"))
        header.addStretch(1)
        header.addWidget(open_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._list)

        bus.clean_copy_ready.connect(self._on_ready)

    def _on_ready(self, source: str, destination: str, file_count: int) -> None:
        item = QListWidgetItem(f"✔ {source}  →  clean & tested — {file_count} file(s) — {destination}")
        item.setData(Qt.ItemDataRole.UserRole, destination)
        self._list.insertItem(0, item)

    def _open_selected(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            try:
                os.startfile(path)
            except OSError as exc:
                logger.warning("Could not open clean-copy folder %s: %s", path, exc)
