"""Per-project baseline snapshots for Code Review's before/after comparison.

A "baseline" is the last set of file contents Code Review approved as
clean, stored on disk (not in memory) so it survives app restarts.
Updated only when Code Review actually passes — a run that finds a
regression leaves the baseline untouched, so the *next* attempt still
compares against the same last-known-good state rather than a broken
intermediate one.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config.settings import CODE_REVIEW_BASELINE_DIR


def _project_key(project_path: str) -> str:
    normalized = str(Path(project_path).resolve())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _baseline_file(project_path: str) -> Path:
    return CODE_REVIEW_BASELINE_DIR / f"{_project_key(project_path)}.json"


def load_baseline(project_path: str) -> dict[str, str]:
    """Returns {absolute_file_path: content} as of the last Code Review
    pass for this project — an empty dict if it has never passed yet."""
    path = _baseline_file(project_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_baseline(project_path: str, files: dict[str, str]) -> None:
    """Merges `files` into the existing baseline (files not touched this
    run keep their previously recorded content) and writes it back."""
    baseline = load_baseline(project_path)
    baseline.update(files)
    CODE_REVIEW_BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    _baseline_file(project_path).write_text(json.dumps(baseline), encoding="utf-8")
