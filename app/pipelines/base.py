"""Core pipeline abstractions shared by Harness, Loop, and Graph engines.

`pipelines/steps/*` holds one real implementation per capability (secret
scan, build, tests, Ollama review, ...). Harness and Graph both wrap the
*same* functions; Harness declares `depends_on` per step and runs
independent ones concurrently (PipelineRunner uses the same DAG-execution
model Graph Engineering does), while Graph organizes them as an explicit
agent DAG. Both read/write the same PipelineContext.
"""
from __future__ import annotations

import concurrent.futures as cf
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from app.core.events import StepEvent, bus

if TYPE_CHECKING:
    from app.config.settings import AppSettings
    from app.core.llm_client import LLMClient
    from app.core.project_context import ProjectContext


@dataclass
class StepResult:
    step_id: str
    step_name: str
    status: str                 # "success" | "failed" | "skipped"
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class PipelineContext:
    run_id: str
    project_path: str
    project: "ProjectContext"
    changed_files: list[str]
    settings: "AppSettings"
    llm_client: "LLMClient"
    results: dict[str, StepResult] = field(default_factory=dict)
    cache: dict = field(default_factory=dict)  # internal memoization, not surfaced as a step

    def get(self, step_id: str) -> StepResult | None:
        return self.results.get(step_id)


@dataclass
class Step:
    id: str
    name: str
    fn: Callable[[PipelineContext], StepResult]
    depends_on: tuple[str, ...] = ()
    skip_if: Callable[[PipelineContext], bool] | None = None


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def emit_step(pipeline: str, run_id: str, result: StepResult) -> None:
    bus.step_updated.emit(
        StepEvent(
            pipeline=pipeline,
            run_id=run_id,
            step_id=result.step_id,
            step_name=result.step_name,
            status=result.status,
            detail=result.detail,
            data=result.data,
        )
    )


def emit_step_running(pipeline: str, run_id: str, step: Step) -> None:
    bus.step_updated.emit(
        StepEvent(pipeline=pipeline, run_id=run_id, step_id=step.id, step_name=step.name, status="running")
    )


def emit_step_pending(pipeline: str, run_id: str, step: Step) -> None:
    bus.step_updated.emit(
        StepEvent(pipeline=pipeline, run_id=run_id, step_id=step.id, step_name=step.name, status="pending")
    )


def _run_step_safe(step: Step, ctx: PipelineContext) -> StepResult:
    try:
        return step.fn(ctx)
    except Exception as exc:  # noqa: BLE001 - a step must never crash the pipeline
        return StepResult(step_id=step.id, step_name=step.name, status="failed", detail=str(exc))


class PipelineRunner:
    """Runs a set of Steps, respecting each Step's `depends_on`, with
    independent steps executing concurrently. The step LIST order is still
    what matters for display: callers should `announce()` all steps up
    front (as "pending") so the UI's row order is locked in immediately,
    regardless of which order they actually finish in.
    """

    def __init__(self, pipeline_name: str, steps: list[Step], max_workers: int = 8):
        self.pipeline_name = pipeline_name
        self.steps = steps
        self.max_workers = max_workers

    def announce(self, run_id: str) -> None:
        for step in self.steps:
            emit_step_pending(self.pipeline_name, run_id, step)

    def run(self, ctx: PipelineContext) -> dict[str, StepResult]:
        completed: set[str] = set()
        in_flight: dict[cf.Future, str] = {}

        with cf.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            def submit_ready() -> None:
                progressed = True
                while progressed:
                    progressed = False
                    for step in self.steps:
                        if step.id in completed or step.id in in_flight.values():
                            continue
                        if not all(dep in completed for dep in step.depends_on):
                            continue
                        if step.skip_if and step.skip_if(ctx):
                            result = StepResult(step_id=step.id, step_name=step.name, status="skipped")
                            ctx.results[step.id] = result
                            completed.add(step.id)
                            emit_step(self.pipeline_name, ctx.run_id, result)
                            progressed = True
                            continue
                        emit_step_running(self.pipeline_name, ctx.run_id, step)
                        future = executor.submit(_run_step_safe, step, ctx)
                        in_flight[future] = step.id
                        progressed = True

            submit_ready()
            while in_flight:
                done, _pending = cf.wait(list(in_flight.keys()), return_when=cf.FIRST_COMPLETED)
                for future in done:
                    step_id = in_flight.pop(future)
                    result = future.result()
                    ctx.results[step_id] = result
                    completed.add(step_id)
                    emit_step(self.pipeline_name, ctx.run_id, result)
                submit_ready()

        return ctx.results
