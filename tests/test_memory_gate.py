"""Tests for the memory gate (app.pipelines.loop.memory_gate): the decision
of whether a Loop Engineering fix is generalizable enough to remember, made
by the configured model and never allowed to crash the (already-successful)
Loop run it runs after."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from app.core import memory_log
from app.core.events import bus
from app.core.llm.base import ProviderError
from app.pipelines.loop import memory_gate


@dataclass
class _FakeLLMClient:
    chat_response: str = ""
    chat_error: Exception | None = None
    embed_calls: list = field(default_factory=list)
    embed_error: Exception | None = None

    def chat(self, provider_id, model, prompt, system="", temperature=0.2, on_token=None, **extra):
        if self.chat_error:
            raise self.chat_error
        return self.chat_response

    def embed(self, provider_id, model, text, **extra):
        if self.embed_error:
            raise self.embed_error
        self.embed_calls.append((provider_id, model, text))
        return [0.1, 0.2, 0.3]


class _FakeRagStore:
    instances: list = []

    def __init__(self):
        self.added = []
        _FakeRagStore.instances.append(self)

    def add_chunks(self, source, chunks, embeddings):
        self.added.append((source, chunks, embeddings))


def _settings(embedding_model="nomic-embed-text"):
    return SimpleNamespace(
        models=SimpleNamespace(
            loop_fix_provider="ollama_local", loop_fix_model="llama3.1",
            rag_embedding_provider="ollama_local", rag_embedding_model=embedding_model,
        )
    )


@pytest.fixture(autouse=True)
def _isolate_memory_log(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_log, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_log, "_LOG_FILE", tmp_path / "gate_decisions.json")
    _FakeRagStore.instances.clear()
    yield


@pytest.fixture(autouse=True)
def _patch_rag_store(monkeypatch):
    monkeypatch.setattr(memory_gate, "RagStore", _FakeRagStore)


def test_parse_decision_remember_yes():
    decision = memory_gate._parse_decision("REMEMBER: yes\nLESSON: Never hardcode secrets.")
    assert decision.remember is True
    assert decision.lesson == "Never hardcode secrets."


def test_parse_decision_remember_no_ignores_lesson():
    decision = memory_gate._parse_decision("REMEMBER: no\nLESSON: n/a")
    assert decision.remember is False
    assert decision.lesson == ""


def test_parse_decision_yes_without_usable_lesson_is_not_remembered():
    decision = memory_gate._parse_decision("REMEMBER: yes\nLESSON: n/a")
    assert decision.remember is False


def test_run_memory_gate_remembers_and_embeds_when_worth_it():
    llm_client = _FakeLLMClient(chat_response="REMEMBER: yes\nLESSON: Never hardcode secrets — use env vars.")
    captured = []
    on_decided = lambda *args: captured.append(args)  # noqa: E731
    bus.memory_gate_decided.connect(on_decided)
    try:
        decision = memory_gate.run_memory_gate(
            "run-1", "/proj", "unit_tests: failed", ["calc.py"], _settings(), llm_client,
        )
    finally:
        bus.memory_gate_decided.disconnect(on_decided)

    assert decision.remember is True
    assert decision.lesson == "Never hardcode secrets — use env vars."
    assert len(_FakeRagStore.instances) == 1
    stored = _FakeRagStore.instances[0].added
    assert stored == [("learned-fix::run-1", [decision.lesson], [[0.1, 0.2, 0.3]])]
    assert captured and captured[0] == ("run-1", True, decision.lesson)

    logged = memory_log.list_decisions()
    assert len(logged) == 1
    assert logged[0]["remember"] is True
    assert logged[0]["run_id"] == "run-1"


def test_run_memory_gate_skips_storage_when_not_worth_remembering():
    llm_client = _FakeLLMClient(chat_response="REMEMBER: no\nLESSON: n/a")
    decision = memory_gate.run_memory_gate("run-2", "/proj", "unit_tests: failed", ["calc.py"], _settings(), llm_client)

    assert decision.remember is False
    assert _FakeRagStore.instances == []
    logged = memory_log.list_decisions()
    assert logged[0]["remember"] is False


def test_run_memory_gate_skips_storage_when_no_embedding_model_configured():
    llm_client = _FakeLLMClient(chat_response="REMEMBER: yes\nLESSON: Validate all external input.")
    decision = memory_gate.run_memory_gate(
        "run-3", "/proj", "security_scan: failed", ["app.py"], _settings(embedding_model=""), llm_client,
    )

    assert decision.remember is True
    assert _FakeRagStore.instances == []  # judged worth remembering, but nothing configured to embed it with
    assert "no RAG embedding model" in decision.reason


def test_run_memory_gate_degrades_gracefully_when_chat_fails():
    llm_client = _FakeLLMClient(chat_error=ProviderError("model unreachable"))
    decision = memory_gate.run_memory_gate("run-4", "/proj", "build_verification: failed", ["a.py"], _settings(), llm_client)

    assert decision.remember is False
    assert "model unreachable" in decision.reason
    assert _FakeRagStore.instances == []


def test_run_memory_gate_degrades_gracefully_when_embedding_fails():
    llm_client = _FakeLLMClient(
        chat_response="REMEMBER: yes\nLESSON: Always close file handles.", embed_error=ProviderError("embed down"),
    )
    decision = memory_gate.run_memory_gate("run-5", "/proj", "static_analysis: failed", ["a.py"], _settings(), llm_client)

    assert decision.remember is True
    assert "could not embed" in decision.reason
    assert len(_FakeRagStore.instances) == 1
    assert _FakeRagStore.instances[0].added == []  # constructed, but add_chunks never reached since embed raised first
