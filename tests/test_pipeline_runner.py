"""Tests for the shared PipelineRunner (used by Harness Engineering; Loop and
Graph use different execution models but the same Step/StepResult/
PipelineContext types)."""
from __future__ import annotations

from app.pipelines.base import PipelineContext, PipelineRunner, Step, StepResult


def _make_ctx(**overrides) -> PipelineContext:
    defaults = dict(
        run_id="test-run", project_path="C:\\fake\\project", project=None,
        changed_files=[], settings=None, llm_client=None,
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


def test_runner_respects_declared_dependencies():
    order = []

    def step_a(ctx):
        order.append("a")
        return StepResult(step_id="a", step_name="A", status="success")

    def step_b(ctx):
        assert "a" in ctx.results  # b depends on a; a's result must already be there
        order.append("b")
        return StepResult(step_id="b", step_name="B", status="success")

    runner = PipelineRunner("test", [Step("a", "A", step_a), Step("b", "B", step_b, depends_on=("a",))])
    results = runner.run(_make_ctx())

    assert order == ["a", "b"]
    assert results["a"].status == "success"
    assert results["b"].status == "success"


def test_runner_executes_independent_steps_and_records_all_results():
    def step_a(ctx):
        return StepResult(step_id="a", step_name="A", status="success")

    def step_b(ctx):
        return StepResult(step_id="b", step_name="B", status="success")

    runner = PipelineRunner("test", [Step("a", "A", step_a), Step("b", "B", step_b)])
    results = runner.run(_make_ctx())

    assert results["a"].status == "success"
    assert results["b"].status == "success"


def test_runner_catches_step_exceptions_as_failed_result():
    def boom(ctx):
        raise ValueError("kaboom")

    runner = PipelineRunner("test", [Step("boom", "Boom", boom)])
    results = runner.run(_make_ctx())

    assert results["boom"].status == "failed"
    assert "kaboom" in results["boom"].detail


def test_runner_respects_skip_if():
    calls = []

    def step_fn(ctx):
        calls.append(1)
        return StepResult(step_id="s", step_name="S", status="success")

    runner = PipelineRunner("test", [Step("s", "S", step_fn, skip_if=lambda ctx: True)])
    results = runner.run(_make_ctx())

    assert calls == []
    assert results["s"].status == "skipped"


def test_context_get_returns_none_for_missing_step():
    ctx = _make_ctx()
    assert ctx.get("nonexistent") is None
