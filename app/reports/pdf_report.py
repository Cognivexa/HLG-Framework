"""PDF report writer via reportlab (builds the PDF directly from structured
data — no HTML-to-PDF conversion, which would need native OS dependencies)."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reports.report_generator import EngineeringReport

_STATUS_COLORS = {
    "success": colors.HexColor("#1a7f37"),
    "failed": colors.HexColor("#cf222e"),
    "skipped": colors.HexColor("#57606a"),
}


def write_pdf_report(report: EngineeringReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=LETTER)

    elements = [
        Paragraph(f"{report.pipeline.capitalize()} Engineering Report", styles["Title"]),
        Paragraph(f"Project: {report.project_path}", styles["Normal"]),
        Paragraph(f"Run ID: {report.run_id} — Generated: {report.generated_at}", styles["Normal"]),
        Paragraph(
            f"Status: {report.overall_status} "
            f"({report.passed} passed, {report.failed} failed, {report.skipped} skipped)",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]

    data = [["Step", "Status", "Detail"]] + [
        [step["step_name"], step["status"], step["detail"][:200]] for step in report.steps
    ]
    table = Table(data, colWidths=[160, 60, 280])

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#26282c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for row_idx, step in enumerate(report.steps, start=1):
        color = _STATUS_COLORS.get(step["status"])
        if color:
            style_commands.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), color))
    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    doc.build(elements)
    return path
