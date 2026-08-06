"""File backup/rollback helper used by Loop Engineering before it applies any
Ollama-suggested fix — every touched file can always be restored exactly."""
from __future__ import annotations

import shutil
from pathlib import Path

from app.config.settings import BACKUP_DIRNAME


def _backup_path(project_root: Path, run_id: str, file_path: Path) -> Path:
    try:
        rel = file_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        rel = Path(file_path.name)
    return project_root / BACKUP_DIRNAME / run_id / rel


def backup_file(project_root: Path, run_id: str, file_path: Path) -> Path | None:
    if not file_path.exists():
        return None
    dest = _backup_path(project_root, run_id, file_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, dest)
    return dest


def restore_file(project_root: Path, run_id: str, file_path: Path) -> bool:
    src = _backup_path(project_root, run_id, file_path)
    if not src.exists():
        return False
    shutil.copy2(src, file_path)
    return True
