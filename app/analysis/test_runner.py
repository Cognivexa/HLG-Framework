"""Runs the monitored project's own unit/integration tests via pytest.

Executes inside the project's own Python environment (its own venv if
present, else the system interpreter) so results reflect the project's
actual dependency set, not this app's.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestRunResult:
    ran: bool
    success: bool
    passed: int
    failed: int
    output: str
    skipped_reason: str = ""


def _run_pytest(python_executable: str, cwd: Path, target: str) -> TestRunResult:
    try:
        proc = subprocess.run(
            [python_executable, "-m", "pytest", target, "-q", "--tb=short"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError as exc:
        return TestRunResult(ran=False, success=False, passed=0, failed=0, output="", skipped_reason=str(exc))
    except subprocess.TimeoutExpired:
        return TestRunResult(ran=True, success=False, passed=0, failed=0, output="Test run timed out after 300s.")

    output = proc.stdout + proc.stderr

    if proc.returncode == 5 or "no tests ran" in output.lower():
        return TestRunResult(ran=False, success=True, passed=0, failed=0, output=output, skipped_reason="No tests collected")

    if "No module named pytest" in output or "No module named 'pytest'" in output:
        return TestRunResult(
            ran=False, success=False, passed=0, failed=0, output=output,
            skipped_reason="pytest not installed in the project's environment",
        )

    # pytest's summary line format varies across versions/verbosity (e.g. with or
    # without a leading "=" banner), so search the whole output rather than
    # gating on line prefixes.
    passed_match = re.search(r"(\d+) passed", output)
    failed_match = re.search(r"(\d+) failed", output)
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0

    return TestRunResult(ran=True, success=proc.returncode == 0, passed=passed, failed=failed, output=output)


def run_unit_tests(python_executable: str, project_root: Path, has_tests_dir: bool) -> TestRunResult:
    if not has_tests_dir:
        return TestRunResult(ran=False, success=True, passed=0, failed=0, output="", skipped_reason="No tests/ directory found")
    return _run_pytest(python_executable, project_root, "tests")


def run_integration_tests(python_executable: str, project_root: Path, has_integration_tests: bool) -> TestRunResult:
    if not has_integration_tests:
        # Unlike a missing tests/ dir (a real gap Loop can act on), a
        # separate integration suite is optional — plenty of projects are
        # fully and correctly tested by unit tests alone. success=True here
        # is deliberate: this is "not applicable," not "something's missing."
        return TestRunResult(
            ran=False, success=True, passed=0, failed=0, output="",
            skipped_reason="No separate tests/integration/ suite — optional, add one only if this project needs integration-level coverage beyond its unit tests.",
        )
    return _run_pytest(python_executable, project_root, "tests/integration")
