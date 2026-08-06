"""Example plugin: scans changed files for TODO/FIXME comments.

To install: copy this file into
    %LOCALAPPDATA%\\HLGFramework\\plugins\\installed\\
and restart the app (or use Settings to reload plugins). It will then appear
as an extra step at the end of every Harness Engineering run.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.pipelines.base import PipelineContext, StepResult
from app.plugins.base import PluginStep

_PATTERN = re.compile(r"#\s*(TODO|FIXME)\b", re.IGNORECASE)


class TodoScannerStep(PluginStep):
    id = "todo_scanner"
    name = "TODO/FIXME comment scanner"

    def run(self, ctx: PipelineContext) -> StepResult:
        findings = []
        for file_path in ctx.changed_files:
            path = Path(file_path)
            if path.suffix != ".py" or not path.exists():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if _PATTERN.search(line):
                    findings.append(f"{path.name}:{lineno}")

        if findings:
            detail = f"{len(findings)} TODO/FIXME comment(s): {', '.join(findings[:5])}"
            return StepResult(step_id=self.id, step_name=self.name, status="failed", detail=detail)
        return StepResult(step_id=self.id, step_name=self.name, status="success", detail="No TODO/FIXME comments found.")


def register(registry) -> None:
    registry.register(TodoScannerStep())
