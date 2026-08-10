"""Shared constants: supported extensions, ignore lists, defaults."""

SUPPORTED_EXTENSIONS = {
    ".py", ".pyi", ".txt", ".toml", ".cfg", ".ini", ".md", ".json", ".yaml", ".yml",
}

IGNORED_DIR_NAMES = {
    ".git", ".hg", ".svn", "__pycache__", ".venv", "venv", "env", "node_modules",
    ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".harness_backup", "site-packages", ".tox", ".chroma",
}

PYTHON_BUILD_FILES = {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"}

DEFAULT_RETRY_LIMIT = 3
# How many full Harness -> Loop rounds Auto Run will attempt for one
# triggered change before giving up and leaving Graph/the final status
# blocked. Distinct from DEFAULT_RETRY_LIMIT, which bounds Loop's own
# fix-iteration count *within* a single one of these rounds.
DEFAULT_HARNESS_AUTO_RETRY_LIMIT = 3
DEFAULT_DEBOUNCE_SECONDS = 0.8
DEFAULT_BATCH_WINDOW_MS = 800
# 127.0.0.1, not "localhost": on this kind of Windows setup, resolving
# "localhost" can add a consistent ~2s stall (IPv6 ::1 attempted before
# falling back to IPv4) on every single Ollama call — 127.0.0.1 skips that
# entirely and responds instantly.
OLLAMA_DEFAULT_HOST = "http://127.0.0.1:11434"
# Default target for the "Ollama (Remote / Cloud API)" provider when the user
# hasn't typed a custom host — this covers the common case (Ollama's own
# hosted cloud models at a fixed, well-known URL) without making every user
# type it in by hand; a self-hosted remote server still overrides it.
OLLAMA_CLOUD_HOST = "https://ollama.com"
OLLAMA_REQUEST_TIMEOUT = 15
OLLAMA_HEALTHCHECK_TIMEOUT = 2

# APP_NAME is the filesystem-safe identifier (settings folder, Windows
# autostart registry key, User-Agent) — no spaces. APP_DISPLAY_NAME is what
# shows up in window titles, the README, and everywhere else a human reads
# it. Kept distinct on purpose: renaming the display name should never mean
# silently relocating (and orphaning) a user's existing settings folder —
# see app.config.settings for the one-time migration this enables.
APP_NAME = "HLGFramework"
APP_DISPLAY_NAME = "HLG Framework"
_LEGACY_APP_NAMES = ("HarnessEngineering",)
