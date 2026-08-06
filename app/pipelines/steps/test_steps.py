"""Steps 13-14: unit and integration test execution via the project's own pytest."""
from __future__ import annotations

from app.analysis.test_runner import run_integration_tests, run_unit_tests
from app.pipelines.base import PipelineContext, StepResult


def unit_test_execution(ctx: PipelineContext) -> StepResult:
    result = run_unit_tests(ctx.project.python_executable, ctx.project.root, ctx.project.has_tests_dir)
    if not result.ran:
        return StepResult(step_id="unit_tests", step_name="Unit test execution", status="skipped", detail=result.skipped_reason)
    status = "success" if result.success else "failed"
    detail = f"{result.passed} passed, {result.failed} failed."
    return StepResult(step_id="unit_tests", step_name="Unit test execution", status=status, detail=detail)


def integration_test_execution(ctx: PipelineContext) -> StepResult:
    result = run_integration_tests(ctx.project.python_executable, ctx.project.root, ctx.project.has_integration_tests)
    if not result.ran:
        return StepResult(
            step_id="integration_tests", step_name="Integration test execution", status="skipped", detail=result.skipped_reason
        )
    status = "success" if result.success else "failed"
    detail = f"{result.passed} passed, {result.failed} failed."
    return StepResult(step_id="integration_tests", step_name="Integration test execution", status=status, detail=detail)
