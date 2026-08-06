"""Provider + Model selector, embedded directly on the Harness/Loop/Graph/RAG
tabs. Selecting a provider auto-fetches that provider's model list (once a
required API key/host is present); for HuggingFace, typing in the model
field re-searches the public Hub (debounced) since HF has no per-account
model list, only search. Writes straight through to AppSettings on every
change — there's no separate "Save" step for these, unlike the rest of
Settings.

Every instance of this widget also listens for `bus.api_keys_changed`
(Settings saved a key/host) and `bus.ollama_status_changed` (the app's
15-second local-Ollama poll) so a model list that was empty because a key
wasn't entered yet — or because Ollama hadn't finished starting up — fills
in on its own, without the user having to remember to click Refresh.
"""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.events import bus
from app.core.llm.registry import EMBEDDING_CAPABLE_PROVIDER_IDS, PROVIDERS
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background

logger = get_logger(__name__)

_DEBOUNCE_MS = 800

# Applied automatically once a provider has a usable model list and this
# selector doesn't have a model chosen yet (a fresh provider switch, or an
# API key that just went from missing to present) — a solid, verified-working
# general-purpose default per provider, so the user isn't left picking a
# model by hand before Harness/Loop/Graph can run. Providers with no entry
# here fall back to whatever model the fetch happened to return first.
_DEFAULT_MODELS: dict[str, str] = {
    "huggingface": "deepseek-ai/DeepSeek-V4-Flash-0731",
}


