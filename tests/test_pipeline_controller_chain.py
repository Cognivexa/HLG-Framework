"""Tests for PipelineController's auto-chain branching logic: Harness pass ->
Graph auto-runs; Harness fail + auto-loop off -> blocked; Harness fail +
auto-loop on -> Loop runs, then Harness is re-checked fresh (regardless of
what Loop itself believes it resolved) and the whole round repeats until
either everything passes or `harness_auto_retry_limit` attempts are used up.

`run_in_background` is monkeypatched to execute synchronously so these tests
don't depend on real background threading — only the branching logic itself
is under test here.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import app.core.pipeline_controller as pipeline_controller_module
from app.core.events import PipelineEvent, bus
from app.core.pipeline_controller import PipelineController
from app.pipelines.base import StepResult


def _fake_run_in_background(work, on_finished=None, on_failed=None):
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        if on_failed:
            on_failed(str(exc))
        return
    if on_finished:
        on_finished(result)


@pytest.fixture(autouse=True)
def _sync_background(monkeypatch):
    monkeypatch.setattr(pipeline_controller_module, "run_in_background", _fake_run_in_background)


class _FakeSettings:
    def __init__(self, auto_loop_on_failure=False, harness_auto_retry_limit=3):
        self.monitoring_enabled = True
        self.auto_loop_on_failure = auto_loop_on_failure
        self.harness_auto_retry_limit = harness_auto_retry_limit
        self.pipeline_batch_window_ms = 800


class _FakeHarnessCtx:
    def __init__(self, results, project="fake-project"):
        self.results = results
        self.project = project
        self.run_id = "run-1"


def _passing_harness_ctx():
    return _FakeHarnessCtx({
        "build_verification": StepResult(step_id="build_verification", step_name="Build", status="success"),
        "unit_tests": StepResult(step_id="unit_tests", step_name="Tests", status="success"),
    })


def _failing_harness_ctx():
    return _FakeHarnessCtx({
        "build_verification": StepResult(step_id="build_verification", step_name="Build", status="success"),
        "unit_tests": StepResult(step_id="unit_tests", step_name="Tests", status="failed"),
    })


def _settle_flag():
    state = {"called": False}
    return state, (lambda: state.update(called=True))


def test_harness_pass_triggers_graph_directly(monkeypatch):
    controller = PipelineController(_FakeSettings(), llm_client=None)
    called = {}

    def fake_run_graph(project_path, files, project, attempt, on_settled, **_kwargs):
        called["args"] = (project_path, files, project, attempt)
        on_settled()

    monkeypatch.setattr(controller, "_run_graph", fake_run_graph)
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _passing_harness_ctx(), 1, on_settled)

    assert called["args"] == ("C:/proj", ["a.py"], "fake-project", 1)
    assert state["called"]


def test_harness_fail_with_auto_loop_off_blocks_without_running_loop_or_graph(monkeypatch):
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=False), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock())
    state, on_settled = _settle_flag()

    received = []
    bus.pipeline_updated.connect(received.append)
    try:
        controller._continue_chain("C:/proj", ["a.py"], _failing_harness_ctx(), 1, on_settled)
    finally:
        bus.pipeline_updated.disconnect(received.append)

    controller._run_graph.assert_not_called()
    assert state["called"]
    statuses = {(e.pipeline, e.status) for e in received if isinstance(e, PipelineEvent)}
    assert ("loop", "blocked") in statuses
    assert ("graph", "blocked") in statuses


def test_harness_fail_with_auto_loop_on_recovers_after_loop_and_runs_graph(monkeypatch):
    """Loop claims it resolved everything; the mandatory fresh Harness
    re-check confirms it (now passing), so Graph finally runs."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args, **kwargs: args[-1]()))
    monkeypatch.setattr(
        pipeline_controller_module, "run_loop_pipeline",
        lambda *a, **kw: {"run_id": "loop-1", "iterations": 1, "final_failures": 0},
    )
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: _passing_harness_ctx())
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _failing_harness_ctx(), 1, on_settled)

    controller._run_graph.assert_called_once()
    assert state["called"]


