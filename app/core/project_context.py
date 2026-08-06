"""Lightweight project context: language detection, build files, venv discovery.

Built cheaply on each pipeline trigger so steps understand the whole project
even though only the changed file(s) are deeply analyzed.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.config.constants import IGNORED_DIR_NAMES, PYTHON_BUILD_FILES, SUPPORTED_EXTENSIONS


@dataclass
class ProjectContext:
    root: Path
    python_executable: str
    build_files: list[str] = field(default_factory=list)
    has_tests_dir: bool = False
    has_integration_tests: bool = False
    source_files: list[Path] = field(default_factory=list)

    @property
    def is_python_project(self) -> bool:
        return bool(self.build_files) or any(f.suffix == ".py" for f in self.source_files)


def _find_project_python(root: Path) -> str:
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
        root / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def build_project_context(root: str | Path) -> ProjectContext:
    root_path = Path(root).resolve()
    build_files = [name for name in PYTHON_BUILD_FILES if (root_path / name).exists()]
    tests_dir = root_path / "tests"
    has_tests_dir = tests_dir.is_dir()
    has_integration_tests = (tests_dir / "integration").is_dir()

    source_files: list[Path] = []
    for path in root_path.rglob("*"):
        if path.is_dir():
            continue
        try:
            rel_parts = path.relative_to(root_path).parts
        except ValueError:
            continue
        if any(part in IGNORED_DIR_NAMES for part in rel_parts):
            continue
        if path.suffix in SUPPORTED_EXTENSIONS:
            source_files.append(path)

    return ProjectContext(
        root=root_path,
        python_executable=_find_project_python(root_path),
        build_files=build_files,
        has_tests_dir=has_tests_dir,
        has_integration_tests=has_integration_tests,
        source_files=source_files,
    )
