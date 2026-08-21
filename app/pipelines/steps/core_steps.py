"""Steps 1-3 (change detection / context loading) and step 18 (report
generation) of the Harness pipeline — cheap, deterministic bookkeeping."""
from __future__ import annotations

from app.core.agent_catalog import format_selection_summary
from app.pipelines.base import PipelineContext, StepResult


def detect_changes(ctx: PipelineContext) -> StepResult:
    count = len(ctx.changed_files)
    return StepResult(
        step_id="detect_changes",
        step_name="Detect file changes",
        status="success",
        detail=f"{count} changed file(s) triggered this run.",
        data={"changed_files": ctx.changed_files},
    )


def identify_affected_files(ctx: PipelineContext) -> StepResult:
    affected = [f for f in ctx.changed_files if f.endswith(".py")]
    return StepResult(
        step_id="identify_affected",
        step_name="Identify affected project files",
        status="success",
        detail=f"{len(affected)} Python file(s) affected.",
        data={"affected_files": affected},
    )


def select_specialist_agents(ctx: PipelineContext) -> StepResult:
    """Reports the specialist agents/skills (app.core.agent_catalog) already
    auto-selected for `ctx.changed_files` — selection itself happens once,
    up front in `run_*_pipeline`, before this step (or any other) runs, so
    every step sees the same list regardless of execution order."""
    entries = ctx.selected_agents
    return StepResult(
        step_id="select_specialist_agents",
        step_name="Select specialist agents/skills",
        status="success",
        detail=format_selection_summary(entries, len(ctx.changed_files)),
        data={"selected": [e.slug for e in entries]},
    )


def load_project_context(ctx: PipelineContext) -> StepResult:
    project = ctx.project
    detail = (
        f"Root: {project.root} | Python: {project.python_executable} | "
        f"Build files: {', '.join(project.build_files) or 'none'} | "
        f"{len(project.source_files)} tracked source file(s)."
    )
    return StepResult(step_id="load_context", step_name="Load project context", status="success", detail=detail)


def generate_engineering_report(ctx: PipelineContext) -> StepResult:
    summary = {step_id: {"status": r.status, "detail": r.detail} for step_id, r in ctx.results.items()}
    failed = [step_id for step_id, r in summary.items() if r["status"] == "failed"]
    detail = "All prior steps passed." if not failed else f"{len(failed)} step(s) failed: {', '.join(failed)}"
    return StepResult(
        step_id="generate_report",
        step_name="Generate engineering report",
        status="success",
        detail=detail,
        data={"summary": summary},
    )
