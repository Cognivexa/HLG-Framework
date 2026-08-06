"""Deterministic remediation for a single detected secret: move its value
into a project-root .env file (creating it if missing) and replace the
in-code literal with an environment-variable lookup.

This is intentionally NOT part of Loop Engineering's automatic LLM fix loop
— it's a narrow, predictable, non-LLM transformation offered from the Issue
Sidebar, applied only when the user explicitly clicks "Move to .env".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.pipelines.base import new_run_id
from app.pipelines.loop.backup import backup_file

_ASSIGNMENT_RE = re.compile(r"^(?P<indent>\s*)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<quote>['\"])(?P<value>.*?)\3\s*(?P<comment>#.*)?$")


@dataclass
class EnvRemediationResult:
    success: bool
    message: str
    env_file: str = ""
    variable_name: str = ""
    backup_path: str = ""


def _find_project_root(file_path: Path) -> Path:
    """Walks upward from the file looking for a recognizable project marker;
    falls back to the file's own directory if none is found."""
    markers = ("requirements.txt", "pyproject.toml", "setup.py", ".git")
    current = file_path.resolve().parent
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return file_path.resolve().parent


def _ensure_os_import(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if any(line.strip() == "import os" for line in lines[:20]):
        return text
    insert_at = 0
    if lines and lines[0].lstrip().startswith(('"""', "'''")):
        quote = lines[0].lstrip()[:3]
        for i in range(1, len(lines)):
            if quote in lines[i]:
                insert_at = i + 1
                break
    lines.insert(insert_at, "import os\n")
    return "".join(lines)


def _ensure_gitignore_has_env(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    try:
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if ".env" not in existing.split():
            with gitignore.open("a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(".env\n")
    except OSError:
        pass  # best-effort; not worth failing the whole remediation over


def move_secret_to_env(file_path: str, line_number: int) -> EnvRemediationResult:
    path = Path(file_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return EnvRemediationResult(success=False, message=f"Could not read {file_path}: {exc}")

    lines = text.splitlines(keepends=True)
    if not (1 <= line_number <= len(lines)):
        return EnvRemediationResult(success=False, message=f"Line {line_number} is out of range for {path.name}.")

    match = _ASSIGNMENT_RE.match(lines[line_number - 1].rstrip("\n"))
    if not match:
        return EnvRemediationResult(
            success=False,
            message=f"Line {line_number} doesn't look like a simple NAME = \"value\" assignment — leaving it as-is.",
        )

    var_name = match.group("name")
    value = match.group("value")
    comment = (match.group("comment") or "").strip()
    indent = match.group("indent")

    project_root = _find_project_root(path)
    run_id = new_run_id()
    backup_path = backup_file(project_root, run_id, path)

    env_path = project_root / ".env"
    env_path.touch(exist_ok=True)
    env_text = env_path.read_text(encoding="utf-8") if env_path.stat().st_size else ""
    if f"{var_name}=" not in env_text.split("\n"):
        with env_path.open("a", encoding="utf-8") as f:
            if env_text and not env_text.endswith("\n"):
                f.write("\n")
            f.write(f"{var_name}={value}\n")

    new_line = f'{indent}{var_name} = os.environ.get("{var_name}", "")'
    if comment:
        new_line += f"  {comment}"
    lines[line_number - 1] = new_line + "\n"

    new_text = _ensure_os_import("".join(lines))
    path.write_text(new_text, encoding="utf-8")

    _ensure_gitignore_has_env(project_root)

    return EnvRemediationResult(
        success=True,
        message=f'Moved {var_name} to {env_path.name} and replaced it with os.environ.get("{var_name}", "") in {path.name}.',
        env_file=str(env_path),
        variable_name=var_name,
        backup_path=str(backup_path) if backup_path else "",
    )