class _FakeGraphCtx:
    def __init__(self):
        self.results = {"final_verification": StepResult(step_id="final_verification", step_name="Final", status="success")}
        self.project = "fake-project"


def test_graph_pass_with_clean_code_review_exports_clean_copy(monkeypatch):
    controller = PipelineController(_FakeSettings(), llm_client=None)
    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FakeGraphCtx())
    monkeypatch.setattr(
        pipeline_controller_module, "run_code_review_pipeline",
        lambda *a, **kw: {"status": "success", "flagged": False, "run_id": "cr-1"},
    )
    monkeypatch.setattr(controller, "_export_clean_copy", MagicMock(side_effect=lambda project_path, on_settled: on_settled()))
    state, on_settled = _settle_flag()

    controller._run_graph("C:/proj", ["a.py"], "fake-project", 1, on_settled)

    controller._export_clean_copy.assert_called_once()
    assert state["called"]


def test_code_review_with_no_panel_configured_still_exports(monkeypatch):
    """status="skipped" (no Code Review panel set up) is a no-op, not a block."""
    controller = PipelineController(_FakeSettings(), llm_client=None)
    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FakeGraphCtx())
    monkeypatch.setattr(
        pipeline_controller_module, "run_code_review_pipeline",
        lambda *a, **kw: {"status": "skipped", "flagged": False, "run_id": "cr-1"},
    )
    monkeypatch.setattr(controller, "_export_clean_copy", MagicMock(side_effect=lambda project_path, on_settled: on_settled()))
    state, on_settled = _settle_flag()

    controller._run_graph("C:/proj", ["a.py"], "fake-project", 1, on_settled)

    controller._export_clean_copy.assert_called_once()
    assert state["called"]


def test_code_review_regression_with_auto_run_on_restarts_the_chain(monkeypatch):
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=3), llm_client=None)
    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FakeGraphCtx())
    monkeypatch.setattr(
        pipeline_controller_module, "run_code_review_pipeline",
        lambda *a, **kw: {"status": "failed", "flagged": True, "detail": "regression!", "run_id": "cr-1"},
    )
    restart = MagicMock(side_effect=lambda project_path, files, attempt, on_settled, **kwargs: on_settled())
    monkeypatch.setattr(controller, "_run_harness_round", restart)
    state, on_settled = _settle_flag()

    controller._run_graph("C:/proj", ["a.py"], "fake-project", 1, on_settled)

    restart.assert_called_once_with("C:/proj", ["a.py"], attempt=2, on_settled=on_settled, cr_stall=1)
    assert state["called"]


def test_code_review_regression_with_auto_run_off_blocks_without_restarting(monkeypatch):
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=False), llm_client=None)
    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FakeGraphCtx())
    monkeypatch.setattr(
        pipeline_controller_module, "run_code_review_pipeline",
        lambda *a, **kw: {"status": "failed", "flagged": True, "detail": "regression!", "run_id": "cr-1"},
    )
    restart = MagicMock()
    monkeypatch.setattr(controller, "_run_harness_round", restart)
    state, on_settled = _settle_flag()

    received = []
    bus.pipeline_updated.connect(received.append)
    try:
        controller._run_graph("C:/proj", ["a.py"], "fake-project", 1, on_settled)
    finally:
        bus.pipeline_updated.disconnect(received.append)

    restart.assert_not_called()
    assert state["called"]
    statuses = {(e.pipeline, e.status) for e in received if isinstance(e, PipelineEvent)}
    assert ("code_review", "blocked") in statuses


