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
from app.core.llm.registry import CHAT_FALLBACK_ORDER, PROVIDERS, get_provider, pick_chat_model

_PROMPT_PREVIEW_CHARS = 500
_RESULT_PREVIEW_CHARS = 300
_RETRY_BACKOFF_SECONDS = 1.5

# Substrings of a ProviderError's message that indicate a transient
# network/server hiccup (worth one retry with the same provider/model)
# rather than a real, stable failure (bad key, invalid model, malformed
# request) that retrying would just reproduce identically.
_TRANSIENT_ERROR_HINTS = (
    "timed out", "timeout", "connection", "temporarily unavailable",
    "502", "503", "504", "429",
)


def _looks_transient(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(hint in message for hint in _TRANSIENT_ERROR_HINTS)

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
        settings_attrs: tuple[str, str] | None = None,
        **extra_overrides,
    ) -> str:
        """`settings_attrs`, if given, is the `(provider_attr, model_attr)`
        pair on `settings.models` that controls this call site's choice
        (e.g. `("loop_fix_provider", "loop_fix_model")`). Opting in enables
        automatic fallback to a different configured provider if this exact
        call fails at runtime — see `_chat_with_fallback` below. Omitting it
        (the default) preserves the exact prior behavior: raise on failure,
        no fallback, nothing persisted."""
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

        # One retry, same provider/model, only for errors that look like a
        # transient network/server hiccup rather than a stable failure
        # (bad key, invalid model, malformed request) — retrying those
        # would just reproduce the identical error and waste a round-trip.
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                result = provider.chat(
                    model, prompt, system, temperature, self._api_key(provider_id), self._extra(**extra_overrides),
                    on_token=on_token,
                )
            except Exception as exc:
                if attempt < max_attempts and _looks_transient(exc):
                    bus.prompt_activity.emit(
                        PromptEvent(
                            prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="running",
                            result_preview=f"Attempt {attempt} hit a transient error, retrying: {exc}"[:_RESULT_PREVIEW_CHARS],
                            run_id=run_id,
                        )
                    )
                    time.sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                if settings_attrs is not None:
                    fallback = self._chat_with_fallback(
                        provider_id, prompt, system, temperature, on_token, agent, run_id, settings_attrs,
                        extra_overrides, exc,
                    )
                    if fallback is not None:
                        return fallback
                bus.prompt_activity.emit(
                    PromptEvent(
                        prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="failed",
                        result_preview=str(exc)[:_RESULT_PREVIEW_CHARS], elapsed_seconds=time.monotonic() - started,
                        run_id=run_id,
                    )
                )
                raise
            else:
                bus.prompt_activity.emit(
                    PromptEvent(
                        prompt_id=prompt_id, agent=agent, provider_id=provider_id, model=model, status="success",
                        result_preview=result[:_RESULT_PREVIEW_CHARS], elapsed_seconds=time.monotonic() - started,
                        run_id=run_id,
                    )
                )
                return result

    def _chat_with_fallback(
        self,
        failed_provider_id: str,
        prompt: str,
        system: str,
        temperature: float,
        on_token: Callable[[str], None] | None,
        agent: str,
        run_id: str,
        settings_attrs: tuple[str, str],
        extra_overrides: dict,
        original_exc: Exception,
    ) -> str | None:
        """Tries each provider in CHAT_FALLBACK_ORDER (skipping the one that
        just failed) until one successfully answers this exact prompt.
        Returns the response text and persists the switch into
        `settings.models` on success, or None if every candidate failed too
        (the caller then raises the original exception, unchanged)."""
        for candidate_id in CHAT_FALLBACK_ORDER:
            if candidate_id == failed_provider_id:
                continue
            candidate = PROVIDERS.get(candidate_id)
            if candidate is None:
                continue
            api_key = self._api_key(candidate_id)
            if candidate.requires_api_key and not api_key:
                continue
            extra = self._extra(**extra_overrides)
            try:
                models = candidate.list_models(api_key, extra)
            except Exception:
                continue
            candidate_model = pick_chat_model(candidate_id, models)
            if not candidate_model:
                continue
            try:
                result = candidate.chat(candidate_model, prompt, system, temperature, api_key, extra, on_token=on_token)
            except Exception:
                continue

            provider_attr, model_attr = settings_attrs
            setattr(self.settings.models, provider_attr, candidate_id)
            setattr(self.settings.models, model_attr, candidate_model)
            self.settings.save()
            bus.model_fallback_applied.emit(provider_attr, model_attr, candidate_id, candidate_model, str(original_exc))
            bus.prompt_activity.emit(
                PromptEvent(
                    prompt_id=_new_prompt_id(), agent=f"{agent} (auto-fallback)", provider_id=candidate_id,
                    model=candidate_model, status="success", result_preview=result[:_RESULT_PREVIEW_CHARS],
                    prompt_preview=f"Fell back from {failed_provider_id} after: {original_exc}"[:_PROMPT_PREVIEW_CHARS],
                    run_id=run_id,
                )
            )
            return result
        return None

    def embed(self, provider_id: str, model: str, text: str, **extra_overrides) -> list[float]:
        provider = get_provider(provider_id)
        return provider.embed(model, text, self._api_key(provider_id), self._extra(**extra_overrides))
