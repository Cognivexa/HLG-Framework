"""Discovers and loads plugin modules from the plugins directory.

A plugin is any .py file placed under the plugins directory that defines a
module-level `register(registry: PluginRegistry) -> None` function. Built-in
Harness/Graph steps do NOT go through this mechanism (they're wired directly
in pipelines/steps) — this loader is purely the extension seam for future
third-party steps.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app.config.settings import CONFIG_DIR
from app.core.logging_setup import get_logger
from app.plugins.base import PluginStep

logger = get_logger(__name__)

PLUGINS_DIR = CONFIG_DIR / "plugins" / "installed"


class PluginRegistry:
    def __init__(self):
        self.steps: dict[str, PluginStep] = {}

    def register(self, step: PluginStep) -> None:
        self.steps[step.id] = step
        logger.info("Registered plugin step: %s", step.id)


def load_plugins(plugins_dir: Path | None = None) -> PluginRegistry:
    registry = PluginRegistry()
    directory = plugins_dir or PLUGINS_DIR
    if not directory.exists():
        return registry

    for path in sorted(directory.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f"harness_plugin_{path.stem}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                module.register(registry)
            else:
                logger.warning("Plugin %s has no register(registry) function; skipped", path.name)
        except Exception as exc:  # noqa: BLE001 - a broken plugin must not crash the app
            logger.error("Failed to load plugin %s: %s", path.name, exc)

    return registry


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = load_plugins()
    return _registry


def reload_plugins() -> PluginRegistry:
    global _registry
    _registry = load_plugins()
    return _registry
