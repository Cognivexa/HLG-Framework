"""Widget for adding/removing monitored project folders."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget


class ProjectSelectorWidget(QWidget):
    projects_changed = Signal(list)

    def __init__(self, initial_projects: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._list = QListWidget()
        for path in initial_projects or []:
            self._list.addItem(path)

        add_btn = QPushButton("Add Project Folder…")
        add_btn.clicked.connect(self._add_project)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)

        btn_row = QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(btn_row)

    def projects(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def _add_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if path and path not in self.projects():
            self._list.addItem(path)
            self.projects_changed.emit(self.projects())

    def _remove_selected(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self.projects_changed.emit(self.projects())
