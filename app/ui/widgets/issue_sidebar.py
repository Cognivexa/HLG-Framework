"""Side panel shown when a step is clicked in a live checklist: classifies
the issue (security / test / build / API error / static analysis / other),
shows its full detail and the actual code line, can jump straight to the
file:line in VS Code, and — for security findings — offers a one-click
"Move to .env" remediation (never automatic; always asks for confirmation
first, see app.pipelines.loop.env_remediation).

Location data comes from StepResult.data["locations"] when the underlying
step populated it (secret scan and lint findings do); everything else falls
back to a best-effort "path.py:line" regex scan over the detail text.
"""
from __future__ import annotations

import re
import subprocess

from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.events import StepEvent
from app.core.logging_setup import get_logger
from app.pipelines.loop.env_remediation import move_secret_to_env

logger = get_logger(__name__)

_SECURITY_STEP_IDS = {
    "scan_api_keys", "scan_secrets", "detect_passwords", "detect_private_keys", "detect_pii", "detect_phi",
    "security_scan", "secret_detection",
}
_TEST_STEP_IDS = {"unit_tests", "integration_tests"}
_BUILD_STEP_IDS = {"build_verification"}
_AI_STEP_IDS = {"ollama_review", "rag_retrieval", "code_improvement"}
_API_ERROR_HINTS = (
    "provider", "api key", "chat call failed", "embed call failed", "unavailable",
    "401", "403", "429", "connection", "timed out",
)
_LOCATION_RE = re.compile(r"([\w.\-/\\]+\.py):(\d+)")


def _classify(event: StepEvent) -> str:
    if event.step_id in _SECURITY_STEP_IDS:
        return "Security issue"
    if event.step_id in _TEST_STEP_IDS:
        return "Unit test failure"
    if event.step_id in _BUILD_STEP_IDS:
        return "Build error"
    if event.step_id in _AI_STEP_IDS:
        detail_lower = (event.detail or "").lower()
        if any(hint in detail_lower for hint in _API_ERROR_HINTS):
            return "API/Provider error"
        return "AI review finding"
    if event.step_id in ("static_analysis", "code_quality", "dependency_analysis"):
        return "Static analysis"
    return "Other"


def _extract_locations(event: StepEvent) -> list[dict]:
    locations = (event.data or {}).get("locations")
    if locations:
        return locations
    matches = _LOCATION_RE.findall(event.detail or "")
    return [{"file": f, "line": int(ln)} for f, ln in matches]


class IssueSidebarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._category_label = QLabel("Click a step to see details.")
        self._category_label.setStyleSheet("font-weight: bold;")
        self._category_label.setWordWrap(True)

        self._detail_view = QTextEdit()
        self._detail_view.setReadOnly(True)

        self._locations_list = QListWidget()
        self._locations_list.itemDoubleClicked.connect(self._open_selected_location)

        self._open_btn = QPushButton("Open in VS Code")
        self._open_btn.clicked.connect(self._open_selected_or_first_location)
        self._open_btn.setEnabled(False)

        self._env_btn = QPushButton("Move to .env…")
        self._env_btn.setToolTip(
            "Move this secret's value into a .env file (created if missing) and replace it in "
            "your code with an environment-variable lookup. Backs up the file first."
        )
        self._env_btn.clicked.connect(self._move_selected_to_env)
        self._env_btn.setEnabled(False)
        self._env_btn.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self._category_label)
        layout.addWidget(self._detail_view)
        layout.addWidget(QLabel("File locations (double-click to open):"))
        layout.addWidget(self._locations_list)
        layout.addWidget(self._open_btn)
        layout.addWidget(self._env_btn)

        self._locations: list[dict] = []
        self._is_security_finding = False

    def show_step(self, event: StepEvent) -> None:
        category = _classify(event)
        self._is_security_finding = category == "Security issue"
        self._category_label.setText(f"[{category}] {event.step_name} — {event.status.upper()}")
        self._detail_view.setPlainText(event.detail or "(no detail)")

        self._locations = _extract_locations(event)
        self._locations_list.clear()
        for loc in self._locations:
            text = f"{loc['file']}:{loc['line']}"
            if loc.get("snippet"):
                text += f"\n    {loc['snippet']}"
            self._locations_list.addItem(text)

        self._open_btn.setEnabled(bool(self._locations))
        self._env_btn.setVisible(self._is_security_finding)
        self._env_btn.setEnabled(self._is_security_finding and bool(self._locations))

    def _selected_or_first_index(self) -> int:
        row = self._locations_list.currentRow()
        return row if row >= 0 else 0

    def _open_location(self, location: dict) -> None:
        file_path = location.get("file")
        line = location.get("line", 1)
        if not file_path:
            return
        try:
            subprocess.run(["code", "-g", f"{file_path}:{line}"], check=False)
        except FileNotFoundError:
            logger.warning("Could not open VS Code — the 'code' CLI isn't on PATH.")
            self._detail_view.append("\n\n(Could not open VS Code — the 'code' command isn't on PATH.)")

    def _open_selected_or_first_location(self) -> None:
        if self._locations:
            self._open_location(self._locations[self._selected_or_first_index()])

    def _open_selected_location(self, item: QListWidgetItem) -> None:
        idx = self._locations_list.row(item)
        if 0 <= idx < len(self._locations):
            self._open_location(self._locations[idx])

    def _move_selected_to_env(self) -> None:
        if not self._locations:
            return
        location = self._locations[self._selected_or_first_index()]
        file_path = location.get("file")
        line = location.get("line")
        if not file_path or not line:
            return

        confirm = QMessageBox.question(
            self,
            "Move secret to .env?",
            f"This will edit {file_path} at line {line} (a backup is kept first), moving the "
            f"value into a .env file in the project root and replacing it with an "
            f"environment-variable lookup.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = move_secret_to_env(file_path, line)
        if result.success:
            QMessageBox.information(self, "Moved to .env", result.message)
        else:
            QMessageBox.warning(self, "Could not move to .env", result.message)
        self._detail_view.append(f"\n\n[{'OK' if result.success else 'FAILED'}] {result.message}")