def test_code_review_regression_exhausts_retries_then_blocks(monkeypatch):
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=2), llm_client=None)
    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FakeGraphCtx())
    monkeypatch.setattr(
        pipeline_controller_module, "run_code_review_pipeline",
        lambda *a, **kw: {"status": "failed", "flagged": True, "detail": "regression!", "run_id": "cr-1"},
    )
    restart = MagicMock()
    monkeypatch.setattr(controller, "_run_harness_round", restart)
    state, on_settled = _settle_flag()

    received = []
    bus.pipeline_updated.connect(received.append)
    try:
        # cr_stall=1: one regression round already happened with no
        # improvement (regressions are binary — every one extends the
        # streak by exactly one), so this one pushes it to the limit.
        controller._run_graph("C:/proj", ["a.py"], "fake-project", 2, on_settled, cr_stall=1)
    finally:
        bus.pipeline_updated.disconnect(received.append)

    restart.assert_not_called()
    assert state["called"]
    statuses = {(e.pipeline, e.status) for e in received if isinstance(e, PipelineEvent)}
    assert ("code_review", "blocked") in statuses


def test_harness_fail_with_auto_loop_on_exhausts_retries_then_blocks(monkeypatch):
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=2), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock())
    monkeypatch.setattr(
        pipeline_controller_module, "run_loop_pipeline",
        lambda *a, **kw: {"run_id": "loop-1", "iterations": 3, "final_failures": 2},
    )
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: _failing_harness_ctx())
    state, on_settled = _settle_flag()

    received = []
    bus.pipeline_updated.connect(received.append)
    try:
        controller._continue_chain("C:/proj", ["a.py"], _failing_harness_ctx(), 1, on_settled)
    finally:
        bus.pipeline_updated.disconnect(received.append)

    controller._run_graph.assert_not_called()
    assert state["called"]
    statuses = {(e.pipeline, e.status) for e in received if isinstance(e, PipelineEvent)}
    assert ("graph", "blocked") in statuses


def test_harness_fail_recovers_on_a_later_retry_attempt(monkeypatch):
    """First Harness re-check after Loop is still failing; the round after
    that finally passes — proves the retry genuinely repeats more than
    once rather than giving up after a single Loop attempt."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=5), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args, **kwargs: args[-1]()))
    monkeypatch.setattr(
        pipeline_controller_module, "run_loop_pipeline",
        lambda *a, **kw: {"run_id": "loop-1", "iterations": 1, "final_failures": 1},
    )
    harness_results = iter([_failing_harness_ctx(), _failing_harness_ctx(), _passing_harness_ctx()])
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: next(harness_results))
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _failing_harness_ctx(), 1, on_settled)

    controller._run_graph.assert_called_once()
    assert state["called"]


def _secret_harness_ctx():
    return _FakeHarnessCtx({
        "build_verification": StepResult(step_id="build_verification", step_name="Build", status="success"),
        "unit_tests": StepResult(step_id="unit_tests", step_name="Tests", status="success"),
        "detect_pii": StepResult(
            step_id="detect_pii", step_name="Detect PII", status="failed", detail="password in prime.py:6",
            data={"locations": [{"file": "prime.py", "line": 6, "snippet": "password = ...", "category": "password"}]},
        ),
    })


def test_secret_finding_blocks_with_specific_message_when_auto_run_off(monkeypatch):
    """With Auto Run off, a real secret/PII finding blocks immediately and
    names exactly what was found — it is not handed to Loop."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=False), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock())
    run_loop = MagicMock()
    monkeypatch.setattr(pipeline_controller_module, "run_loop_pipeline", run_loop)
    state, on_settled = _settle_flag()

    received = []
    bus.pipeline_updated.connect(received.append)
    try:
        controller._continue_chain("C:/proj", ["a.py"], _secret_harness_ctx(), 1, on_settled)
    finally:
        bus.pipeline_updated.disconnect(received.append)

    controller._run_graph.assert_not_called()
    run_loop.assert_not_called()
    assert state["called"]
    blocked = {(e.pipeline, e.status): e.summary for e in received if isinstance(e, PipelineEvent)}
    assert ("loop", "blocked") in blocked
    assert ("graph", "blocked") in blocked
    assert "prime.py:6" in blocked[("graph", "blocked")]


