"""Project "skills": a HARNESS.md file at a monitored project's root,
written once by the user, automatically injected into every AI review/fix
prompt — a durable, always-on complement to RAG's retrieval-based semantic
memory (RAG surfaces relevant chunks per query; this is always included,
in full, regardless of what's being reviewed).

Purely additive: a project with no HARNESS.md behaves exactly as it did
before this existed — with_skills() is a no-op in that case.
"""
from __future__ import annotations

from pathlib import Path

SKILLS_FILENAME = "HARNESS.md"
# Keeps this a deliberate, curated standards doc the user actually wrote and
# maintains, not an invitation to paste in an entire codebase or design doc.
_MAX_SKILLS_CHARS = 4000

_STARTER_TEMPLATE = """# HARNESS.md

Project-specific standards and context, read automatically before every AI
code review, fix, and improvement suggestion Harness/Loop/Graph Engineering
make for this project. Keep this a curated, deliberate standards doc — not
a dump of the whole codebase.

Examples of what belongs here:
- Coding conventions this project follows (naming, error handling, etc.)
- Architectural decisions and why (e.g. "this project uses the repository
  pattern for data access")
- Things that look wrong but are intentional, so the AI doesn't "fix" them
- Domain terms or business rules a reviewer needs to know
"""


def skills_path(project_root: Path) -> Path:
    return project_root / SKILLS_FILENAME


def load_skills(project_root: Path) -> str:
    path = skills_path(project_root)
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""
    return text[:_MAX_SKILLS_CHARS]


def with_skills(system_prompt: str, project_root: Path) -> str:
    """Prepends the project's HARNESS.md content (if any) to a system
    prompt, clearly delimited so the model can tell "standing project
    standards" apart from "this specific step's own instructions"."""
    skills = load_skills(project_root)
    if not skills:
        return system_prompt
    return (
        "Project-specific standards and context (from this project's "
        f"{SKILLS_FILENAME} — always apply these):\n{skills}\n\n---\n\n{system_prompt}"
    )


def ensure_starter_skills_file(project_root: Path) -> Path:
    """Creates a starter HARNESS.md with guidance text if one doesn't
    already exist. Never overwrites an existing file."""
    path = skills_path(project_root)
    if not path.exists():
        path.write_text(_STARTER_TEMPLATE, encoding="utf-8")
    return path
