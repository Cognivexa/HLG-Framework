"""Tests for report generation (build_report + JSON/HTML/PDF writers)."""
from __future__ import annotations

import json

from app.pipelines.base import PipelineContext, StepResult
from app.reports.html_report import write_html_report
from app.reports.json_report import write_json_report
from app.reports.pdf_report import write_pdf_report
from app.reports.report_generator import build_report


def _make_ctx() -> PipelineContext:
    ctx = PipelineContext(
        run_id="report-test", project_path="C:\\fake\\project", project=None,
        changed_files=[], settings=None, llm_client=None,
    )
    ctx.results = {
        "a": StepResult(step_id="a", step_name="A", status="success", detail="ok"),
        "b": StepResult(step_id="b", step_name="B", status="failed", detail="broke"),
        "c": StepResult(step_id="c", step_name="C", status="skipped", detail="n/a"),
    }
    return ctx


def test_build_report_counts_statuses():
    report = build_report("harness", _make_ctx())
    assert report.passed == 1
    assert report.failed == 1
    assert report.skipped == 1
    assert report.overall_status == "FAILED"


def test_build_report_passes_when_nothing_failed():
    ctx = _make_ctx()
    ctx.results = {"a": StepResult(step_id="a", step_name="A", status="success")}
    report = build_report("harness", ctx)
    assert report.overall_status == "PASSED"


def test_write_json_report_round_trips(tmp_path):
    report = build_report("harness", _make_ctx())
    path = write_json_report(report, tmp_path / "report.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == "report-test"
    assert data["overall_status"] == "FAILED"
    assert len(data["steps"]) == 3


def test_write_html_report_contains_step_names(tmp_path):
    report = build_report("harness", _make_ctx())
    path = write_html_report(report, tmp_path / "report.html")
    html = path.read_text(encoding="utf-8")
    assert "<html" in html
    assert "A" in html and "B" in html


def test_write_pdf_report_produces_valid_pdf(tmp_path):
    report = build_report("harness", _make_ctx())
    path = write_pdf_report(report, tmp_path / "report.pdf")
    assert path.read_bytes()[:5] == b"%PDF-"
