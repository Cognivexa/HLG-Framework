"""Tests for the file watcher's event classification: which paths trigger
analysis vs. which are purely informational (deletes, git HEAD, build output)."""
from __future__ import annotations

from pathlib import Path

from app.core.file_watcher import ANALYSIS_CHANGE_TYPES, _DebouncedHandler, _is_build_output, _is_git_head


def _handler() -> _DebouncedHandler:
    return _DebouncedHandler("C:/fake/project", debounce_seconds=0.01, on_change=lambda e: None)


def test_normal_python_file_classified_as_default_type():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/app.py"), "modified") == "modified"


def test_git_head_classified_as_git_changed_regardless_of_ignore_rules():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/.git/HEAD"), "modified") == "git_changed"


def test_build_output_dir_classified_as_build_output_changed():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/dist/app.whl"), "created") == "build_output_changed"
    assert handler._classify(Path("C:/fake/project/build/output.txt"), "created") == "build_output_changed"


def test_build_output_extension_classified_even_outside_build_dir():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/lib.dll"), "created") == "build_output_changed"


def test_ignored_directory_dropped():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/__pycache__/mod.cpython-312.pyc"), "modified") in (
        "build_output_changed",  # .pyc is also a build-output extension — either classification is acceptable
        None,
    )
    assert handler._classify(Path("C:/fake/project/.venv/lib/site.py"), "modified") is None


def test_unsupported_extension_dropped():
    handler = _handler()
    assert handler._classify(Path("C:/fake/project/image.png"), "modified") is None


def test_is_git_head_helper():
    assert _is_git_head(Path("/repo/.git/HEAD")) is True
    assert _is_git_head(Path("/repo/.git/config")) is False
    assert _is_git_head(Path("/repo/HEAD")) is False


def test_is_build_output_helper():
    assert _is_build_output(Path("/repo/dist/pkg.whl")) is True
    assert _is_build_output(Path("/repo/src/main.py")) is False


def test_analysis_change_types_excludes_informational_kinds():
    assert ANALYSIS_CHANGE_TYPES == {"created", "modified", "renamed"}
    assert "deleted" not in ANALYSIS_CHANGE_TYPES
    assert "git_changed" not in ANALYSIS_CHANGE_TYPES
    assert "build_output_changed" not in ANALYSIS_CHANGE_TYPES
