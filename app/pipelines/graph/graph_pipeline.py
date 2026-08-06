"""Graph Engineering entry point: routes a trigger to an agent DAG and
executes it with real concurrency for independent nodes."""
from __future__ import annotations

from app.core.events import PipelineEvent, bus
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.core.project_context import ProjectContext, build_project_context
from app.pipelines.base import PipelineContext, new_run_id
from app.pipelines.graph.graph_executor import run_graph
from app.pipelines.graph.orchestrator import route
from app.reports.report_generator import generate_and_save_reports

logger = get_logger(__name__)


def run_graph_pipeline(
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
    )

    bus.pipeline_updated.emit(PipelineEvent(pipeline="graph", run_id=run_id, project_path=project_path, status="started"))
    logger.info("Graph run %s started for %s (%d changed file(s))", run_id, project_path, len(changed_files))

    nodes = route("file_saved")
    run_graph(nodes, ctx, run_id)

    final = ctx.results.get("final_verification")
    status = "completed" if final and final.status == "success" else "failed"
    summary = final.detail if final else "No final verification result."
    bus.pipeline_updated.emit(PipelineEvent(pipeline="graph", run_id=run_id, project_path=project_path, status=status, summary=summary))
    logger.info("Graph run %s %s: %s", run_id, status, summary)
    generate_and_save_reports("graph", ctx)
    return ctx
