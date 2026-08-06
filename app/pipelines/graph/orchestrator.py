"""Router/Orchestrator Agent: decides which agent nodes execute for a given
trigger, and their dependency structure (i.e. what may run in parallel)."""
from __future__ import annotations

from app.core.logging_setup import get_logger
from app.pipelines.graph.agents import GraphNode, build_agent_graph

logger = get_logger(__name__)


def route(trigger: str = "file_saved") -> dict[str, GraphNode]:
    """Returns the agent DAG to execute for the given trigger.

    A single trigger type covers this MVP (the full 16-agent graph always
    runs); the seam is here for future trigger types — e.g. a
    dependency-only recheck — to route to a smaller node subset without
    touching the executor or the agents themselves.
    """
    graph = build_agent_graph()
    logger.info("Routed trigger '%s' to %d agent(s)", trigger, len(graph))
    return graph
