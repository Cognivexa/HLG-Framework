"""Topological DAG execution with real concurrency for independent nodes —
this is what distinguishes Graph Engineering's execution model from Harness
Engineering's strictly sequential one, even though many nodes wrap the same
underlying step functions."""
from __future__ import annotations

import concurrent.futures as cf

from app.core.events import GraphNodeEvent, StepEvent, bus
from app.core.logging_setup import get_logger
from app.pipelines.base import PipelineContext, StepResult
from app.pipelines.graph.agents import GraphNode

logger = get_logger(__name__)


def _emit(run_id: str, node: GraphNode, status: str, detail: str = "", data: dict | None = None) -> None:
    bus.graph_node_updated.emit(
        GraphNodeEvent(run_id=run_id, node_id=node.id, node_label=node.label, status=status, depends_on=node.depends_on)
    )
    bus.step_updated.emit(
        StepEvent(
            pipeline="graph", run_id=run_id, step_id=node.id, step_name=node.label, status=status, detail=detail,
            data=data or {},
        )
    )


def _run_node_safe(node: GraphNode, ctx: PipelineContext) -> StepResult:
    try:
        return node.fn(ctx)
    except Exception as exc:  # noqa: BLE001 - a node must never crash the whole graph run
        return StepResult(step_id=node.id, step_name=node.label, status="failed", detail=str(exc))


def run_graph(nodes: dict[str, GraphNode], ctx: PipelineContext, run_id: str, max_workers: int = 8) -> dict[str, StepResult]:
    for node in nodes.values():
        _emit(run_id, node, "pending")

    completed: set[str] = set()
    in_flight: dict[cf.Future, str] = {}

    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        def submit_ready() -> None:
            in_flight_ids = set(in_flight.values())
            for node in nodes.values():
                if node.id in completed or node.id in in_flight_ids:
                    continue
                if all(dep in completed for dep in node.depends_on):
                    _emit(run_id, node, "running")
                    future = executor.submit(_run_node_safe, node, ctx)
                    in_flight[future] = node.id

        submit_ready()
        while in_flight:
            done, _pending = cf.wait(list(in_flight.keys()), return_when=cf.FIRST_COMPLETED)
            for future in done:
                node_id = in_flight.pop(future)
                result = future.result()
                ctx.results[result.step_id] = result
                completed.add(node_id)
                _emit(run_id, nodes[node_id], result.status, result.detail, result.data)
            submit_ready()

    logger.info("Graph run %s: %d/%d node(s) completed", run_id, len(completed), len(nodes))
    return ctx.results
