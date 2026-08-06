"""Exports a full clean copy of a project to the user's Downloads folder,
once the full Harness -> (Loop, if it ran) -> Graph chain has passed for it.
Excludes build/VCS/cache artifacts that have no business in a "clean,
tested" snapshot handed to someone else.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.events import bus
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_EXCLUDED_DIR_NAMES = {
    ".venv", "venv", ".git", "__pycache__", "node_modules", ".harness_backup",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "dist", "build", ".idea", ".vscode",
}


@dataclass
class CleanCopyResult:
    source: str
    destination: str
    file_count: int


def _downloads_dir() -> Path:
    return Path.home() / "Downloads"


def _ignore(_dir_path: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _EXCLUDED_DIR_NAMES}


def export_clean_copy(project_path: str) -> CleanCopyResult:
    source = Path(project_path)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destination = _downloads_dir() / f"HarnessClean_{source.name}_{timestamp}"

    shutil.copytree(source, destination, ignore=_ignore)
    file_count = sum(1 for p in destination.rglob("*") if p.is_file())

    logger.info("Exported clean copy of %s to %s (%d file(s))", project_path, destination, file_count)
    result = CleanCopyResult(source=str(source), destination=str(destination), file_count=file_count)
    bus.clean_copy_ready.emit(result.source, result.destination, result.file_count)
    return result