def test_secret_finding_routes_through_loop_when_auto_run_on(monkeypatch):
    """With Auto Run on, a secret/PII finding is treated like any other
    Loop-fixable failure — Loop gets a chance to fix it (moved to an
    environment variable, per loop_pipeline's fix prompt), not an immediate
    block."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args, **kwargs: args[-1]()))
    run_loop = MagicMock(return_value={"run_id": "loop-1", "iterations": 1, "final_failures": 0})
    monkeypatch.setattr(pipeline_controller_module, "run_loop_pipeline", run_loop)
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: _passing_harness_ctx())
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _secret_harness_ctx(), 1, on_settled)

    run_loop.assert_called_once()
    controller._run_graph.assert_called_once()
    assert state["called"]


def test_graph_failure_on_loop_relevant_step_retries_through_harness(monkeypatch):
    """A Graph failure that isn't a secret finding used to just call
    on_settled() and stop silently; it should now retry through the same
    Harness/Loop path a Harness-level failure would."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=3), llm_client=None)

    class _FailingGraphCtx:
        def __init__(self):
            self.results = {
                "final_verification": StepResult(
                    step_id="final_verification", step_name="Final", status="failed",
                    detail="REJECTED — 1 check(s) failing: unit_tests",
                ),
                "unit_tests": StepResult(step_id="unit_tests", step_name="Unit Test Agent", status="failed"),
            }
            self.project = "fake-project"
            self.run_id = "graph-1"

    monkeypatch.setattr(pipeline_controller_module, "run_graph_pipeline", lambda *a, **kw: _FailingGraphCtx())
    restart = MagicMock(side_effect=lambda *args, **kwargs: kwargs["on_settled"]())
    monkeypatch.setattr(controller, "_run_harness_round", restart)
    state, on_settled = _settle_flag()

    controller._run_graph("C:/proj", ["a.py"], "fake-project", 1, on_settled)

    restart.assert_called_once_with(
        "C:/proj", ["a.py"], attempt=2, on_settled=on_settled, stall=0, prev_failures=1, cr_stall=0,
    )
    assert state["called"]


def test_stall_tracking_keeps_retrying_past_old_hard_cap_while_improving(monkeypatch):
    """With harness_auto_retry_limit=2, the OLD hard-cap logic would have
    given up after exactly 2 attempts regardless of trend. Since each round
    here strictly reduces the failure count, the new stall-based logic keeps
    going well past that number and only stops once it actually passes."""
    controller = PipelineController(_FakeSettings(auto_loop_on_failure=True, harness_auto_retry_limit=2), llm_client=None)
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args, **kwargs: args[-1]()))
    monkeypatch.setattr(
        pipeline_controller_module, "run_loop_pipeline",
        lambda *a, **kw: {"run_id": "loop-1", "iterations": 1, "final_failures": 0},
    )

    def _ctx_with(failing_steps):
        results = {
            step_id: StepResult(
                step_id=step_id, step_name=step_id, status="failed" if step_id in failing_steps else "success",
            )
            for step_id in ("build_verification", "unit_tests", "static_analysis")
        }
        return _FakeHarnessCtx(results)

    remaining = iter([
        _ctx_with({"unit_tests", "static_analysis"}),  # 2 failing (improved from 3)
        _ctx_with({"static_analysis"}),  # 1 failing (improved again)
        _ctx_with(set()),  # 0 failing — passes
    ])
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: next(remaining))
    state, on_settled = _settle_flag()

    initial_ctx = _ctx_with({"build_verification", "unit_tests", "static_analysis"})  # 3 failing
    controller._continue_chain("C:/proj", ["a.py"], initial_ctx, 1, on_settled)

    controller._run_graph.assert_called_once()
    assert state["called"]
