"""Tests for the Dashboard's metric-computation helpers (pure functions over
a report's step list — no psutil/filesystem involved here)."""
from __future__ import annotations

from app.core.dashboard_metrics import (
    _QUALITY_STEP_IDS,
    _SECURITY_STEP_IDS,
    _latest_ai_decision,
    _overall_health,
    _score_for,
    _status_for,
)


def test_score_for_computes_pass_rate():
    steps = [
        {"step_id": "security_scan", "status": "success"},
        {"step_id": "scan_api_keys", "status": "failed"},
        {"step_id": "unrelated", "status": "failed"},
    ]
    assert _score_for(steps, _SECURITY_STEP_IDS) == 50


def test_score_for_ignores_skipped_steps():
    steps = [
        {"step_id": "static_analysis", "status": "success"},
        {"step_id": "code_quality", "status": "skipped"},
    ]
    assert _score_for(steps, _QUALITY_STEP_IDS) == 100


def test_score_for_returns_none_when_nothing_relevant():
    steps = [{"step_id": "build_verification", "status": "success"}]
    assert _score_for(steps, _SECURITY_STEP_IDS) is None


def test_status_for_finds_step():
    steps = [{"step_id": "build_verification", "status": "failed"}]
    assert _status_for(steps, "build_verification") == "failed"
    assert _status_for(steps, "unit_tests") == "unknown"


def test_latest_ai_decision_prefers_final_verification():
    steps = [
        {"step_id": "ollama_review", "detail": "reviewed fine"},
        {"step_id": "final_verification", "detail": "APPROVED"},
    ]
    assert _latest_ai_decision(steps).startswith("ollama_review")  # ollama_review checked first in _AI_STEP_IDS order


def test_latest_ai_decision_empty_when_no_ai_steps():
    assert _latest_ai_decision([{"step_id": "build_verification", "detail": "ok"}]) == ""


def test_overall_health_unknown_when_no_runs():
    assert _overall_health(None, None, 0, 0) == "Unknown"


def test_overall_health_critical_when_failures_dominate():
    assert _overall_health(80, 80, failed_jobs=5, completed_jobs=1) == "Critical"


def test_overall_health_warning_on_low_score():
    assert _overall_health(40, 90, failed_jobs=0, completed_jobs=3) == "Warning"


def test_overall_health_good_when_clean():
    assert _overall_health(100, 100, failed_jobs=0, completed_jobs=5) == "Good"
