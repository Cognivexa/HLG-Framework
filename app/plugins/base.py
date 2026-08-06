"""Extension point for third-party pipeline steps.

A plugin is a .py file placed in the plugins directory (see loader.py) that
defines a module-level `register(registry)` function, which adds one or more
PluginStep instances to the registry. The Harness pipeline appends any
registered plugin steps to its own step list at run time — this is a real
extension seam, not a placeholder: see examples/plugins/todo_scanner_plugin.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.pipelines.base import PipelineContext, StepResult


class PluginStep(ABC):
    id: str = ""
    name: str = ""

    @abstractmethod
    def run(self, ctx: PipelineContext) -> StepResult:
        ...
