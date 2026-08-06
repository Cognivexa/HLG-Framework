"""Anthropic provider (Messages API). No embeddings endpoint exists, so
embed() is intentionally not overridden — the base class raises for it, and
this provider is excluded from RAG embedding provider choices in the UI."""
from __future__ import annotations

from typing import Callable

import requests

from app.core.llm.base import LLMProvider, ProviderError, ProviderModel

_BASE = "https://api.anthropic.com/v1"
_API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    id = "anthropic"
    display_name = "Anthropic"
    requires_api_key = True
    supports_embeddings = False

    def _headers(self, api_key: str) -> dict:
        return {"x-api-key": api_key, "anthropic-version": _API_VERSION, "content-type": "application/json"}

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        if not api_key:
            raise ProviderError("Anthropic API key is required.")
        try:
            resp = requests.get(f"{_BASE}/models", headers=self._headers(api_key), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Anthropic list_models failed: {exc}") from exc
        data = resp.json()
        return [ProviderModel(id=m["id"], display_name=m.get("display_name", m["id"])) for m in data.get("data", [])]

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        if not api_key:
            raise ProviderError("Anthropic API key is required.")
        payload = {
            "model": model,
            "max_tokens": (extra or {}).get("max_tokens", 2048),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        try:
            resp = requests.post(f"{_BASE}/messages", headers=self._headers(api_key), json=payload, timeout=120)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Anthropic chat call failed: {exc}") from exc
        data = resp.json()
        try:
            text = "".join(block.get("text", "") for block in data.get("content", []))
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Unexpected Anthropic response shape: {data}") from exc
        if on_token:
            on_token(text)  # no streaming here (yet) — deliver the whole response at once
        return text
