"""Tests for the concurrent DAG executor used by Graph Engineering."""
from __future__ import annotations

import threading

from app.pipelines.base import PipelineContext, StepResult
from app.pipelines.graph.agents import GraphNode
from app.pipelines.graph.graph_executor import run_graph


def _make_ctx() -> PipelineContext:
    return PipelineContext(
        run_id="graph-test", project_path="C:\\fake", project=None,
        changed_files=[], settings=None, llm_client=None,
    )


def test_dependent_node_runs_after_its_dependency():
    execution_order = []
    lock = threading.Lock()

    def record(name):
        with lock:
            execution_order.append(name)

    def node_a(ctx):
        record("a")
        return StepResult(step_id="a", step_name="A", status="success")

    def node_b(ctx):
        assert "a" in ctx.results  # b depends on a; a's result must already be there
        record("b")
        return StepResult(step_id="b", step_name="B", status="success")

    nodes = {
        "a": GraphNode(id="a", label="A", fn=node_a),
        "b": GraphNode(id="b", label="B", fn=node_b, depends_on=("a",)),
    }
    results = run_graph(nodes, _make_ctx(), run_id="graph-test")

    assert execution_order == ["a", "b"]
    assert results["a"].status == "success"
    assert results["b"].status == "success"


def test_independent_nodes_run_concurrently():
    # A Barrier only clears once BOTH nodes reach it. If the executor ran them
    # sequentially, the second node would never be started while the first
    # blocks on the barrier, and this would raise BrokenBarrierError instead.
    barrier = threading.Barrier(2, timeout=5)

    def slow_node(node_id):
        def fn(ctx):
            barrier.wait()
            return StepResult(step_id=node_id, step_name=node_id, status="success")
        return fn

    nodes = {
        "x": GraphNode(id="x", label="X", fn=slow_node("x")),
        "y": GraphNode(id="y", label="Y", fn=slow_node("y")),
    }
    results = run_graph(nodes, _make_ctx(), run_id="graph-test-2")

    assert results["x"].status == "success"
    assert results["y"].status == "success"


def test_node_exception_is_captured_as_failed_result_and_does_not_block_others():
    def boom(ctx):
        raise RuntimeError("node blew up")

    def fine(ctx):
        return StepResult(step_id="fine", step_name="Fine", status="success")

    nodes = {
        "boom": GraphNode(id="boom", label="Boom", fn=boom),
        "fine": GraphNode(id="fine", label="Fine", fn=fine),
    }
    results = run_graph(nodes, _make_ctx(), run_id="graph-test-3")

    assert results["boom"].status == "failed"
    assert "node blew up" in results["boom"].detail
    assert results["fine"].status == "success"
