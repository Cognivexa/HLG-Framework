"""Modal dialog Loop Engineering uses to get explicit user approval before
writing any proposed fix to disk. Shown from LoopWidget in response to
`bus.fix_proposed`; the background Loop thread is blocked (see
app.pipelines.loop.fix_approval) until this dialog is closed."""
from __future__ import annotations

import difflib

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget


class FixReviewDialog(QDialog):
    def __init__(self, files: dict[str, dict[str, str]], iteration: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Review proposed fix — Loop Engineering iteration {iteration}")
        self.resize(900, 650)

        self._checkboxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Loop Engineering wants to apply this fix. Review each file's diff below — every file "
                "starts checked; uncheck any you want to skip — then click Apply Selected (a backup is "
                "kept first). Reject All skips every file and asks the model to try a different approach."
            )
        )

        tabs = QTabWidget()
        for path, versions in files.items():
            diff_text = "".join(
                difflib.unified_diff(
                    versions["old"].splitlines(keepends=True),
                    versions["new"].splitlines(keepends=True),
                    fromfile=f"{path} (before)",
                    tofile=f"{path} (proposed)",
                )
            ) or "(no textual difference detected)"

            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(4, 4, 4, 4)

            checkbox = QCheckBox(f"Apply this change to {path}")
            checkbox.setChecked(True)
            self._checkboxes[path] = checkbox
            tab_layout.addWidget(checkbox)

            view = QPlainTextEdit(diff_text)
            view.setReadOnly(True)
            tab_layout.addWidget(view)

            tab_label = path.replace("\\", "/").rsplit("/", 1)[-1]
            tabs.addTab(tab_widget, tab_label)
        layout.addWidget(tabs)

        buttons = QDialogButtonBox()
        buttons.addButton("Apply Selected", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Reject All", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def approved_files(self) -> dict[str, bool]:
        """Call after exec(): {path: True} for files that were both checked
        and the dialog closed via Apply Selected; every file maps to False
        if Reject All was clicked (or the dialog was otherwise dismissed
        without accepting)."""
        if self.result() != QDialog.DialogCode.Accepted:
            return dict.fromkeys(self._checkboxes, False)
        return {path: checkbox.isChecked() for path, checkbox in self._checkboxes.items()}
