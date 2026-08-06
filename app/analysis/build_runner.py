"""Build verification for Python projects.

Pure Python has no universal "build" step, so this performs a compile-time
check (`python -m compileall`) over the changed files using the *project's
own* interpreter — catching syntax errors early without needing a real build
system.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildResult:
    success: bool
    output: str


def run_build_verification(python_executable: str, files: list[Path]) -> BuildResult:
    py_files = [f for f in files if f.suffix == ".py" and f.exists()]
    if not py_files:
        return BuildResult(success=True, output="No Python files to compile-check.")
    try:
        proc = subprocess.run(
            [python_executable, "-m", "compileall", "-q", *[str(f) for f in py_files]],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return BuildResult(success=False, output=f"Could not run compileall: {exc}")
    output = (proc.stdout + proc.stderr).strip()
    return BuildResult(success=proc.returncode == 0, output=output or "Compiled successfully.")
