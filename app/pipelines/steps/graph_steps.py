"""Graph-only synthetic nodes: report aggregation and final verification.

These read the PipelineContext.results dict already populated by sibling DAG
nodes rather than performing new analysis of their own.
"""
from __future__ import annotations

from app.pipelines.base import PipelineContext, StepResult

_DECISION_STEP_IDS = (
    "dependency_analysis",
    "security_scan",
    "secret_detection",
    "static_analysis",
    "build_verification",
    "unit_tests",
    "integration_tests",
    "documentation_check",
    "architecture_validation",
)


def merge_results_report(ctx: PipelineContext) -> StepResult:
    summary = {step_id: {"status": r.status, "detail": r.detail} for step_id, r in ctx.results.items()}
    failed = [step_id for step_id, r in summary.items() if r["status"] == "failed"]
    detail = "All agent results merged." + (f" {len(failed)} finding(s) need attention." if failed else "")
    return StepResult(
        step_id="report_generation", step_name="Generate final engineering report", status="success",
        detail=detail, data={"summary": summary},
    )


def final_verification(ctx: PipelineContext) -> StepResult:
    failed = [
        step_id for step_id in _DECISION_STEP_IDS
        if ctx.results.get(step_id) and ctx.results[step_id].status == "failed"
    ]
    if failed:
        return StepResult(
            step_id="final_verification", step_name="Final verification decision", status="failed",
            detail=f"REJECTED — {len(failed)} check(s) failing: {', '.join(failed)}",
        )
    return StepResult(
        step_id="final_verification", step_name="Final verification decision", status="success",
        detail="APPROVED — all checks passed.",
    )
