"""The memory gate: after Loop Engineering successfully fixes every
failure, decide whether the underlying lesson is worth remembering.

This is deliberately not "log everything" — a real decision, made by the
same configured fix model, separates a generalizable lesson ("never
hardcode secrets — read them from the environment") from a one-off detail
("fixed calculator.py's subtract function") that would just be noise in
future retrieval. Accepted lessons are embedded and stored in the RAG
knowledge base (semantic memory) so future Harness/Loop/Graph runs can
retrieve them via the existing `rag_retrieval` step; every decision (kept
or not) is recorded in app/core/memory_log.py (episodic memory of the
gate itself) for the Memory tab to display.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core import memory_log
from app.core.events import bus
from app.core.llm.base import ProviderError
from app.core.llm_client import LLMClient
from app.core.logging_setup import get_logger
from app.rag.vector_store import RagStore

logger = get_logger(__name__)

_GATE_SYSTEM_PROMPT = (
    "You review one autonomous code fix that was just applied and verified to work. Decide whether "
    "the underlying lesson generalizes to other, unrelated code (e.g. 'never hardcode secrets — read "
    "them from environment variables' generalizes; 'fixed calculator.py's subtract function' does "
    "not). Respond with EXACTLY two lines and nothing else:\n"
    "REMEMBER: yes or no\n"
    "LESSON: one generalized sentence a future code reviewer would find useful (write \"n/a\" if REMEMBER is no)"
)


@dataclass
class MemoryGateDecision:
    remember: bool
    lesson: str = ""
    reason: str = ""


def _parse_decision(response: str) -> MemoryGateDecision:
    remember = False
    lesson = ""
    for line in response.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("REMEMBER:"):
            remember = "yes" in stripped.lower()
        elif stripped.upper().startswith("LESSON:"):
            lesson = stripped.split(":", 1)[1].strip()
    if lesson.lower() in ("n/a", "none", ""):
        lesson = ""
    return MemoryGateDecision(remember=remember and bool(lesson), lesson=lesson)


def run_memory_gate(
    run_id: str,
    project_path: str,
    failure_summary: str,
    fixed_files: list[str],
    settings,
    llm_client: LLMClient,
) -> MemoryGateDecision:
    """Best-effort: any failure here (model unreachable, no embedding model
    configured, etc.) degrades to "not remembered", never to a crash — this
    runs after Loop has already succeeded and must not put that at risk."""
    provider_id = settings.models.loop_fix_provider
    model = settings.models.loop_fix_model
    prompt = f"Failures that were fixed:\n{failure_summary}\n\nFiles touched: {', '.join(fixed_files)}"

    try:
        response = llm_client.chat(
            provider_id=provider_id, model=model, prompt=prompt, system=_GATE_SYSTEM_PROMPT, temperature=0.0,
            label="Memory Gate — Remember This Fix?", run_id=run_id,
        )
        decision = _parse_decision(response)
    except ProviderError as exc:
        decision = MemoryGateDecision(remember=False, reason=f"Gate call failed: {exc}")

    if decision.remember:
        embedding_provider = settings.models.rag_embedding_provider
        embedding_model = settings.models.rag_embedding_model
        if not embedding_model:
            decision.reason = "Judged worth remembering, but no RAG embedding model is configured — lesson was not stored."
        else:
            try:
                store = RagStore()
                embedding = llm_client.embed(embedding_provider, embedding_model, decision.lesson)
                store.add_chunks(f"learned-fix::{run_id}", [decision.lesson], [embedding])
            except ProviderError as exc:
                decision.reason = f"Judged worth remembering, but could not embed it: {exc}"

    memory_log.record_decision(
        {
            "run_id": run_id, "project_path": project_path, "remember": decision.remember,
            "lesson": decision.lesson, "reason": decision.reason,
        }
    )
    logger.info("Memory gate for run %s: remember=%s lesson=%r", run_id, decision.remember, decision.lesson)
    bus.memory_gate_decided.emit(run_id, decision.remember, decision.lesson)
    return decision
