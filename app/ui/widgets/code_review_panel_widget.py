"""Multi-model panel picker for the Code Review tab: unlike
ProviderModelSelectorWidget (one provider+model pair written straight to a
single settings field), this manages a *list* of (provider, model) reviewer
entries on `settings.models.code_review_panel` — Code Review deliberately
asks several independent models to look at the same diff rather than one
model reviewing its own prior work.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.llm.registry import PROVIDERS
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background

logger = get_logger(__name__)


class _AddReviewerDialog(QDialog):
    def __init__(self, llm_client, parent=None):
        super().__init__(parent)
        self._llm_client = llm_client
        self.setWindowTitle("Add Code Review reviewer")

        self._provider_combo = QComboBox()
        for pid, provider in PROVIDERS.items():
            self._provider_combo.addItem(provider.display_name, pid)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(70)

        model_row = QHBoxLayout()
        model_row.addWidget(self._model_combo, 1)
        model_row.addWidget(self._refresh_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Provider:"))
        layout.addWidget(self._provider_combo)
        layout.addWidget(QLabel("Model:"))
        layout.addLayout(model_row)
        layout.addWidget(buttons)

        self._provider_combo.currentIndexChanged.connect(self._fetch_models)
        self._refresh_btn.clicked.connect(self._fetch_models)
        self._fetch_models()

    def current_provider_id(self) -> str:
        return self._provider_combo.currentData()

    def current_model(self) -> str:
        return self._model_combo.currentText().strip()

    def _fetch_models(self) -> None:
        provider_id = self.current_provider_id()
        self._model_combo.clear()
        self._model_combo.addItem("(loading models…)")

        def work():
            return self._llm_client.list_models(provider_id)

        def done(models) -> None:
            if self.current_provider_id() != provider_id:
                return
            self._model_combo.clear()
            self._model_combo.addItems([m.id for m in models])

        def failed(message: str) -> None:
            if self.current_provider_id() != provider_id:
                return
            logger.warning("Could not fetch models for %s: %s", provider_id, message)
            self._model_combo.clear()
            self._model_combo.addItem(f"(unavailable: {message[:60]})")

        run_in_background(work, on_finished=done, on_failed=failed)


class CodeReviewPanelWidget(QWidget):
    def __init__(self, settings, llm_client, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client

        self._list = QListWidget()
        self._add_btn = QPushButton("Add Reviewer…")
        self._remove_btn = QPushButton("Remove Selected")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Code Review panel — every model below independently reviews each diff:"))
        layout.addWidget(self._list)
        layout.addLayout(btn_row)

        self._add_btn.clicked.connect(self._add_reviewer)
        self._remove_btn.clicked.connect(self._remove_selected)

        self._refresh_list()

    def _refresh_list(self) -> None:
        self._list.clear()
        for entry in self._settings.models.code_review_panel:
            provider = PROVIDERS.get(entry.get("provider", ""))
            provider_label = provider.display_name if provider else entry.get("provider", "?")
            self._list.addItem(f"{provider_label} — {entry.get('model', '?')}")

    def _add_reviewer(self) -> None:
        dialog = _AddReviewerDialog(self._llm_client, self)
        if dialog.exec() != QDialog.Accepted:
            return
        provider_id, model = dialog.current_provider_id(), dialog.current_model()
        if not provider_id or not model or model.startswith("("):
            return
        self._settings.models.code_review_panel.append({"provider": provider_id, "model": model})
        self._settings.save()
        self._refresh_list()

    def _remove_selected(self) -> None:
        rows = sorted((self._list.row(item) for item in self._list.selectedItems()), reverse=True)
        if not rows:
            return
        for row in rows:
            del self._settings.models.code_review_panel[row]
        self._settings.save()
        self._refresh_list()
