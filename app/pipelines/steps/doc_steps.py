"""Documentation Agent: real docstring-coverage check via Python's ast module
(no LLM call — this is a fast, deterministic structural check)."""
from __future__ import annotations

import ast
from pathlib import Path

from app.pipelines.base import PipelineContext, StepResult


def _docstring_coverage(path: Path) -> tuple[int, int]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return 0, 0
    total = documented = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            total += 1
            if ast.get_docstring(node):
                documented += 1
    return documented, total


def documentation_check(ctx: PipelineContext) -> StepResult:
    documented = total = 0
    for f in ctx.changed_files:
        path = Path(f)
        if path.suffix != ".py" or not path.exists():
            continue
        d, t = _docstring_coverage(path)
        documented += d
        total += t

    if total == 0:
        return StepResult(
            step_id="documentation_check", step_name="Documentation coverage", status="skipped",
            detail="No documentable modules/classes/functions in this change set.",
        )

    ratio = documented / total
    status = "success" if ratio >= 0.5 else "failed"
    detail = f"{documented}/{total} module(s)/class(es)/function(s) documented ({ratio:.0%})."
    return StepResult(step_id="documentation_check", step_name="Documentation coverage", status=status, detail=detail)
