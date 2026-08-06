"""JSON report writer."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.reports.report_generator import EngineeringReport


def write_json_report(report: EngineeringReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["overall_status"] = report.overall_status
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
