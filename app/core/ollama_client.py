"""Thin HTTP client for a locally running Ollama server (no cloud API involved)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import requests

from app.config.constants import OLLAMA_HEALTHCHECK_TIMEOUT, OLLAMA_REQUEST_TIMEOUT
from app.core.llm.base import response_error_detail
from app.core.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class OllamaModel:
    name: str
    size_bytes: int = 0
    parameter_size: str = ""
    family: str = ""


class OllamaError(RuntimeError):
    """Raised when a call to the local Ollama server fails or is misconfigured."""


def _chat_error_hint(model: str, exc: requests.RequestException) -> str:
    """The two most common causes of a broken local-Ollama chat call are
    invisible from requests' own error text — add a concrete, actionable
    hint rather than leaving the user to guess at a bare "400"/"401"."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 401 and model.endswith(":cloud"):
        return (
            f" — {model!r} is an Ollama cloud-proxy model; it needs the local Ollama "
            "app itself to be signed in (run `ollama signin` in a terminal), separately "
            "from this app's Settings. Or switch this pipeline to the 'Ollama (Remote / "
            "Cloud API)' provider instead, which uses this app's own API key."
        )
    if status == 400 and "embed" in model.lower():
        return (
            f" — {model!r} looks like an embeddings-only model, not a chat model; it "
            "can't answer prompts. Pick a different model for this pipeline (embedding "
            "models are only valid for the RAG tab's embedding selector)."
        )
    return ""


class OllamaClient:
    def __init__(self, host: str = "http://127.0.0.1:11434", api_key: str = ""):
        self.host = host.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.host}/api/tags", headers=self._headers(), timeout=OLLAMA_HEALTHCHECK_TIMEOUT)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[OllamaModel]:
        try:
            resp = requests.get(f"{self.host}/api/tags", headers=self._headers(), timeout=OLLAMA_REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not list Ollama models: %s", exc)
            return []
        data = resp.json()
        models: list[OllamaModel] = []
        for entry in data.get("models", []):
            details = entry.get("details", {}) or {}
            models.append(
                OllamaModel(
                    name=entry.get("name", ""),
                    size_bytes=entry.get("size", 0),
                    parameter_size=details.get("parameter_size", ""),
                    family=details.get("family", ""),
                )
            )
        return models

    def chat(
        self,
        model: str,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        num_ctx: int = 4096,
        timeout: int = 300,
    ) -> str:
        if not model:
            raise OllamaError("No Ollama model selected for this pipeline.")
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        try:
            resp = requests.post(f"{self.host}/api/chat", headers=self._headers(), json=payload, timeout=timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Ollama chat call failed: {exc}{_chat_error_hint(model, exc)}{response_error_detail(exc)}"
            ) from exc
        data = resp.json()
        return data.get("message", {}).get("content", "")

    def chat_stream(
        self,
        model: str,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        num_ctx: int = 4096,
        timeout: int = 300,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Like chat(), but streams: Ollama sends one JSON object per line as
        tokens are generated. `on_token` is called with each incremental
        chunk of text as it arrives; the full accumulated text is returned
        at the end either way."""
        if not model:
            raise OllamaError("No Ollama model selected for this pipeline.")
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        full_text_parts: list[str] = []
        try:
            with requests.post(
                f"{self.host}/api/chat", headers=self._headers(), json=payload, timeout=timeout, stream=True,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        full_text_parts.append(piece)
                        if on_token:
                            on_token(piece)
                    if chunk.get("done"):
                        break
        except requests.RequestException as exc:
            raise OllamaError(
                f"Ollama chat call failed: {exc}{_chat_error_hint(model, exc)}{response_error_detail(exc)}"
            ) from exc
        return "".join(full_text_parts)

    def embed(self, model: str, text: str) -> list[float]:
        if not model:
            raise OllamaError("No Ollama embedding model selected.")
        payload = {"model": model, "prompt": text}
        try:
            resp = requests.post(f"{self.host}/api/embeddings", headers=self._headers(), json=payload, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama embeddings call failed: {exc}{response_error_detail(exc)}") from exc
        data = resp.json()
        embedding = data.get("embedding")
        if not embedding:
            raise OllamaError("Ollama returned an empty embedding — is this an embedding-capable model?")
        return embedding
