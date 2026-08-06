"""Dependency inventory + best-effort vulnerability check.

Declared-package parsing is fully offline. The vulnerability check
(pip-audit against PyPI/OSV) genuinely needs network access — that's a
property of CVE data, not something a local app can fake — so it is run
best-effort using this app's own bundled pip-audit and reported as
"skipped (offline)" rather than pretending to have a bundled CVE database.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DependencyFinding:
    package: str
    installed_version: str
    vulnerability_id: str
    description: str
    fix_versions: list[str] = field(default_factory=list)


@dataclass
class DependencyReport:
    declared_packages: list[str]
    vulnerabilities: list[DependencyFinding]
    audit_skipped_reason: str = ""


def _read_declared_packages(project_root: Path) -> list[str]:
    packages: list[str] = []
    req_file = project_root / "requirements.txt"
    if req_file.exists():
        for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                packages.append(line)
    return packages


def run_dependency_analysis(project_root: Path) -> DependencyReport:
    """Runs pip-audit (bundled with this app, via sys.executable) against the
    project's requirements.txt. Uses this app's own interpreter, not the
    monitored project's, since pip-audit only needs to *read* the requirements
    file — it does not need the project's packages actually installed.
    """
    declared = _read_declared_packages(project_root)
    req_file = project_root / "requirements.txt"

    if not req_file.exists():
        return DependencyReport(
            declared_packages=declared,
            vulnerabilities=[],
            audit_skipped_reason="No requirements.txt found (pyproject.toml dependency audit not yet supported)",
        )

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", str(req_file), "--format", "json", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            # This step needs the OSV network feed by nature and can legitimately
            # take 30-40s even when online. 45s (down from the old 120s) still
            # caps a fully-offline machine's stall without cutting off a normal,
            # just-slow-network run — and now that Harness runs steps
            # concurrently, this no longer blocks the rest of the pipeline.
            timeout=45,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return DependencyReport(declared_packages=declared, vulnerabilities=[], audit_skipped_reason=f"pip-audit unavailable: {exc}")

    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        reason = proc.stderr.strip()[:300] or "Could not parse pip-audit output (likely offline)"
        return DependencyReport(declared_packages=declared, vulnerabilities=[], audit_skipped_reason=reason)

    findings: list[DependencyFinding] = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            findings.append(
                DependencyFinding(
                    package=dep.get("name", ""),
                    installed_version=dep.get("version", ""),
                    vulnerability_id=vuln.get("id", ""),
                    description=(vuln.get("description", "") or "")[:300],
                    fix_versions=vuln.get("fix_versions", []),
                )
            )

    return DependencyReport(declared_packages=declared, vulnerabilities=findings)
