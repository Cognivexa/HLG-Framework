"""Run history index: a lightweight record of past pipeline runs and where
their generated reports live on disk, for the Reports tab to browse."""
from __future__ import annotations

import json

from app.config.settings import HISTORY_DIR

_INDEX_FILE = HISTORY_DIR / "index.json"
_MAX_ENTRIES = 500


def _load_index() -> list[dict]:
    if not _INDEX_FILE.exists():
        return []
    try:
        return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def record_run(entry: dict) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    index = _load_index()
    index.append(entry)
    index = index[-_MAX_ENTRIES:]
    _INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def list_runs() -> list[dict]:
    return list(reversed(_load_index()))
