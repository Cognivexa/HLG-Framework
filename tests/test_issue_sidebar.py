"""Tests for the issue sidebar's classification and location-extraction
logic (the pure functions the widget itself just calls into)."""
from __future__ import annotations

from app.core.events import StepEvent
from app.ui.widgets.issue_sidebar import _classify, _extract_locations


def _event(step_id, detail="", data=None, status="failed"):
    return StepEvent(pipeline="harness", run_id="r1", step_id=step_id, step_name=step_id, status=status, detail=detail, data=data or {})


def test_classifies_security_steps():
    assert _classify(_event("scan_api_keys")) == "Security issue"
    assert _classify(_event("security_scan")) == "Security issue"
    assert _classify(_event("secret_detection")) == "Security issue"


def test_classifies_test_and_build_steps():
    assert _classify(_event("unit_tests")) == "Unit test failure"
    assert _classify(_event("integration_tests")) == "Unit test failure"
    assert _classify(_event("build_verification")) == "Build error"


def test_classifies_ai_step_as_api_error_when_detail_hints_at_it():
    event = _event("ollama_review", detail="Ollama chat call failed: connection refused")
    assert _classify(event) == "API/Provider error"


def test_classifies_ai_step_as_review_finding_otherwise():
    event = _event("ollama_review", detail="Found a bug on line 12.")
    assert _classify(event) == "AI review finding"


def test_classifies_static_analysis_steps():
    assert _classify(_event("static_analysis")) == "Static analysis"
    assert _classify(_event("dependency_analysis")) == "Static analysis"


def test_classifies_unknown_step_as_other():
    assert _classify(_event("some_new_step")) == "Other"


def test_extract_locations_prefers_structured_data():
    event = _event("scan_api_keys", detail="ignored", data={"locations": [{"file": "a.py", "line": 3}]})
    assert _extract_locations(event) == [{"file": "a.py", "line": 3}]


def test_extract_locations_falls_back_to_regex_on_detail():
    event = _event("build_verification", detail="SyntaxError in app/main.py:42: invalid syntax")
    locations = _extract_locations(event)
    assert {"file": "app/main.py", "line": 42} in locations


def test_extract_locations_empty_when_nothing_found():
    event = _event("architecture_validation", detail="No README found at project root.")
    assert _extract_locations(event) == []
