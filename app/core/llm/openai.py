"""OpenAI provider (Chat Completions API)."""
from __future__ import annotations

from typing import Callable

import requests

from app.core.llm.base import LLMProvider, ProviderError, ProviderModel

_BASE = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
    id = "openai"
    display_name = "OpenAI"
    requires_api_key = True
    supports_embeddings = True

    def _headers(self, api_key: str) -> dict:
        return {"Authorization": f"Bearer {api_key}"}

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        if not api_key:
            raise ProviderError("OpenAI API key is required.")
        try:
            resp = requests.get(f"{_BASE}/models", headers=self._headers(api_key), timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"OpenAI list_models failed: {exc}") from exc
        data = resp.json()
        return [ProviderModel(id=m["id"]) for m in data.get("data", [])]

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        if not api_key:
            raise ProviderError("OpenAI API key is required.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "temperature": temperature}
        try:
            resp = requests.post(f"{_BASE}/chat/completions", headers=self._headers(api_key), json=payload, timeout=120)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"OpenAI chat call failed: {exc}") from exc
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI response shape: {data}") from exc
        if on_token:
            on_token(text)  # no streaming here (yet) — deliver the whole response at once
        return text

    def embed(self, model: str, text: str, api_key: str, extra: dict) -> list[float]:
        if not api_key:
            raise ProviderError("OpenAI API key is required.")
        try:
            resp = requests.post(
                f"{_BASE}/embeddings", headers=self._headers(api_key), json={"model": model, "input": text}, timeout=60
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"OpenAI embed call failed: {exc}") from exc
        data = resp.json()
        try:
            return data["data"][0]["embedding"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI embedding response: {data}") from exc
