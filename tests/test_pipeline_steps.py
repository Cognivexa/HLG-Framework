"""Tests for pure-logic pipeline steps that don't need subprocess calls
(build/test/lint step wrappers are covered by the end-to-end smoke tests
instead, since their value is in the real subprocess integration)."""
from __future__ import annotations

from app.pipelines.base import PipelineContext
from app.pipelines.steps import doc_steps, secrets_steps


def _make_ctx(changed_files) -> PipelineContext:
    return PipelineContext(
        run_id="steps-test", project_path="C:\\fake", project=None,
        changed_files=changed_files, settings=None, llm_client=None,
    )


def test_documentation_check_flags_low_coverage(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text(
        "def documented():\n    \"\"\"Has a docstring.\"\"\"\n    pass\n\n"
        "def undocumented():\n    pass\n\n"
        "def also_undocumented():\n    pass\n"
    )
    result = doc_steps.documentation_check(_make_ctx([str(path)]))
    assert result.status == "failed"


def test_documentation_check_passes_with_good_coverage(tmp_path):
    path = tmp_path / "mod.py"
    path.write_text('"""Module docstring."""\n\n\ndef documented():\n    """Has a docstring."""\n    pass\n')
    result = doc_steps.documentation_check(_make_ctx([str(path)]))
    assert result.status == "success"


def test_documentation_check_fails_on_undocumented_module(tmp_path):
    # Every parseable file has at least the Module AST node, so a file with
    # no docstring and no functions/classes still counts as 1 undocumented
    # definition (0% coverage), not "nothing to check."
    path = tmp_path / "mod.py"
    path.write_text("x = 1\n")
    result = doc_steps.documentation_check(_make_ctx([str(path)]))
    assert result.status == "failed"


def test_documentation_check_skips_when_no_python_files_in_change_set(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("just some notes\n")
    result = doc_steps.documentation_check(_make_ctx([str(path)]))
    assert result.status == "skipped"


def test_combined_secret_detection_aggregates_categories(tmp_path):
    path = tmp_path / "secrets.py"
    path.write_text('PASSWORD = "hunter2222"\nAWS_ACCESS_KEY_ID = "AKIAABCDEFGHIJKLMNOP"\n')
    result = secrets_steps.combined_secret_detection(_make_ctx([str(path)]))
    assert result.status == "failed"
    assert "password" in result.detail
    assert "api_key" in result.detail


def test_combined_secret_detection_success_on_clean_file(tmp_path):
    path = tmp_path / "clean.py"
    path.write_text("def add(a, b):\n    return a + b\n")
    result = secrets_steps.combined_secret_detection(_make_ctx([str(path)]))
    assert result.status == "success"
