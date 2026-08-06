"""Step 9: dependency analysis (declared packages + best-effort pip-audit)."""
from __future__ import annotations

from app.pipelines.base import PipelineContext, StepResult
from app.security.dependency_scanner import run_dependency_analysis


def dependency_analysis(ctx: PipelineContext) -> StepResult:
    report = run_dependency_analysis(ctx.project.root)

    if report.audit_skipped_reason:
        detail = f"{len(report.declared_packages)} declared package(s). Vulnerability audit skipped: {report.audit_skipped_reason}"
        return StepResult(step_id="dependency_analysis", step_name="Dependency analysis", status="skipped", detail=detail)

    if report.vulnerabilities:
        names = ", ".join(sorted({f"{v.package}=={v.installed_version} ({v.vulnerability_id})" for v in report.vulnerabilities[:5]}))
        detail = f"{len(report.vulnerabilities)} known vulnerability finding(s): {names}"
        return StepResult(
            step_id="dependency_analysis",
            step_name="Dependency analysis",
            status="failed",
            detail=detail,
            data={"count": len(report.vulnerabilities)},
        )

    detail = f"{len(report.declared_packages)} declared package(s), no known vulnerabilities."
    return StepResult(step_id="dependency_analysis", step_name="Dependency analysis", status="success", detail=detail)
