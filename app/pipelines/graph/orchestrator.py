"""Router/Orchestrator Agent: decides which agent nodes execute for a given
trigger, and their dependency structure (i.e. what may run in parallel)."""
from __future__ import annotations

from app.core.agent_catalog import AgentCatalogEntry
from app.core.logging_setup import get_logger
from app.pipelines.graph.agents import GraphNode, build_agent_graph

logger = get_logger(__name__)


def route(
    trigger: str = "file_saved",
    selected_agents: list[AgentCatalogEntry] | tuple[AgentCatalogEntry, ...] = (),
) -> dict[str, GraphNode]:
    """Returns the agent DAG to execute for the given trigger.

    A single trigger type covers this MVP (the fixed agent graph always
    runs, plus one extra node per auto-selected specialist — see
    app.core.agent_catalog); the seam is here for future trigger types —
    e.g. a dependency-only recheck — to route to a smaller node subset
    without touching the executor or the agents themselves.
    """
    graph = build_agent_graph(selected_agents)
    logger.info("Routed trigger '%s' to %d agent(s) (%d specialist)", trigger, len(graph), len(selected_agents))
    return graph
