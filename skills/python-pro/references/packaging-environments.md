# Packaging & Environments

## pyproject.toml

Use `pyproject.toml` as the single source of project metadata and dependencies (PEP 621), rather than a separate `setup.py`/`setup.cfg`/`requirements.txt` trio that can drift out of sync with each other.

## Virtual Environments

Never install project dependencies into the system Python. Use `venv`, `poetry`, or `uv` to create an isolated environment per project, and commit the lockfile (`poetry.lock`, `uv.lock`) so every machine — including CI — resolves the exact same dependency graph.

## Dependency Pinning

Pin direct dependencies with a compatible-release specifier (`httpx>=0.27,<0.28`) rather than an exact pin for a library, and let the lockfile pin the full transitive graph exactly. Exact-pinning every direct dependency makes routine security patches harder to pull in.

## Entry Points & CLI Tools

Declare console scripts in `pyproject.toml` (`[project.scripts]`) rather than a hand-rolled `if __name__ == "__main__"` wrapper, so the package installs a proper CLI command when installed.

## Auditing

Run `pip-audit` or the equivalent for your package manager against the lockfile on a schedule — a vulnerable transitive dependency is exploitable the same as vulnerable code you wrote yourself.
