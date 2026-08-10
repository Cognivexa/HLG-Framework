"""Ollama API provider: Ollama's own hosted cloud models by default, or a
self-hosted remote Ollama server if you point the host at one — same wire
protocol as Ollama Local, just a different, explicitly configured target.

No host configured in Settings means "use Ollama's own cloud API"
(https://ollama.com) — its /api/tags (model listing) is public, no key
needed — put an API key from ollama.com/settings/keys in Settings to
actually chat with a model (https://ollama.com/api/chat returns 401 without
one). Only users pointing at their own self-hosted remote Ollama server need
to type a host at all."""
from __future__ import annotations

from typing import Callable

from app.config.constants import OLLAMA_CLOUD_HOST
from app.core.llm.base import LLMProvider, ProviderError, ProviderModel
from app.core.ollama_client import OllamaClient, OllamaError


class OllamaRemoteProvider(LLMProvider):
    id = "ollama_api"
    display_name = "Ollama (Remote / Cloud API)"
    # Listing is technically public on ollama.com, but chat/embed always need
    # a key there — same "search doesn't need one, everything else does"
    # situation as HuggingFace, so this matches its requires_api_key = True
    # rather than leaving the model picker populated with models that are
    # guaranteed to 403 the moment anything actually tries to call them.
    requires_api_key = True
    supports_embeddings = True

    def _client(self, api_key: str, extra: dict) -> OllamaClient:
        # An unset host defaults to Ollama's own cloud API — the case almost
        # every user of this provider actually wants. A custom value here
        # (a self-hosted remote Ollama server) always overrides the default.
        host = (extra or {}).get("ollama_remote_host") or OLLAMA_CLOUD_HOST
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
