"""Application settings persisted as JSON under %LOCALAPPDATA%\\HLGFramework."""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.config.constants import (
    APP_NAME,
    DEFAULT_BATCH_WINDOW_MS,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_HARNESS_AUTO_RETRY_LIMIT,
    DEFAULT_RETRY_LIMIT,
    OLLAMA_DEFAULT_HOST,
    _LEGACY_APP_NAMES,
)


def _default_config_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_NAME


def _migrate_legacy_config_dir(new_dir: Path) -> None:
    """One-time, one-way copy (never a move) from a previous APP_NAME's
    settings folder, so renaming the app never silently resets a user's API
    keys, model choices, or project list. Runs once at import time, before
    anything reads/writes CONFIG_DIR; a no-op once the new folder exists."""
    if new_dir.exists():
        return
    for legacy_name in _LEGACY_APP_NAMES:
        legacy_dir = new_dir.parent / legacy_name
        if legacy_dir.exists() and legacy_dir != new_dir:
            shutil.copytree(legacy_dir, new_dir)
            return


CONFIG_DIR = _default_config_dir()
_migrate_legacy_config_dir(CONFIG_DIR)
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR = CONFIG_DIR / "logs"
RAG_DIR = CONFIG_DIR / "rag_store"
REPORTS_DIR = CONFIG_DIR / "reports"
HISTORY_DIR = CONFIG_DIR / "history"
BACKUP_DIRNAME = ".harness_backup"


@dataclass
class PipelineModelChoice:
    harness_review_model: str = ""
    harness_review_provider: str = "ollama_local"
    loop_fix_model: str = ""
    loop_fix_provider: str = "ollama_local"
    graph_review_model: str = ""
    graph_review_provider: str = "ollama_local"
    rag_embedding_model: str = ""
    rag_embedding_provider: str = "ollama_local"


@dataclass
class AppSettings:
    projects: list[str] = field(default_factory=list)
    ollama_host: str = OLLAMA_DEFAULT_HOST
    ollama_remote_host: str = ""
    api_keys: dict[str, str] = field(default_factory=dict)
    models: PipelineModelChoice = field(default_factory=PipelineModelChoice)
    theme: str = "dark"
    retry_limit: int = DEFAULT_RETRY_LIMIT
    harness_auto_retry_limit: int = DEFAULT_HARNESS_AUTO_RETRY_LIMIT
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS
    pipeline_batch_window_ms: int = DEFAULT_BATCH_WINDOW_MS
    autostart: bool = False
    temperature: float = 0.2
    context_size: int = 4096
    monitoring_enabled: bool = True
    auto_loop_on_failure: bool = False
    auto_apply_fixes: bool = False
    web_dashboard_enabled: bool = True
    web_dashboard_port: int = 8765

    @property
    def auto_run_enabled(self) -> bool:
        """"Auto Run": the single hands-off toggle exposed in the UI (Dashboard
        and Settings). ON means Loop auto-triggers after a failed Harness run
        AND its proposed fixes are applied without an Accept/Reject prompt —
        OFF means both stay manual, matching today's default behavior."""
        return self.auto_loop_on_failure and self.auto_apply_fixes

    def set_auto_run(self, enabled: bool) -> None:
        self.auto_loop_on_failure = enabled
        self.auto_apply_fixes = enabled
        self.save()

    @classmethod
    def load(cls) -> "AppSettings":
        if CONFIG_FILE.exists():
            try:
                raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = {}
            models_raw = raw.pop("models", {}) or {}
            known_fields = {f for f in cls.__dataclass_fields__}
            settings = cls(**{k: v for k, v in raw.items() if k in known_fields})
            settings.models = PipelineModelChoice(
                **{k: v for k, v in models_raw.items() if k in PipelineModelChoice.__dataclass_fields__}
            )
            # One-time migration: earlier versions defaulted to "localhost",
            # which resolves ~2s slower than 127.0.0.1 on some Windows setups.
            if settings.ollama_host == "http://localhost:11434":
                settings.ollama_host = OLLAMA_DEFAULT_HOST
                settings.save()
            return settings
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def add_project(self, path: str) -> None:
        normalized = str(Path(path).resolve())
        if normalized not in self.projects:
            self.projects.append(normalized)
            self.save()

    def remove_project(self, path: str) -> None:
        normalized = str(Path(path).resolve())
        if normalized in self.projects:
            self.projects.remove(normalized)
            self.save()
