"""Registry of the Claude Code-style specialist agents (agents/*.md) and
skills (skills/*/SKILL.md) shipped alongside this project, plus the
rule-based selector that decides which of them are relevant to a given set
of changed files.

This is what lets Harness, Loop, and Graph Engineering auto-route a change
to the right specialist the way a real engineering org auto-assigns a
domain reviewer to a pull request: touch a Dockerfile and the
docker-kubernetes-pro persona gets pulled in; touch an auth-related file and
the security reviewer does. Selection is purely additive and silent when it
finds nothing — a project with no agents/ or skills/ directory (or no
matching specialist) behaves exactly as it did before this existed.

Two folders, one catalog: an agent and a skill sharing the same slug (e.g.
agents/python-pro.md and skills/python-pro/SKILL.md) are merged into a
single entry, since they describe the same specialty from two angles (a
persona vs. a reference).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = _PROJECT_ROOT / "agents"
SKILLS_DIR = _PROJECT_ROOT / "skills"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")

_MAX_EXCERPT_CHARS = 600
_MAX_TOTAL_GUIDANCE_CHARS = 2400
_MAX_SELECTED = 3


@dataclass(frozen=True)
class AgentCatalogEntry:
    slug: str
    name: str
    description: str
    kind: str  # "agent", "skill", or "agent+skill"
    excerpt: str  # short guidance text injected into prompts


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        field_match = _FIELD_RE.match(line)
        if field_match:
            fields[field_match.group(1).lower()] = field_match.group(2).strip().strip("\"'")
    return fields, text[match.end():]


def _humanize(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.replace("_", "-").split("-"))


def _first_paragraph(body: str) -> str:
    for para in body.strip().split("\n\n"):
        cleaned = para.strip().lstrip("#").strip()
        if cleaned:
            return cleaned
    return ""


def _load_one(path: Path, slug: str) -> tuple[str, str, str]:
    """Returns (name, description, excerpt) for one agent .md or SKILL.md file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return _humanize(slug), "", ""
    fields, body = _parse_frontmatter(text)
    name = fields.get("name") or _humanize(slug)
    description = (fields.get("description") or _first_paragraph(body))[:300]
    excerpt = (description + " " + _first_paragraph(body)).strip()[:_MAX_EXCERPT_CHARS]
    return name, description, excerpt


def _discover_catalog() -> dict[str, AgentCatalogEntry]:
    raw: dict[str, dict] = {}

    if AGENTS_DIR.is_dir():
        for path in sorted(AGENTS_DIR.glob("*.md")):
            slug = path.stem
            name, description, excerpt = _load_one(path, slug)
            entry = raw.setdefault(slug, {"name": name, "description": description, "excerpt": excerpt, "kinds": set()})
            entry["kinds"].add("agent")

    if SKILLS_DIR.is_dir():
        for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            slug = path.parent.name
            name, description, excerpt = _load_one(path, slug)
            entry = raw.setdefault(slug, {"name": name, "description": description, "excerpt": excerpt, "kinds": set()})
            entry["kinds"].add("skill")
            if not entry.get("description"):
                entry["description"] = description
                entry["excerpt"] = excerpt

    return {
        slug: AgentCatalogEntry(
            slug=slug,
            name=data["name"],
            description=data["description"],
            kind="+".join(sorted(data["kinds"])),
            excerpt=data["excerpt"],
        )
        for slug, data in raw.items()
    }


_catalog_cache: dict[str, AgentCatalogEntry] | None = None


