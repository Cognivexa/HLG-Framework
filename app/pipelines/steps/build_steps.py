"""Step 12: build verification (compile-check via the project's own interpreter)."""
from __future__ import annotations

from pathlib import Path

from app.analysis.build_runner import run_build_verification
from app.pipelines.base import PipelineContext, StepResult


def build_verification(ctx: PipelineContext) -> StepResult:
    files = [Path(f) for f in ctx.changed_files]
    result = run_build_verification(ctx.project.python_executable, files)
    status = "success" if result.success else "failed"
    return StepResult(step_id="build_verification", step_name="Build verification", status=status, detail=result.output[:500])
