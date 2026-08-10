"""Settings tab: Ollama connection, cloud provider API keys, theme, retry
limit, autostart, and other behavior. Per-pipeline model selection lives on
each of the Harness/Loop/Graph/RAG tabs themselves (ProviderModelSelectorWidget)
— this tab only holds what's shared across all of them.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.events import bus
from app.core.llm.registry import PROVIDERS

_KEY_SAVE_DEBOUNCE_MS = 500


class SettingsWidget(QWidget):
    settings_changed = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings

        connection_box = QGroupBox("Ollama Connection")
        self._host_edit = QLineEdit(settings.ollama_host)
        self._remote_host_edit = QLineEdit(settings.ollama_remote_host)
        self._remote_host_edit.setPlaceholderText(
            "Leave blank to use Ollama's own cloud API (https://ollama.com) with the key below — "
            "only set this if you're pointing at your own self-hosted remote Ollama server instead"
        )
        self._remote_host_timer = QTimer(self)
        self._remote_host_timer.setSingleShot(True)
        self._remote_host_timer.timeout.connect(self._save_remote_host)
        self._remote_host_edit.textChanged.connect(lambda: self._remote_host_timer.start(_KEY_SAVE_DEBOUNCE_MS))
        connection_form = QFormLayout()
        connection_form.addRow("Local host", self._host_edit)
        connection_form.addRow("Remote host", self._remote_host_edit)
        connection_box.setLayout(connection_form)

        api_keys_box = QGroupBox("Cloud Provider API Keys")
        api_keys_form = QFormLayout()
        self._api_key_edits: dict[str, QLineEdit] = {}
        self._key_save_timers: dict[str, QTimer] = {}
        # ollama_api normally needs no key at all for a self-hosted server,
        # so it's excluded by requires_api_key — but it's also how you reach
        # Ollama's own cloud models at https://ollama.com, and *that* needs a
        # key from ollama.com/settings/keys to actually chat (listing models
        # is public). Always show its field, just mark it optional.
        for provider_id, provider in PROVIDERS.items():
            if not provider.requires_api_key and provider_id != "ollama_api":
                continue
            edit = QLineEdit(settings.api_keys.get(provider_id, ""))
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            placeholder = f"{provider.display_name} API key"
            if provider_id == "ollama_api":
                placeholder += " (optional — only for calling ollama.com directly from this app)"
                edit.setToolTip(
                    "Only used by the 'Ollama (Remote / Cloud API)' provider choice, to call "
                    "https://ollama.com directly with this key as the request's auth. This is "
                    "unrelated to running `ollama signin` in a terminal or the Ollama desktop app "
                    "being signed in — those control your LOCAL Ollama server, which the 'Ollama "
                    "(Local)' provider already talks to with no key needed here. If a model shows "
                    "up in `ollama list` on this machine, pick 'Ollama (Local)' to use it, not this."
                )
            edit.setPlaceholderText(placeholder)
            edit.textChanged.connect(lambda _text, pid=provider_id: self._debounce_save_key(pid))
            api_keys_form.addRow(provider.display_name, edit)
            self._api_key_edits[provider_id] = edit
        api_keys_box.setLayout(api_keys_form)

        behavior_box = QGroupBox("Behavior")
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        self._theme_combo.setCurrentText(settings.theme)

        self._retry_spin = QSpinBox()
        self._retry_spin.setRange(0, 10)
        self._retry_spin.setToolTip(
            "Loop keeps fixing and re-checking for as long as each attempt improves on the "
            "last one — this is NOT a total attempt cap. It only gives up once this many "
            "consecutive iterations in a row fail to improve anything (a genuine stall), not "
            "after a fixed number of tries overall."
        )
        self._retry_spin.setValue(settings.retry_limit)

        self._harness_retry_spin = QSpinBox()
        self._harness_retry_spin.setRange(1, 10)
        self._harness_retry_spin.setToolTip(
            "With Auto Run on: the full Harness -> Loop -> Graph -> Code Review chain keeps "
            "retrying automatically for as long as each round is making progress, including "
            "secret/PII findings (Loop moves them to an environment variable, never masks them). "
            "It only gives up once this many consecutive rounds in a row show no improvement (a "
            "genuine stall) — not after a fixed total number of rounds. With Auto Run OFF, any "
            "failure — including secrets/PII — blocks immediately for manual review instead."
        )
        self._harness_retry_spin.setValue(settings.harness_auto_retry_limit)

        self._debounce_spin = QDoubleSpinBox()
        self._debounce_spin.setRange(0.2, 10.0)
        self._debounce_spin.setSingleStep(0.1)
        self._debounce_spin.setValue(settings.debounce_seconds)

        self._batch_window_spin = QSpinBox()
        self._batch_window_spin.setRange(200, 10000)
        self._batch_window_spin.setSingleStep(100)
        self._batch_window_spin.setValue(settings.pipeline_batch_window_ms)

        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.0, 1.5)
        self._temperature_spin.setSingleStep(0.05)
        self._temperature_spin.setValue(settings.temperature)

        self._context_spin = QSpinBox()
        self._context_spin.setRange(512, 131072)
        self._context_spin.setSingleStep(512)
        self._context_spin.setValue(settings.context_size)

        self._autostart_check = QCheckBox("Start monitoring automatically at Windows login")
        self._autostart_check.setChecked(settings.autostart)

        self._monitoring_check = QCheckBox("Monitoring enabled")
        self._monitoring_check.setChecked(settings.monitoring_enabled)

        self._auto_run_check = QCheckBox(
            "Auto Run — OFF: ask before every fix (Accept/Reject each diff). "
            "ON: auto-trigger Loop Engineering on failure, auto-apply its fixes, "
            "auto-chain into Graph Engineering, no prompts — you'll just see a "
            "final \"100% clean\" notification when it's done."
        )
        self._auto_run_check.setChecked(settings.auto_run_enabled)
        self._auto_run_check.toggled.connect(self._on_auto_run_toggled)
        bus.auto_run_changed.connect(self._on_auto_run_changed_elsewhere)

        self._web_dashboard_check = QCheckBox(
            "Open a live browser mirror of this app on startup (restart required to apply)"
        )
        self._web_dashboard_check.setChecked(settings.web_dashboard_enabled)

        self._web_port_spin = QSpinBox()
        self._web_port_spin.setRange(1024, 65535)
        self._web_port_spin.setValue(settings.web_dashboard_port)

        behavior_form = QFormLayout()
        behavior_form.addRow("Theme", self._theme_combo)
        behavior_form.addRow("Loop stall limit (consecutive non-improving iterations)", self._retry_spin)
        behavior_form.addRow("Chain stall limit (consecutive non-improving rounds, Auto Run)", self._harness_retry_spin)
        behavior_form.addRow("File debounce (seconds)", self._debounce_spin)
        behavior_form.addRow("Pipeline batch window (ms)", self._batch_window_spin)
        behavior_form.addRow("Model temperature", self._temperature_spin)
        behavior_form.addRow("Context size (tokens)", self._context_spin)
        behavior_form.addRow(self._monitoring_check)
        behavior_form.addRow(self._autostart_check)
        behavior_form.addRow(self._auto_run_check)
        behavior_form.addRow(self._web_dashboard_check)
        behavior_form.addRow("Browser mirror port", self._web_port_spin)
        behavior_box.setLayout(behavior_form)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)

        layout = QVBoxLayout(self)
        layout.addWidget(connection_box)
        layout.addWidget(api_keys_box)
        layout.addWidget(behavior_box)
        layout.addWidget(save_btn)
        layout.addStretch(1)

    def _debounce_save_key(self, provider_id: str) -> None:
        timer = self._key_save_timers.get(provider_id)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda pid=provider_id: self._save_key(pid))
            self._key_save_timers[provider_id] = timer
        timer.start(_KEY_SAVE_DEBOUNCE_MS)

    def _save_key(self, provider_id: str) -> None:
        self._settings.api_keys[provider_id] = self._api_key_edits[provider_id].text().strip()
        self._settings.save()
        bus.api_keys_changed.emit()

    def _save_remote_host(self) -> None:
        self._settings.ollama_remote_host = self._remote_host_edit.text().strip()
        self._settings.save()
        bus.api_keys_changed.emit()

    def _save(self) -> None:
        s = self._settings
        s.ollama_host = self._host_edit.text().strip() or s.ollama_host
        s.ollama_remote_host = self._remote_host_edit.text().strip()
        for provider_id, edit in self._api_key_edits.items():
            s.api_keys[provider_id] = edit.text().strip()
        s.theme = self._theme_combo.currentText()
        s.retry_limit = self._retry_spin.value()
        s.harness_auto_retry_limit = self._harness_retry_spin.value()
        s.debounce_seconds = self._debounce_spin.value()
        s.pipeline_batch_window_ms = self._batch_window_spin.value()
        s.temperature = self._temperature_spin.value()
        s.context_size = self._context_spin.value()
        s.autostart = self._autostart_check.isChecked()
        s.monitoring_enabled = self._monitoring_check.isChecked()
        s.web_dashboard_enabled = self._web_dashboard_check.isChecked()
        s.web_dashboard_port = self._web_port_spin.value()
        s.save()
        bus.api_keys_changed.emit()
        self.settings_changed.emit()

    def _on_auto_run_toggled(self, checked: bool) -> None:
        self._settings.set_auto_run(checked)
        bus.auto_run_changed.emit(checked)

    def _on_auto_run_changed_elsewhere(self, checked: bool) -> None:
        # Another widget (the Dashboard toggle) already persisted this —
        # just reflect it here without re-emitting or re-saving.
        self._auto_run_check.blockSignals(True)
        self._auto_run_check.setChecked(checked)
        self._auto_run_check.blockSignals(False)