def get_catalog() -> dict[str, AgentCatalogEntry]:
    """Lazily discovers and caches the agent/skill catalog. Call
    `invalidate_catalog_cache()` if agents/ or skills/ change while running
    (not needed in normal use — these are read once at process start)."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = _discover_catalog()
    return _catalog_cache


def invalidate_catalog_cache() -> None:
    global _catalog_cache
    _catalog_cache = None


# --- Trigger rules --------------------------------------------------------
# Each rule maps one or more catalog slugs to a matcher over a single
# changed file's path. Multiple rules may match the same file; a slug earns
# one point per matching file, and the highest-scoring slugs win (capped at
# _MAX_SELECTED). This is a curated, deliberately conservative table — it
# only routes to specialists that add something the deterministic Harness
# checks (security/static/quality scans) don't already cover.


def _suffix(*suffixes: str) -> Callable[[str], bool]:
    lowered = tuple(s.lower() for s in suffixes)
    return lambda f: f.lower().endswith(lowered)


def _name_is(*names: str) -> Callable[[str], bool]:
    lowered = {n.lower() for n in names}
    return lambda f: Path(f).name.lower() in lowered


def _name_starts(*prefixes: str) -> Callable[[str], bool]:
    lowered = tuple(p.lower() for p in prefixes)
    return lambda f: Path(f).name.lower().startswith(lowered)


def _path_contains(*fragments: str) -> Callable[[str], bool]:
    lowered = tuple(fr.lower() for fr in fragments)
    return lambda f: any(fr in f.lower().replace("\\", "/") for fr in lowered)


def _any(*matchers: Callable[[str], bool]) -> Callable[[str], bool]:
    return lambda f: any(m(f) for m in matchers)


_TRIGGER_RULES: tuple[tuple[tuple[str, ...], Callable[[str], bool]], ...] = (
    (("python-pro",), _suffix(".py")),
    (("django-pro",), _any(_path_contains("/django/", "django"), _name_is("manage.py", "wsgi.py", "asgi.py"), _path_contains("/migrations/"))),
    (("laravel-specialist",), _any(_name_is("artisan"), _path_contains("/app/http/", "/routes/"))),
    (("php-pro",), _suffix(".php")),
    (("typescript-pro",), _suffix(".ts", ".tsx")),
    (("react-best-practices",), _suffix(".tsx", ".jsx")),
    (("docker-kubernetes-pro", "dockerfile-hardening-checker"), _any(_name_starts("dockerfile"), _name_is("docker-compose.yml", "docker-compose.yaml"), _path_contains("/k8s/", "/kubernetes/"))),
    (("wordpress-pro",), _path_contains("wp-content", "wordpress")),
    (("postgres",), _suffix(".sql")),
    (("ci-cd-pipeline-engineer", "ci-pipeline-linter"), _any(_path_contains(".github/workflows"), _name_is("jenkinsfile", ".gitlab-ci.yml"))),
    (("infrastructure-as-code-architect", "infra-drift-detector"), _any(_suffix(".tf", ".tfvars"), _path_contains("/terraform/", "/infra/"))),
    (("dependency-vuln-triage",), _name_is("requirements.txt", "pyproject.toml", "package.json", "package-lock.json", "poetry.lock", "pipfile")),
    (("application-security-reviewer", "security-reviewer"), _path_contains("auth", "login", "security", "crypto", "password", "token", "session", "secret")),
    (("test-driven-development", "flaky-test-hunter"), _any(_name_starts("test_"), _path_contains("/tests/", "/test/"), _suffix("_test.py", ".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx"))),
    (("rest-api-scaffolder", "api-integration-engineer"), _path_contains("/api/")),
    (("rag-pipeline-architect",), _path_contains("/rag/")),
    (("agent-tooling-reliability-engineer",), _path_contains("/pipelines/", "/core/llm")),
    (("design-systems-specialist", "web-perf-budget-keeper"), _suffix(".html", ".css")),
)


def select_for_changed_files(
    changed_files: list[str], *, always: tuple[str, ...] = (), limit: int = _MAX_SELECTED
) -> list[AgentCatalogEntry]:
    """Ranks catalog entries by how many changed files matched their
    trigger rule(s), always includes any slug listed in `always` (e.g. Loop
    Engineering always wants its debugging-methodology skill regardless of
    file type), and returns at most `limit` entries — capped to bound how
    many extra LLM calls one change set can fan out into."""
    catalog = get_catalog()
    if not catalog:
        return []

    scores: dict[str, int] = {}
    for slugs, matcher in _TRIGGER_RULES:
        for f in changed_files:
            if matcher(f):
                for slug in slugs:
                    if slug in catalog:
                        scores[slug] = scores.get(slug, 0) + 1

    ranked = [slug for slug, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]

    ordered: list[str] = [slug for slug in always if slug in catalog]
    for slug in ranked:
        if slug not in ordered:
            ordered.append(slug)

    return [catalog[slug] for slug in ordered[:limit]]


def format_selection_summary(entries: list[AgentCatalogEntry], changed_count: int) -> str:
    if not entries:
        return f"No specialist agents/skills matched {changed_count} changed file(s)."
    names = ", ".join(f"{e.name} ({e.kind})" for e in entries)
    return f"Auto-selected {len(entries)} specialist(s) for {changed_count} changed file(s): {names}."


def with_specialist_guidance(system_prompt: str, entries: list[AgentCatalogEntry]) -> str:
    """Prepends auto-selected specialist guidance to a system prompt,
    bounded the same deliberate way `app.core.skills.with_skills` bounds
    HARNESS.md — a few hundred characters per specialist, not whole files."""
    if not entries:
        return system_prompt
    blocks: list[str] = []
    budget = _MAX_TOTAL_GUIDANCE_CHARS
    for entry in entries:
        if budget <= 0:
            break
        text = f"### {entry.name} ({entry.kind})\n{entry.excerpt}".strip()[:budget]
        if not text:
            continue
        blocks.append(text)
        budget -= len(text)
    if not blocks:
        return system_prompt
    guidance = "\n\n".join(blocks)
    return (
        "Specialist guidance auto-selected for the file(s) in this change (apply where relevant, "
        f"ignore what doesn't apply):\n\n{guidance}\n\n---\n\n{system_prompt}"
    )
