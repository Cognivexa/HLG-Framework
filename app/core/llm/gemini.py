"""Google Gemini provider (Generative Language API)."""
from __future__ import annotations

from typing import Callable

import requests

from app.core.llm.base import LLMProvider, ProviderError, ProviderModel

_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    id = "gemini"
    display_name = "Google Gemini"
    requires_api_key = True
    supports_embeddings = True

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        if not api_key:
            raise ProviderError("Gemini API key is required.")
        try:
            resp = requests.get(f"{_BASE}/models", params={"key": api_key}, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Gemini list_models failed: {exc}") from exc
        data = resp.json()
        models = []
        for entry in data.get("models", []):
            name = entry.get("name", "")  # "models/gemini-1.5-flash"
            methods = entry.get("supportedGenerationMethods", [])
            if "generateContent" in methods or "embedContent" in methods:
                models.append(ProviderModel(id=name.removeprefix("models/"), display_name=entry.get("displayName", name)))
        return models

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        if not api_key:
            raise ProviderError("Gemini API key is required.")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            resp = requests.post(
                f"{_BASE}/models/{model}:generateContent", params={"key": api_key}, json=payload, timeout=120
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Gemini chat call failed: {exc}") from exc
        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected Gemini response shape: {data}") from exc
        if on_token:
            on_token(text)  # Gemini has no streaming here (yet) — deliver the whole response at once
        return text

    def embed(self, model: str, text: str, api_key: str, extra: dict) -> list[float]:
        if not api_key:
            raise ProviderError("Gemini API key is required.")
        payload = {"content": {"parts": [{"text": text}]}}
        try:
            resp = requests.post(
                f"{_BASE}/models/{model}:embedContent", params={"key": api_key}, json=payload, timeout=60
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"Gemini embed call failed: {exc}") from exc
        data = resp.json()
        try:
            return data["embedding"]["values"]
        except KeyError as exc:
            raise ProviderError(f"Unexpected Gemini embedding response: {data}") from exc
