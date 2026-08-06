"""Tests for project context detection (build files, tests dir, venv discovery)."""
from __future__ import annotations

import sys

from app.core.project_context import build_project_context


def test_detects_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    ctx = build_project_context(tmp_path)
    assert "requirements.txt" in ctx.build_files
    assert ctx.is_python_project


def test_detects_tests_directory(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): assert True\n")
    ctx = build_project_context(tmp_path)
    assert ctx.has_tests_dir
    assert not ctx.has_integration_tests


def test_detects_integration_tests_directory(tmp_path):
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    ctx = build_project_context(tmp_path)
    assert ctx.has_integration_tests


def test_falls_back_to_system_python_without_venv(tmp_path):
    ctx = build_project_context(tmp_path)
    assert ctx.python_executable == sys.executable


def test_finds_project_venv(tmp_path):
    venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_bytes(b"")
    ctx = build_project_context(tmp_path)
    assert ctx.python_executable == str(venv_python)


def test_ignores_ignored_directories(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.py").write_text("# should be ignored\n")
    (tmp_path / "real.py").write_text("# real file\n")
    ctx = build_project_context(tmp_path)
    names = {f.name for f in ctx.source_files}
    assert "real.py" in names
    assert "cache.py" not in names
