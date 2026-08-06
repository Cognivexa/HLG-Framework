"""Ollama Local provider: talks to a local Ollama server (default
http://127.0.0.1:11434), no API key required. Wraps the existing, already
tested OllamaClient rather than re-implementing the HTTP calls."""
from __future__ import annotations

from typing import Callable

from app.config.constants import OLLAMA_DEFAULT_HOST
from app.core.llm.base import LLMProvider, ProviderError, ProviderModel
from app.core.ollama_client import OllamaClient, OllamaError


class OllamaLocalProvider(LLMProvider):
    id = "ollama_local"
    display_name = "Ollama (Local)"
    requires_api_key = False
    supports_embeddings = True

    def _client(self, extra: dict) -> OllamaClient:
        host = (extra or {}).get("ollama_host") or OLLAMA_DEFAULT_HOST
        return OllamaClient(host=host)

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        client = self._client(extra)
        return [ProviderModel(id=m.name) for m in client.list_models()]

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        client = self._client(extra)
        num_ctx = (extra or {}).get("num_ctx", 4096)
        try:
            if on_token is not None:
                return client.chat_stream(
                    model=model, prompt=prompt, system=system, temperature=temperature,
                    num_ctx=num_ctx, on_token=on_token,
                )
            return client.chat(model=model, prompt=prompt, system=system, temperature=temperature, num_ctx=num_ctx)
        except OllamaError as exc:
            raise ProviderError(str(exc)) from exc

    def embed(self, model: str, text: str, api_key: str, extra: dict) -> list[float]:
        client = self._client(extra)
        try:
            return client.embed(model=model, text=text)
        except OllamaError as exc:
            raise ProviderError(str(exc)) from exc
