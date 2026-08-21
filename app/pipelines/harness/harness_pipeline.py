"""The declarative 21-step Harness Engineering pipeline.

Each step is a thin wrapper (see app/pipelines/steps/) around a real,
independently testable implementation in app/security or app/analysis. The
Graph orchestrator wraps these same step functions as DAG nodes, so "Harness"
and "Graph" views never diverge on what a given check actually does.

Steps declare `depends_on` and PipelineRunner executes independent ones
concurrently — the only genuine data dependencies are the secret-scan cache
(the 5 category checks after scan_api_keys reuse its cached scan rather than
racing to populate it) and the build -> unit tests -> integration tests
chain. Everything else (security/static/quality/dependency analysis, the
Ollama review, RAG retrieval, architecture checks) is independent and runs
in parallel, which is what makes this materially faster than a strictly
sequential 21-step run while keeping the exact same fixed display order
(see PipelineRunner.announce).
"""
from __future__ import annotations

from app.core.agent_catalog import select_for_changed_files
from app.core.events import PipelineEvent, bus
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.core.project_context import ProjectContext, build_project_context
from app.pipelines.base import PipelineContext, PipelineRunner, Step, new_run_id
from app.pipelines.steps import ai_steps, build_steps, core_steps, dependency_steps, doc_steps, quality_steps, secrets_steps, test_steps
from app.reports.report_generator import generate_and_save_reports

logger = get_logger(__name__)

HARNESS_STEPS: list[Step] = [
    Step("detect_changes", "Detect file changes", core_steps.detect_changes),
    Step("identify_affected", "Identify affected project files", core_steps.identify_affected_files),
    Step("load_context", "Load project context", core_steps.load_project_context),
    Step("select_specialist_agents", "Select specialist agents/skills", core_steps.select_specialist_agents),
    Step("scan_api_keys", "Scan for API keys", secrets_steps.scan_api_keys),
    Step("scan_secrets", "Scan for secrets", secrets_steps.scan_secrets, depends_on=("scan_api_keys",)),
    Step("detect_passwords", "Detect passwords", secrets_steps.detect_passwords, depends_on=("scan_api_keys",)),
    Step("detect_private_keys", "Detect private keys", secrets_steps.detect_private_keys, depends_on=("scan_api_keys",)),
    Step("detect_pii", "Detect PII", secrets_steps.detect_pii, depends_on=("scan_api_keys",)),
    Step("detect_phi", "Detect PHI", secrets_steps.detect_phi, depends_on=("scan_api_keys",)),
    Step("security_scan", "Security vulnerability scan", quality_steps.security_vulnerability_scan),
    Step("dependency_analysis", "Dependency analysis", dependency_steps.dependency_analysis),
    Step("static_analysis", "Static code analysis", quality_steps.static_code_analysis),
    Step("code_quality", "Code quality inspection", quality_steps.code_quality_inspection),
    Step("documentation_check", "Documentation coverage", doc_steps.documentation_check),
    Step("build_verification", "Build verification", build_steps.build_verification),
    Step("unit_tests", "Unit test execution", test_steps.unit_test_execution, depends_on=("build_verification",)),
    Step("integration_tests", "Integration test execution", test_steps.integration_test_execution, depends_on=("unit_tests",)),
    Step("ollama_review", "Ollama AI code review", ai_steps.ollama_code_review),
    Step("rag_retrieval", "RAG knowledge retrieval", ai_steps.rag_knowledge_retrieval),
    Step("architecture_validation", "Architecture validation", ai_steps.architecture_validation),
    Step("generate_report", "Generate engineering report", core_steps.generate_engineering_report),
]


def build_harness_runner() -> PipelineRunner:
    from app.plugins.loader import get_registry

    steps = list(HARNESS_STEPS)
    for plugin_step in get_registry().steps.values():
        steps.append(Step(plugin_step.id, plugin_step.name, plugin_step.run))

    # generate_report aggregates ctx.results for every other step (built-in
    # or plugin), so it must depend on all of them regardless of what's
    # registered at runtime.
    report_step = next(s for s in steps if s.id == "generate_report")
    report_step.depends_on = tuple(s.id for s in steps if s.id != "generate_report")

    return PipelineRunner("harness", steps)


def run_harness_pipeline(
    project_path: str,
    changed_files: list[str],
    settings,
    llm_client: LLMClient,
    project: ProjectContext | None = None,
) -> PipelineContext:
    run_id = new_run_id()
    project = project or build_project_context(project_path)
    ctx = PipelineContext(
        run_id=run_id,
        project_path=project_path,
        project=project,
        changed_files=changed_files,
        settings=settings,
        llm_client=llm_client,
        selected_agents=select_for_changed_files(changed_files),
    )

    runner = build_harness_runner()
    runner.announce(run_id)
    bus.pipeline_updated.emit(PipelineEvent(pipeline="harness", run_id=run_id, project_path=project_path, status="started"))
    logger.info("Harness run %s started for %s (%d changed file(s))", run_id, project_path, len(changed_files))

    runner.run(ctx)

    failed_steps = [r.step_name for r in ctx.results.values() if r.status == "failed"]
    status = "failed" if failed_steps else "completed"
    summary = "Completed successfully." if not failed_steps else f"{len(failed_steps)} step(s) failed."
    bus.pipeline_updated.emit(
        PipelineEvent(pipeline="harness", run_id=run_id, project_path=project_path, status=status, summary=summary)
    )
    logger.info("Harness run %s %s: %s", run_id, status, summary)
    generate_and_save_reports("harness", ctx)
    return ctx
