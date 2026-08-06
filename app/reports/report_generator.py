"""Builds a structured engineering report from any pipeline's PipelineContext
(Harness, Loop, and Graph all populate the same ctx.results shape), then
writes it out in all three formats and records it in the run history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.pipelines.base import PipelineContext


@dataclass
class EngineeringReport:
    run_id: str
    pipeline: str
    project_path: str
    generated_at: str
    steps: list[dict] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def overall_status(self) -> str:
        return "FAILED" if self.failed else "PASSED"


def build_report(pipeline: str, ctx: PipelineContext) -> EngineeringReport:
    steps = []
    passed = failed = skipped = 0
    for step_id, result in ctx.results.items():
        steps.append({"step_id": step_id, "step_name": result.step_name, "status": result.status, "detail": result.detail})
        if result.status == "success":
            passed += 1
        elif result.status == "failed":
            failed += 1
        elif result.status == "skipped":
            skipped += 1

    return EngineeringReport(
        run_id=ctx.run_id,
        pipeline=pipeline,
        project_path=ctx.project_path,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        steps=steps,
        passed=passed,
        failed=failed,
        skipped=skipped,
    )


def generate_and_save_reports(pipeline: str, ctx: PipelineContext) -> dict:
    # Local imports: these modules import EngineeringReport from this module
    # at their own top level, so importing them back at this module's top
    # level would create a circular import.
    from app.config.settings import REPORTS_DIR
    from app.core.events import bus
    from app.reports.history import record_run
    from app.reports.html_report import write_html_report
    from app.reports.json_report import write_json_report
    from app.reports.pdf_report import write_pdf_report

    report = build_report(pipeline, ctx)
    run_dir = REPORTS_DIR / report.run_id

    json_path = write_json_report(report, run_dir / "report.json")
    html_path = write_html_report(report, run_dir / "report.html")
    pdf_path = write_pdf_report(report, run_dir / "report.pdf")

    record_run(
        {
            "run_id": report.run_id,
            "pipeline": pipeline,
            "project_path": report.project_path,
            "generated_at": report.generated_at,
            "overall_status": report.overall_status,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "report_dir": str(run_dir),
        }
    )

    bus.report_ready.emit(report.run_id, str(run_dir))
    return {"json": str(json_path), "html": str(html_path), "pdf": str(pdf_path), "dir": str(run_dir)}
