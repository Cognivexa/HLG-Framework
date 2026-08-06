"""Aggregates live system + pipeline metrics for the Dashboard: CPU/memory
via psutil, queue/running counts from the PipelineController, and
security/quality scores + build/test status + the latest AI decision text
read from the most recent run's report.json (see reports/history.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import psutil

from app.reports.history import list_runs

_SECURITY_STEP_IDS = {
    "scan_api_keys", "scan_secrets", "detect_passwords", "detect_private_keys",
    "security_scan", "secret_detection",
}
_QUALITY_STEP_IDS = {"static_analysis", "code_quality"}
_AI_STEP_IDS = ("ollama_review", "loop_verdict", "final_verification", "code_improvement")

# Shared with the Eval tab (eval_widget.py) and the browser mirror
# (web/static/index.html, kept in sync by hand): every Harness/Loop/Graph
# step is either a deterministic check (pytest/ruff/pip-audit — same result
# every time for the same code) or an LLM-as-judge call (a model's opinion,
# which can vary). Nothing here is scored by an LLM grading another LLM;
# both columns come straight from real step results already on the bus.
DETERMINISTIC_STEP_IDS = {
    "build_verification", "unit_tests", "integration_tests", "security_scan", "static_analysis",
    "code_quality", "dependency_analysis", "secret_detection", "scan_api_keys", "scan_secrets",
    "detect_passwords", "detect_private_keys",
}
LLM_JUDGE_STEP_IDS = {"ollama_review", "architecture_validation", "final_verification", "code_improvement", "loop_verdict"}


@dataclass
class DashboardSnapshot:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    queue_size: int = 0
    running_count: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    security_score: int | None = None
    quality_score: int | None = None
    build_status: str = "unknown"
    test_status: str = "unknown"
    latest_ai_decision: str = ""
    overall_health: str = "Unknown"


def read_latest_report_steps(pipeline: str | None = None) -> list[dict]:
    """The step list from the most recent run's report.json — optionally
    restricted to one pipeline (e.g. "harness", the one the Eval tab cares
    about, since Loop/Graph re-run the same checks rather than defining new
    ones)."""
    runs = list_runs()
    if pipeline:
        runs = [r for r in runs if r.get("pipeline") == pipeline]
    if not runs:
        return []
    report_dir = runs[0].get("report_dir")
    if not report_dir:
        return []
    report_file = Path(report_dir) / "report.json"
    if not report_file.exists():
        return []
    try:
        data = json.loads(report_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("steps", [])


def _score_for(steps: list[dict], relevant_ids: set[str]) -> int | None:
    matched = [s for s in steps if s.get("step_id") in relevant_ids and s.get("status") in ("success", "failed")]
    if not matched:
        return None
    passed = sum(1 for s in matched if s["status"] == "success")
    return round(100 * passed / len(matched))


def _status_for(steps: list[dict], step_id: str) -> str:
    for s in steps:
        if s.get("step_id") == step_id:
            return s.get("status", "unknown")
    return "unknown"


def _latest_ai_decision(steps: list[dict]) -> str:
    for step_id in _AI_STEP_IDS:
        for s in steps:
            if s.get("step_id") == step_id and s.get("detail"):
                return f"{s['step_id']}: {s['detail'][:200]}"
    return ""


def _overall_health(security_score, quality_score, failed_jobs, completed_jobs) -> str:
    if completed_jobs == 0 and failed_jobs == 0:
        return "Unknown"
    if failed_jobs > 0 and failed_jobs >= completed_jobs:
        return "Critical"
    scores = [s for s in (security_score, quality_score) if s is not None]
    if scores and min(scores) < 60:
        return "Warning"
    if failed_jobs > 0:
        return "Warning"
    return "Good"


def build_snapshot(pipeline_controller=None) -> DashboardSnapshot:
    runs = list_runs()
    completed_jobs = sum(1 for r in runs if r.get("overall_status") == "PASSED")
    failed_jobs = sum(1 for r in runs if r.get("overall_status") == "FAILED")

    steps = read_latest_report_steps()
    security_score = _score_for(steps, _SECURITY_STEP_IDS)
    quality_score = _score_for(steps, _QUALITY_STEP_IDS)

    queue_size = pipeline_controller.pending_count() if pipeline_controller else 0
    running_count = pipeline_controller.running_count() if pipeline_controller else 0

    return DashboardSnapshot(
        cpu_percent=psutil.cpu_percent(interval=None),
        memory_percent=psutil.virtual_memory().percent,
        queue_size=queue_size,
        running_count=running_count,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        security_score=security_score,
        quality_score=quality_score,
        build_status=_status_for(steps, "build_verification"),
        test_status=_status_for(steps, "unit_tests"),
        latest_ai_decision=_latest_ai_decision(steps),
        overall_health=_overall_health(security_score, quality_score, failed_jobs, completed_jobs),
    )
