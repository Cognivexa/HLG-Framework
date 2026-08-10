"""Steps 4-9: API key / secret / password / private-key / PII / PHI detection.

The regex+entropy scan runs once per pipeline run (memoized in ctx.cache) and
each of the six harness steps below just filters that single scan by
category — running six separate full-file scans would be wasteful busywork
for an identical result.
"""
from __future__ import annotations

from pathlib import Path

from app.pipelines.base import PipelineContext, StepResult
from app.security.secret_scanner import (
    CATEGORY_API_KEY,
    CATEGORY_PASSWORD,
    CATEGORY_PHI,
    CATEGORY_PII,
    CATEGORY_PRIVATE_KEY,
    CATEGORY_SECRET,
    SecretFinding,
    filter_by_category,
    scan_files,
)

_CACHE_KEY = "secret_scan_findings"


def _get_scan(ctx: PipelineContext) -> list[SecretFinding]:
    if _CACHE_KEY not in ctx.cache:
        files = [Path(f) for f in ctx.changed_files]
        ctx.cache[_CACHE_KEY] = scan_files(files)
    return ctx.cache[_CACHE_KEY]


def _result_for(ctx: PipelineContext, step_id: str, step_name: str, category: str) -> StepResult:
    findings = filter_by_category(_get_scan(ctx), category)
    if findings:
        detail = "; ".join(f"{f.rule_name} in {Path(f.file).name}:{f.line}" for f in findings[:5])
        if len(findings) > 5:
            detail += f" (+{len(findings) - 5} more)"
        locations = [{"file": f.file, "line": f.line, "snippet": f.snippet, "category": f.category} for f in findings]
        return StepResult(
            step_id=step_id, step_name=step_name, status="failed", detail=detail,
            data={"count": len(findings), "locations": locations},
        )
    return StepResult(step_id=step_id, step_name=step_name, status="success", detail="None found.")


def scan_api_keys(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "scan_api_keys", "Scan for API keys", CATEGORY_API_KEY)


def scan_secrets(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "scan_secrets", "Scan for secrets", CATEGORY_SECRET)


def detect_passwords(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "detect_passwords", "Detect passwords", CATEGORY_PASSWORD)


def detect_private_keys(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "detect_private_keys", "Detect private keys", CATEGORY_PRIVATE_KEY)


def detect_pii(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "detect_pii", "Detect PII (emails, usernames, payment data)", CATEGORY_PII)


def detect_phi(ctx: PipelineContext) -> StepResult:
    return _result_for(ctx, "detect_phi", "Detect PHI (SSNs, medical/patient identifiers)", CATEGORY_PHI)


def combined_secret_detection(ctx: PipelineContext) -> StepResult:
    """Graph Engineering's Secret Detection Agent: one node covering all six
    categories that Harness Engineering shows as separate steps."""
    findings = _get_scan(ctx)
    if not findings:
        return StepResult(step_id="secret_detection", step_name="Secret detection", status="success", detail="None found.")

    by_category: dict[str, int] = {}
    for finding in findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    detail = ", ".join(f"{category}: {count}" for category, count in sorted(by_category.items()))
    locations = [{"file": f.file, "line": f.line, "snippet": f.snippet, "category": f.category} for f in findings]
    return StepResult(
        step_id="secret_detection", step_name="Secret detection", status="failed", detail=detail,
        data={"count": len(findings), "locations": locations},
    )
