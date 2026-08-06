"""Steps 8, 10, 11: security vulnerability scan, static analysis, code quality.

All three are ruff invocations with a different rule selection — see
app.analysis.static_analysis for the exact rulesets and why they don't
overlap with each other.
"""
from __future__ import annotations

from pathlib import Path

from app.analysis.static_analysis import run_code_quality, run_security_scan, run_static_analysis
from app.pipelines.base import PipelineContext, StepResult


def _lint_result(step_id: str, step_name: str, files: list[Path], runner) -> StepResult:
    findings, error = runner(files)
    if error:
        return StepResult(step_id=step_id, step_name=step_name, status="skipped", detail=error)
    if findings:
        detail = "; ".join(f"{f.code} {Path(f.file).name}:{f.line} — {f.message}" for f in findings[:5])
        if len(findings) > 5:
            detail += f" (+{len(findings) - 5} more)"
        locations = [{"file": f.file, "line": f.line} for f in findings]
        return StepResult(
            step_id=step_id, step_name=step_name, status="failed", detail=detail,
            data={"count": len(findings), "locations": locations},
        )
    return StepResult(step_id=step_id, step_name=step_name, status="success", detail="No issues found.")


def security_vulnerability_scan(ctx: PipelineContext) -> StepResult:
    files = [Path(f) for f in ctx.changed_files]
    return _lint_result("security_scan", "Security vulnerability scan", files, run_security_scan)


def static_code_analysis(ctx: PipelineContext) -> StepResult:
    files = [Path(f) for f in ctx.changed_files]
    return _lint_result("static_analysis", "Static code analysis", files, run_static_analysis)


def code_quality_inspection(ctx: PipelineContext) -> StepResult:
    files = [Path(f) for f in ctx.changed_files]
    return _lint_result("code_quality", "Code quality inspection", files, run_code_quality)
