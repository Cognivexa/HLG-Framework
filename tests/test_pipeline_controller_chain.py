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

    def fake_run_graph(project_path, files, project, on_settled):
        called["args"] = (project_path, files, project)
        on_settled()

    monkeypatch.setattr(controller, "_run_graph", fake_run_graph)
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _passing_harness_ctx(), 1, on_settled)

    assert called["args"] == ("C:/proj", ["a.py"], "fake-project")
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
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args: args[-1]()))
    monkeypatch.setattr(
        pipeline_controller_module, "run_loop_pipeline",
        lambda *a, **kw: {"run_id": "loop-1", "iterations": 1, "final_failures": 0},
    )
    monkeypatch.setattr(pipeline_controller_module, "run_harness_pipeline", lambda *a, **kw: _passing_harness_ctx())
    state, on_settled = _settle_flag()

    controller._continue_chain("C:/proj", ["a.py"], _failing_harness_ctx(), 1, on_settled)

    controller._run_graph.assert_called_once()
    assert state["called"]


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
    monkeypatch.setattr(controller, "_run_graph", MagicMock(side_effect=lambda *args: args[-1]()))
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
