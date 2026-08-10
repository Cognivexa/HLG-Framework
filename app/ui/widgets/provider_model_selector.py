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

If the currently selected provider turns out to be unconfigured or
unreachable, this widget also auto-switches to whichever provider the user
actually has configured (see `_try_next_configured_provider` below) — enter
just one API key anywhere in Settings and every Harness/Loop/Graph/RAG
selector that isn't already working lands on that provider on its own.
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
from app.core.llm.registry import (
    CHAT_FALLBACK_ORDER,
    EMBEDDING_CAPABLE_PROVIDER_IDS,
    EMBEDDING_FALLBACK_ORDER,
    PROVIDERS,
    looks_embedding_only,
    pick_chat_model,
    pick_embedding_model,
)
from app.core.logging_setup import get_logger
from app.core.pipeline_worker import run_in_background

logger = get_logger(__name__)

_DEBOUNCE_MS = 800


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
        self._embeddings_only = embeddings_only
        self._showing_placeholder = False
        self._gated_model_id: str | None = None
        self._tried_fallbacks: set[str] = set()
        self._all_model_names: list[str] = []

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

        # Hidden unless this is a chat/review selector (not embeddings_only)
        # whose currently-resolved model heuristically looks embeddings-only
        # (e.g. "nomic-embed-text") — a model that can never answer a chat
        # prompt, so every call through it would otherwise fail with an
        # opaque "400 Bad Request" and no indication why.
        self._embed_mismatch_notice = QLabel()
        self._embed_mismatch_notice.setWordWrap(True)
        self._embed_mismatch_notice.setStyleSheet("color: #d9a441;")
        embed_row = QHBoxLayout()
        embed_row.setContentsMargins(0, 0, 0, 0)
        embed_row.addSpacing(150)
        embed_row.addWidget(self._embed_mismatch_notice, 1)
        self._embed_mismatch_notice.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(gated_row)
        layout.addLayout(embed_row)

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
        bus.model_fallback_applied.connect(self._on_model_fallback_applied)

        self._update_embed_mismatch_notice()
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
        self._update_embed_mismatch_notice()
        self._fetch_models()

    def _on_model_text_edited(self) -> None:
        self._showing_placeholder = False
        if self.current_provider_id() == "huggingface":
            self._debounce_timer.start(_DEBOUNCE_MS)
        else:
            # No server-side search for these providers — filter what was
            # already fetched instead of leaving the dropdown static.
            self._filter_cached_models()

    def _on_api_keys_changed(self) -> None:
        # A key or the remote-Ollama host was just saved somewhere — if the
        # provider this selector currently has picked needs a key to work,
        # re-check now rather than waiting for a manual Refresh click. If
        # it's still blocked, _fetch_models' own blocker check below will
        # cascade into whichever provider actually has a key configured.
        provider_id = self.current_provider_id()
        provider = PROVIDERS.get(provider_id)
        if provider and provider.requires_api_key:
            self._fetch_models()

    def _on_model_fallback_applied(
        self, provider_attr: str, model_attr: str, new_provider_id: str, new_model: str, reason: str
    ) -> None:
        # Only the selector that actually controls this exact settings pair
        # cares — e.g. Loop's fix-model selector reacts to a Loop fallback,
        # Harness's review selector doesn't. Switching the provider combo
        # here re-triggers _on_provider_changed -> _fetch_models, which lands
        # on `new_model` on its own via the same pick_chat_model() LLMClient
        # just used, so there's no need to force-set model text directly.
        if provider_attr != self._provider_attr or model_attr != self._model_attr:
            return
        logger.info(
            "%s/%s auto-switched to %s after a runtime failure: %s",
            self._provider_attr, self._model_attr, new_provider_id, reason,
        )
        self._tried_fallbacks.clear()
        self._select_by_data(self._provider_combo, new_provider_id)

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
        self._update_embed_mismatch_notice()
        self.changed.emit()

    def _update_embed_mismatch_notice(self) -> None:
        if self._embeddings_only or self._showing_placeholder:
            self._embed_mismatch_notice.hide()
            return
        model = self.current_model()
        if model and looks_embedding_only(model):
            self._embed_mismatch_notice.setText(
                f"⚠ {model!r} looks like an embeddings-only model — chat/review calls through it will "
                "fail. Pick a different model (embedding models belong on the RAG tab's selector only)."
            )
            self._embed_mismatch_notice.show()
        else:
            self._embed_mismatch_notice.hide()

    def _config_blocker(self, provider_id: str) -> str:
        """Returns a placeholder message if this provider can't even be
        attempted yet (missing key/host) — "" if it's configured enough to try."""
        provider = PROVIDERS.get(provider_id)
        if provider is None:
            return "(unknown provider)"
        if provider.requires_api_key and not self._settings.api_keys.get(provider_id):
            return "(enter API key in Settings)"
        # No blocker for ollama_api's remote host: an unset host defaults to
        # Ollama's own cloud API (see app.core.llm.ollama_remote) — only a
        # self-hosted remote server needs it typed in, and that's optional.
        return ""

    def _try_next_configured_provider(self, blocked_provider_id: str, force: bool = False) -> bool:
        """Rather than leaving the user stuck on a provider that's
        unconfigured or unreachable, automatically switch to the next
        untried candidate (from EMBEDDING_FALLBACK_ORDER or
        CHAT_FALLBACK_ORDER, depending on this selector's purpose) that's at
        least configured enough to attempt.

        With force=False (an empty model list, or a fetch that failed
        outright — could just be a transient hiccup), this only kicks in
        while no real model has been chosen yet, so a working deliberate
        choice never gets silently swapped out. With force=True (the
        provider is definitively blocked — e.g. a required key is missing),
        it overrides even an already-selected model, since that selection is
        guaranteed to fail every call regardless. Placeholder text (e.g.
        "(loading models…)") never counts as a real selection either way, so
        a chain of several fallback attempts in one trigger can't get stuck
        on its own leftover placeholder from the previous attempt.

        Returns True if it switched — the switch's own
        _on_provider_changed -> _fetch_models call takes over from there, so
        the caller should stop immediately."""
        has_real_selection = not self._showing_placeholder and bool(self.current_model())
        if not force and has_real_selection:
            return False
        self._tried_fallbacks.add(blocked_provider_id)
        candidates = EMBEDDING_FALLBACK_ORDER if self._embeddings_only else CHAT_FALLBACK_ORDER
        for candidate in candidates:
            if candidate in self._tried_fallbacks:
                continue
            if self._embeddings_only and candidate not in EMBEDDING_CAPABLE_PROVIDER_IDS:
                continue
            if self._config_blocker(candidate):
                continue  # not configured either — leave untried, Settings might fill it in later
            self._select_by_data(self._provider_combo, candidate)
            return True
        return False

    def _pick_default_model(self, provider_id: str, models: list) -> str:
        # Shared with LLMClient's runtime chat-failure fallback (see
        # app.core.llm.registry) so both paths land on the identical model
        # for a given provider/model-list, not two independently-drifting
        # heuristics.
        if self._embeddings_only:
            return pick_embedding_model(provider_id, models)
        return pick_chat_model(provider_id, models)

    def _fetch_models(self) -> None:
        provider_id = self.current_provider_id()
        blocker = self._config_blocker(provider_id)
        if blocker:
            if self._try_next_configured_provider(provider_id, force=True):
                return
            self._set_placeholder(blocker)
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
            if not models and self._try_next_configured_provider(provider_id):
                return
            # Captured before _populate_models resets the flag: True means
            # there was no real selection yet (fresh provider switch, or an
            # API key that just went from missing to present).
            had_no_real_selection = self._showing_placeholder or not self.current_model()
            self._populate_models([m.id for m in models])
            self._update_gated_notice(models)
            if had_no_real_selection:
                default_id = self._pick_default_model(provider_id, models)
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
            if self._try_next_configured_provider(provider_id):
                return
            self._set_placeholder(f"(unavailable: {message[:60]})")
            self._hide_gated_notice()

        run_in_background(work, on_finished=done, on_failed=failed)

    def _populate_models(self, names: list[str]) -> None:
        self._all_model_names = list(names)
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

    def _filter_cached_models(self) -> None:
        """Ollama/OpenAI/Anthropic/Gemini have no server-side search — as the
        user types, narrow the dropdown to the already-fetched list's
        matches client-side instead of doing nothing until Refresh."""
        typed = self.current_model()
        query = typed.strip().lower()
        matches = [n for n in self._all_model_names if query in n.lower()] if query else self._all_model_names
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItems(matches or self._all_model_names)
        self._model_combo.setEditText(typed)
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
            f"⚠ {gated_model.id} is a gated repo on HuggingFace. If you haven't accepted its license "
            "yet, click through below first. If you already have, this notice is informational only "
            "(gating is a repo property HuggingFace's public search always reports, regardless of your "
            "personal access) — a chat call through it can still fail separately if no Inference "
            "Provider actually serves this specific model."
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
