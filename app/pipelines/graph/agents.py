"""Graph Engineering's agent registry.

Each entry binds one of the spec-named agents (File Monitoring, Security,
Build, ...) to a real, already-tested step implementation shared with
Harness Engineering (or a small graph-only aggregator), plus its DAG
dependencies. Harness and Graph therefore never diverge on what a given
check actually does — only on whether it runs sequentially or concurrently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.core.agent_catalog import AgentCatalogEntry, with_specialist_guidance
from app.core.llm.base import ProviderError
from app.core.skills import with_skills
from app.pipelines.base import PipelineContext, StepResult
from app.pipelines.steps import (
    ai_steps,
    build_steps,
    core_steps,
    dependency_steps,
    doc_steps,
    graph_steps,
    quality_steps,
    secrets_steps,
    test_steps,
)
from app.pipelines.steps.ai_steps import _read_changed_sources


@dataclass
class GraphNode:
    id: str
    label: str
    fn: Callable[[PipelineContext], StepResult]
    depends_on: tuple[str, ...] = ()


def _make_specialist_node_fn(entry: AgentCatalogEntry) -> Callable[[PipelineContext], StepResult]:
    """Builds the node function for one auto-selected specialist — this is
    Graph Engineering's clearest expression of "a node can be a full agent,
    not just a fixed function": the node's entire behavior comes from an
    agents/*.md or skills/*/SKILL.md file picked at run time, not from code
    written for this specific specialty."""
    step_id = f"specialist_{entry.slug}"
    step_name = f"{entry.name} (Specialist Agent)"

    def run(ctx: PipelineContext) -> StepResult:
        model = ctx.settings.models.graph_review_model or ctx.settings.models.harness_review_model
        provider_id = ctx.settings.models.graph_review_provider or ctx.settings.models.harness_review_provider
        if not model:
            return StepResult(step_id=step_id, step_name=step_name, status="skipped", detail="No Graph review model selected in Settings.")

        source = _read_changed_sources(ctx)
        if not source.strip():
            return StepResult(step_id=step_id, step_name=step_name, status="skipped", detail="No reviewable source in this change set.")

        base_prompt = (
            f"You are acting as this project's {entry.name} specialist. Review the following "
            "changed file(s) through that lens specifically — flag only what's relevant to your "
            "specialty. Be concise; if nothing in your specialty applies here, say so in one sentence."
        )
        try:
            review = ctx.llm_client.chat(
                provider_id=provider_id,
                model=model,
                prompt=source,
                system=with_skills(with_specialist_guidance(base_prompt, [entry]), ctx.project.root),
                temperature=ctx.settings.temperature,
                label=f"{entry.name} Specialist Agent",
                run_id=ctx.run_id,
                settings_attrs=("graph_review_provider", "graph_review_model"),
            )
        except ProviderError as exc:
            return StepResult(step_id=step_id, step_name=step_name, status="failed", detail=str(exc))

        return StepResult(step_id=step_id, step_name=step_name, status="success", detail=review[:500], data={"full_review": review})

    return run


def build_agent_graph(selected_agents: list[AgentCatalogEntry] | tuple[AgentCatalogEntry, ...] = ()) -> dict[str, GraphNode]:
    nodes: dict[str, GraphNode] = {}

    def add(node_id: str, label: str, fn, depends_on: tuple[str, ...] = ()) -> None:
        nodes[node_id] = GraphNode(id=node_id, label=label, fn=fn, depends_on=depends_on)

    add("file_monitoring", "File Monitoring Agent", core_steps.detect_changes)
    add("project_analysis", "Project Analysis Agent", core_steps.load_project_context, ("file_monitoring",))

    add("dependency_analysis", "Dependency Agent", dependency_steps.dependency_analysis, ("project_analysis",))
    add("security_scan", "Security Agent", quality_steps.security_vulnerability_scan, ("project_analysis",))
    add("secret_detection", "Secret Detection Agent", secrets_steps.combined_secret_detection, ("project_analysis",))
    add("static_analysis", "Static Analysis Agent", quality_steps.static_code_analysis, ("project_analysis",))
    add("build_verification", "Build Agent", build_steps.build_verification, ("project_analysis",))
    add("unit_tests", "Unit Test Agent", test_steps.unit_test_execution, ("build_verification",))
    add("integration_tests", "Integration Test Agent", test_steps.integration_test_execution, ("unit_tests",))
    add("documentation_check", "Documentation Agent", doc_steps.documentation_check, ("project_analysis",))
    add("rag_retrieval", "RAG Retrieval Agent", ai_steps.rag_knowledge_retrieval, ("project_analysis",))
    add("ollama_review", "Ollama Review Agent", ai_steps.ollama_code_review, ("project_analysis",))
    add("architecture_validation", "Architecture Review Agent", ai_steps.architecture_validation, ("project_analysis",))
    add(
        "code_improvement", "Code Improvement Agent", ai_steps.suggest_code_improvements,
        ("security_scan", "build_verification", "unit_tests", "static_analysis"),
    )

    for entry in selected_agents:
        add(f"specialist_{entry.slug}", f"{entry.name} (Specialist Agent)", _make_specialist_node_fn(entry), ("project_analysis",))

    downstream_of_project_analysis = tuple(
        node_id for node_id in nodes if node_id not in ("file_monitoring", "project_analysis")
    )
    add("report_generation", "Report Generation Agent", graph_steps.merge_results_report, downstream_of_project_analysis)
    add("final_verification", "Final Verification Agent", graph_steps.final_verification, ("report_generation",))

    return nodes