class ProviderModelSelectorWidget(QWidget):
    changed = Signal()

    def __init__(
        self,
        label: str,
        settings,
        llm_client,
        provider_attr: str,
        model_attr: str,
        embeddings_only: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._settings = settings
        self._llm_client = llm_client
        self._provider_attr = provider_attr
        self._model_attr = model_attr
        self._showing_placeholder = False
        self._gated_model_id: str | None = None

        self._provider_combo = QComboBox()
        provider_ids = EMBEDDING_CAPABLE_PROVIDER_IDS if embeddings_only else tuple(PROVIDERS.keys())
        for pid in provider_ids:
            self._provider_combo.addItem(PROVIDERS[pid].display_name, pid)
        self._select_by_data(self._provider_combo, getattr(settings.models, provider_attr, "ollama_local"))

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        current_model = getattr(settings.models, model_attr, "")
        if current_model:
            self._model_combo.addItem(current_model)
            self._model_combo.setCurrentText(current_model)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(70)

        label_widget = QLabel(label)
        label_widget.setFixedWidth(150)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(label_widget)
        row.addWidget(self._provider_combo, 1)
        row.addWidget(self._model_combo, 1)
        row.addWidget(self._refresh_btn)

        # Hidden unless the currently-resolved model is gated (HuggingFace
        # only) — a repo owner requiring a license click-through before the
        # model can actually be used for inference.
        self._gated_notice = QLabel()
        self._gated_notice.setWordWrap(True)
        self._gated_notice.setStyleSheet("color: #d9a441;")
        self._gated_open_btn = QPushButton("Acknowledge license…")
        self._gated_open_btn.setFixedWidth(150)
        gated_row = QHBoxLayout()
        gated_row.setContentsMargins(0, 0, 0, 0)
        gated_row.addSpacing(150)
        gated_row.addWidget(self._gated_notice, 1)
        gated_row.addWidget(self._gated_open_btn)
        self._gated_notice.hide()
        self._gated_open_btn.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(gated_row)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._fetch_models)

        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self._model_combo.editTextChanged.connect(self._on_model_text_edited)
        self._model_combo.currentTextChanged.connect(self._persist)
        self._refresh_btn.clicked.connect(self._fetch_models)
        self._gated_open_btn.clicked.connect(self._open_gated_license_page)

        bus.api_keys_changed.connect(self._on_api_keys_changed)
        bus.ollama_status_changed.connect(self._on_ollama_status_changed)

        self._fetch_models()

    @staticmethod
    def _select_by_data(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def current_provider_id(self) -> str:
        return self._provider_combo.currentData()

    def current_model(self) -> str:
        return self._model_combo.currentText()

    def _on_provider_changed(self) -> None:
        # Persist the provider immediately, but NOT the model text still
        # showing from the previous provider — that stale pairing (e.g. a
        # HuggingFace model id saved alongside "ollama_local") is exactly
        # what made chat calls silently target the wrong backend and 404.
        # Clear it here; _fetch_models' done() below assigns and persists a
        # real, valid model for the new provider once the list is in.
        setattr(self._settings.models, self._provider_attr, self.current_provider_id())
        setattr(self._settings.models, self._model_attr, "")
        self._settings.save()
        self.changed.emit()
        # A fetch can take several seconds (first-connection network/DNS
        # latency, a slow provider, ...) — an empty combo for that whole
        # stretch reads as broken, not loading. This also correctly leaves
        # `_showing_placeholder=True` for search_text's placeholder guard.
        self._set_placeholder("(loading models…)")
        self._hide_gated_notice()
        self._fetch_models()

    def _on_model_text_edited(self) -> None:
        self._showing_placeholder = False
        if self.current_provider_id() == "huggingface":
            self._debounce_timer.start(_DEBOUNCE_MS)

    def _on_api_keys_changed(self) -> None:
        # A key or the remote-Ollama host was just saved somewhere — if it's
        # relevant to whichever provider this selector currently has picked,
        # pick up the change without waiting for a manual Refresh click.
        provider_id = self.current_provider_id()
        provider = PROVIDERS.get(provider_id)
        if provider and (provider.requires_api_key or provider_id == "ollama_api"):
            self._fetch_models()

    def _on_ollama_status_changed(self, available: bool, models: list[str]) -> None:
        if self.current_provider_id() != "ollama_local":
            return
        if available:
            self._populate_models(models)
        else:
            self._set_placeholder("(Ollama not detected — is it running?)")

    def _persist(self) -> None:
        setattr(self._settings.models, self._provider_attr, self.current_provider_id())
        setattr(self._settings.models, self._model_attr, self.current_model())
        self._settings.save()
        self.changed.emit()

    def _fetch_models(self) -> None:
        provider_id = self.current_provider_id()
        provider = PROVIDERS.get(provider_id)
        if provider is None:
            return
        if provider.requires_api_key and not self._settings.api_keys.get(provider_id):
            self._set_placeholder("(enter API key in Settings)")
            return
        if provider_id == "ollama_api" and not self._settings.ollama_remote_host:
            self._set_placeholder("(set remote host in Settings)")
            return

        # Never send placeholder text we set ourselves (e.g. "(enter API key
        # in Settings)") to HuggingFace's search as if it were a real query.
        search_text = "" if self._showing_placeholder else self.current_model()
        search_text = search_text if provider_id == "huggingface" else ""

        def work():
            return self._llm_client.list_models(provider_id, search=search_text)

        def done(models) -> None:
            # Guard against a slow fetch for a provider the user has since
            # switched away from landing late and clobbering the combo.
            if self.current_provider_id() != provider_id:
                return
            # Captured before _populate_models resets the flag: True means
            # there was no real selection yet (fresh provider switch, or an
            # API key that just went from missing to present).
            had_no_real_selection = self._showing_placeholder or not self.current_model()
            self._populate_models([m.id for m in models])
            self._update_gated_notice(models)
            if had_no_real_selection:
                default_id = _DEFAULT_MODELS.get(provider_id) or (models[0].id if models else "")
                if default_id:
                    # Don't rely on currentTextChanged to trigger the save:
                    # if the fetch happens to auto-select this exact model
                    # already (e.g. it's simply first in a popularity-sorted
                    # browse list), the text never actually changes, so Qt
                    # never fires the signal and nothing would get persisted.
                    self._model_combo.setCurrentText(default_id)
                    self._persist()

        def failed(message: str) -> None:
            if self.current_provider_id() != provider_id:
                return
            logger.warning("Could not fetch models for %s: %s", provider_id, message)
            self._set_placeholder(f"(unavailable: {message[:60]})")
            self._hide_gated_notice()

        run_in_background(work, on_finished=done, on_failed=failed)

    def _populate_models(self, names: list[str]) -> None:
        was_placeholder = self._showing_placeholder
        self._showing_placeholder = False
        current = "" if was_placeholder else self.current_model()
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItems(names)
        if current:
            idx = self._model_combo.findText(current)
            self._model_combo.setCurrentIndex(idx) if idx >= 0 else self._model_combo.setCurrentText(current)
        self._model_combo.blockSignals(False)

    def _set_placeholder(self, text: str) -> None:
        self._showing_placeholder = True
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItem(text)
        self._model_combo.blockSignals(False)

    def _update_gated_notice(self, models) -> None:
        gated_model = next((m for m in models if getattr(m, "gated", False)), None)
        if gated_model is None:
            self._hide_gated_notice()
            return
        self._gated_model_id = gated_model.id
        self._gated_notice.setText(
            f"⚠ {gated_model.id} requires accepting a license "
            "on HuggingFace before it can be used."
        )
        self._gated_notice.show()
        self._gated_open_btn.show()

    def _hide_gated_notice(self) -> None:
        self._gated_model_id = None
        self._gated_notice.hide()
        self._gated_open_btn.hide()

    def _open_gated_license_page(self) -> None:
        if self._gated_model_id:
            webbrowser.open(f"https://huggingface.co/{self._gated_model_id}")
