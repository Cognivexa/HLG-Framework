"""Central Qt signal bus used to decouple background workers from the UI.

A single process-wide `bus` instance is imported everywhere. Background threads
(file watcher, pipeline workers) emit signals here; UI widgets connect to them.
Qt marshals cross-thread signal emissions onto the receiving (UI) thread safely.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class StepEvent:
    pipeline: str          # "harness" | "loop" | "graph"
    run_id: str
    step_id: str
    step_name: str
    status: str             # "pending" | "running" | "success" | "failed" | "skipped"
    detail: str = ""
    data: dict = field(default_factory=dict)  # mirrors StepResult.data — e.g. {"locations": [...]}
    timestamp: str = field(default_factory=_now)


@dataclass
class PipelineEvent:
    pipeline: str
    run_id: str
    project_path: str
    status: str              # "started" | "completed" | "failed" | "blocked"
    summary: str = ""
    timestamp: str = field(default_factory=_now)


@dataclass
class LogEvent:
    level: str
    message: str
    timestamp: str = field(default_factory=_now)


@dataclass
class FileChangeEvent:
    project_path: str
    file_path: str
    change_type: str          # "created" | "modified"


@dataclass
class GraphNodeEvent:
    run_id: str
    node_id: str
    node_label: str
    status: str                # "pending" | "running" | "success" | "failed" | "skipped"
    depends_on: tuple[str, ...] = ()


@dataclass
class PromptEvent:
    """One model call, start to finish — the AI Prompt Timeline's raw feed.
    `prompt_id` correlates a call's "running" event with its later
    "success"/"failed" event (same id, emitted twice)."""
    prompt_id: str
    agent: str              # human label, e.g. "Loop Fix Generation (iteration 2)"
    provider_id: str
    model: str
    status: str              # "running" | "success" | "failed"
    prompt_preview: str = ""
    result_preview: str = ""
    elapsed_seconds: float | None = None
    run_id: str = ""
    timestamp: str = field(default_factory=_now)


class EventBus(QObject):
    step_updated = Signal(object)          # StepEvent
    pipeline_updated = Signal(object)      # PipelineEvent
    log_emitted = Signal(object)           # LogEvent
    file_changed = Signal(object)          # FileChangeEvent
    ollama_status_changed = Signal(bool, list)   # connected, model names
    graph_node_updated = Signal(object)    # GraphNodeEvent
    report_ready = Signal(str, str)        # run_id, report_dir
    clean_copy_ready = Signal(str, str, int)  # source_path, destination_path, file_count
    api_keys_changed = Signal()            # fired whenever Settings saves an API key, anywhere
    auto_run_changed = Signal(bool)        # fired whenever the "Auto Run" toggle changes, from any widget
    fix_proposed = Signal(object)          # FixProposal — Loop wants approval before writing a fix
    memory_gate_decided = Signal(str, bool, str)  # run_id, remembered, lesson
    prompt_activity = Signal(object)       # PromptEvent — every model call, for the AI Prompt Timeline


bus = EventBus()
