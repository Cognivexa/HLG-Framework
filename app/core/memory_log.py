"""Episodic log of memory-gate decisions: every time Loop Engineering fixes
something, was the lesson generalized and remembered (see
app/pipelines/loop/memory_gate.py), or was it judged too specific to keep?
Mirrors the shape of reports/history.py."""
from __future__ import annotations

import json

from app.config.settings import CONFIG_DIR

MEMORY_DIR = CONFIG_DIR / "memory"
_LOG_FILE = MEMORY_DIR / "gate_decisions.json"
_MAX_ENTRIES = 500


def _load() -> list[dict]:
    if not _LOG_FILE.exists():
        return []
    try:
        return json.loads(_LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def record_decision(entry: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    log = _load()
    log.append(entry)
    log = log[-_MAX_ENTRIES:]
    _LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


def list_decisions() -> list[dict]:
    return list(reversed(_load()))
