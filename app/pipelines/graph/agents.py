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


@dataclass
class GraphNode:
    id: str
    label: str
    fn: Callable[[PipelineContext], StepResult]
    depends_on: tuple[str, ...] = ()


def build_agent_graph() -> dict[str, GraphNode]:
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

    downstream_of_project_analysis = tuple(
        node_id for node_id in nodes if node_id not in ("file_monitoring", "project_analysis")
    )
    add("report_generation", "Report Generation Agent", graph_steps.merge_results_report, downstream_of_project_analysis)
    add("final_verification", "Final Verification Agent", graph_steps.final_verification, ("report_generation",))

    return nodes
