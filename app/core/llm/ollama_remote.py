"""Ollama API provider: a remote or self-hosted Ollama server reached by a
user-supplied host URL, with an optional bearer API key — same wire protocol
as Ollama Local, just a different, explicitly configured target.

This also covers Ollama's own hosted cloud models: point the host at
https://ollama.com — its /api/tags (model listing) is public, no key needed
— and put an API key from ollama.com/settings/keys in Settings to actually
chat with a model (https://ollama.com/api/chat returns 401 without one)."""
from __future__ import annotations

from typing import Callable

from app.core.llm.base import LLMProvider, ProviderError, ProviderModel
from app.core.ollama_client import OllamaClient, OllamaError


class OllamaRemoteProvider(LLMProvider):
    id = "ollama_api"
    display_name = "Ollama (Remote / Cloud API)"
    requires_api_key = False  # the host is the real requirement; key is optional for listing, needed to chat on ollama.com
    supports_embeddings = True

    def _client(self, api_key: str, extra: dict) -> OllamaClient:
        host = (extra or {}).get("ollama_remote_host", "")
        if not host:
            raise ProviderError("Set a remote Ollama host URL in Settings first.")
        return OllamaClient(host=host, api_key=api_key)

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        client = self._client(api_key, extra)
        return [ProviderModel(id=m.name) for m in client.list_models()]

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        client = self._client(api_key, extra)
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
        client = self._client(api_key, extra)
        try:
            return client.embed(model=model, text=text)
        except OllamaError as exc:
            raise ProviderError(str(exc)) from exc
