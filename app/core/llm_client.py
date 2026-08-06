"""Facade the rest of the app calls instead of talking to a specific
provider directly. Looks up the configured API key (and, for Ollama
providers, host) from AppSettings and dispatches to the right LLMProvider.

Every chat() call also emits `bus.prompt_activity` (a PromptEvent) — this is
the single point every pipeline's model calls pass through, so it's also the
one place that can observe all of them for the AI Prompt Timeline without
instrumenting each call site's business logic individually.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from app.core.events import PromptEvent, bus
from app.core.llm.base import ProviderModel
from app.core.llm.registry import get_provider

_PROMPT_PREVIEW_CHARS = 500
_RESULT_PREVIEW_CHARS = 300

_prompt_id_lock = threading.Lock()
_next_prompt_id = 0


def _new_prompt_id() -> str:
    global _next_prompt_id
    with _prompt_id_lock:
        _next_prompt_id += 1
        return str(_next_prompt_id)


class LLMClient:
    def __init__(self, settings):
        self.settings = settings

    def _extra(self, **overrides) -> dict:
        extra = {
            "ollama_host": self.settings.ollama_host,
            "ollama_remote_host": self.settings.ollama_remote_host,
            "num_ctx": self.settings.context_size,
        }
        extra.update(overrides)
        return extra

    def _api_key(self, provider_id: str) -> str:
        return self.settings.api_keys.get(provider_id, "")

    def list_models(self, provider_id: str, **extra_overrides) -> list[ProviderModel]:
        provider = get_provider(provider_id)
        return provider.list_models(self._api_key(provider_id), self._extra(**extra_overrides))

    def chat(
        self,
        provider_id: str,
        model: str,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        on_token: Callable[[str], None] | None = None,
        label: str = "",
        run_id: str = "",
        **extra_overrides,
    ) -> str:
        provider = get_provider(provider_id)
        agent = label or "Model call"
        prompt_id = _new_prompt_id()
        started = time.monotonic()

        bus.prompt_activity.emit(
            PromptEvent(
                prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="running",
                prompt_preview=prompt[:_PROMPT_PREVIEW_CHARS], run_id=run_id,
            )
        )
        try:
            result = provider.chat(
                model, prompt, system, temperature, self._api_key(provider_id), self._extra(**extra_overrides),
                on_token=on_token,
            )
        except Exception as exc:
            bus.prompt_activity.emit(
                PromptEvent(
                    prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="failed",
                    result_preview=str(exc)[:_RESULT_PREVIEW_CHARS], elapsed_seconds=time.monotonic() - started,
                    run_id=run_id,
                )
            )
            raise
        bus.prompt_activity.emit(
            PromptEvent(
                prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="success",
                result_preview=result[:_RESULT_PREVIEW_CHARS], elapsed_seconds=time.monotonic() - started,
                run_id=run_id,
            )
        )
        return result

    def embed(self, provider_id: str, model: str, text: str, **extra_overrides) -> list[float]:
        provider = get_provider(provider_id)
        return provider.embed(model, text, self._api_key(provider_id), self._extra(**extra_overrides))
