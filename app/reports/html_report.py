"""HTML report writer (Jinja2, template inlined — no external template files)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from app.reports.report_generator import EngineeringReport

_TEMPLATE = Template(
    """<!doctype html>
<html><head><meta charset="utf-8"><title>Engineering Report — {{ report.pipeline }}</title>
<style>
body { font-family: 'Segoe UI', sans-serif; background:#1e1f22; color:#d4d4d8; padding:24px; }
h1 { color: #2f81f7; }
.status-PASSED { color:#3fb950; font-weight:bold; }
.status-FAILED { color:#f85149; font-weight:bold; }
table { border-collapse: collapse; width:100%; margin-top:16px; }
th, td { border:1px solid #33353a; padding:8px; text-align:left; vertical-align:top; }
th { background:#26282c; }
.success { color:#3fb950; }
.failed { color:#f85149; }
.skipped { color:#8b8f98; }
</style></head>
<body>
<h1>{{ report.pipeline | capitalize }} Engineering Report</h1>
<p>Project: {{ report.project_path }}</p>
<p>Run ID: {{ report.run_id }} &mdash; Generated: {{ report.generated_at }}</p>
<p>Status: <span class="status-{{ report.overall_status }}">{{ report.overall_status }}</span>
 ({{ report.passed }} passed, {{ report.failed }} failed, {{ report.skipped }} skipped)</p>
<table>
<tr><th>Step</th><th>Status</th><th>Detail</th></tr>
{% for step in report.steps %}
<tr><td>{{ step.step_name }}</td><td class="{{ step.status }}">{{ step.status }}</td><td>{{ step.detail }}</td></tr>
{% endfor %}
</table>
</body></html>
"""
)


def write_html_report(report: EngineeringReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.render(report=report), encoding="utf-8")
    return path
