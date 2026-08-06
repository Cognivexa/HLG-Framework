"""Static analysis and code-quality inspection via ruff, run with this app's own
bundled interpreter (ruff analyzes source text — it needs no target-project
dependencies installed, unlike pytest)."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Bandit-equivalent security ruleset for the "security vulnerability scan" step.
# S101 (assert-detected) is excluded: asserts are idiomatic in pytest test files,
# not a real vulnerability, and would otherwise fail this step on every project
# that has tests.
SECURITY_SCAN_RULES = "S"
SECURITY_SCAN_IGNORE = "S101"
# Correctness/bug-risk oriented ruleset for the "static analysis" step.
STATIC_ANALYSIS_RULES = "E,F,B"
# Style/complexity/naming/maintainability ruleset for the "code quality" step.
CODE_QUALITY_RULES = "C90,N,SIM"


@dataclass
class LintFinding:
    file: str
    line: int
    code: str
    message: str


def _run_ruff(files: list[Path], select: str, ignore: str = "") -> tuple[list[LintFinding], str]:
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return [], ""
    args = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--select",
        select,
    ]
    if ignore:
        args += ["--ignore", ignore]
    args += ["--output-format", "json", *[str(f) for f in py_files]]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=90)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return [], f"ruff unavailable: {exc}"

    if not proc.stdout.strip():
        return [], "" if proc.returncode == 0 else proc.stderr.strip()[:300]

    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], "Could not parse ruff output"

    findings = [
        LintFinding(
            file=entry.get("filename", ""),
            line=(entry.get("location") or {}).get("row", 0),
            code=entry.get("code", "") or "",
            message=entry.get("message", ""),
        )
        for entry in raw
    ]
    return findings, ""


def run_security_scan(files: list[Path]) -> tuple[list[LintFinding], str]:
    return _run_ruff(files, SECURITY_SCAN_RULES, ignore=SECURITY_SCAN_IGNORE)


def run_static_analysis(files: list[Path]) -> tuple[list[LintFinding], str]:
    return _run_ruff(files, STATIC_ANALYSIS_RULES)


def run_code_quality(files: list[Path]) -> tuple[list[LintFinding], str]:
    return _run_ruff(files, CODE_QUALITY_RULES)
