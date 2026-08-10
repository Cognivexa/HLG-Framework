"""HuggingFace provider: model discovery via the public Hub search API (no
key required for search), chat via HF's OpenAI-compatible router endpoint
(key required for actual inference). No embeddings support here — HF's
embedding models are typically run via feature-extraction pipelines with
model-specific shapes, out of scope for this app."""
from __future__ import annotations

from typing import Callable

import requests

from app.core.llm.base import LLMProvider, ProviderError, ProviderModel, response_error_detail

_HUB_API = "https://huggingface.co/api/models"
_ROUTER_BASE = "https://router.huggingface.co/v1"


class HuggingFaceProvider(LLMProvider):
    id = "huggingface"
    display_name = "HuggingFace"
    requires_api_key = True  # required for chat; search itself doesn't need it
    supports_embeddings = False

    def list_models(self, api_key: str, extra: dict) -> list[ProviderModel]:
        query = (extra or {}).get("search", "").strip()
        # The text-generation filter keeps the default (empty-query) browse
        # list relevant, but it also hides plenty of real chat models tagged
        # differently (conversational, text2text-generation, or untagged) —
        # don't apply it once the user is actively searching for something.
        params = {"limit": 20 if not query else 30, "expand[]": "gated"}
        if query:
            params["search"] = query
        else:
            params["filter"] = "text-generation"
        # Authenticated when a key is configured — the Hub search endpoint
        # doesn't require it, but sending it costs nothing and is a
        # prerequisite for HF ever being able to reflect this specific
        # account's own access grants rather than only the repo's blanket
        # "gated" flag.
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            resp = requests.get(_HUB_API, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"HuggingFace model search failed: {exc}{response_error_detail(exc)}") from exc
        data = resp.json()
        models = [
            ProviderModel(id=entry["id"], gated=bool(entry.get("gated")))
            for entry in data
            if "id" in entry
        ]

        # Fuzzy search can miss an exact repo id the user already knows and
        # typed in full (ranking, tagging, or indexing lag) — if it looks
        # like a real "owner/model" id and isn't already in the results,
        # check for it directly so it's still selectable/usable.
        already_listed = any(m.id.lower() == query.lower() for m in models)
        if query and "/" in query and not already_listed:
            exact = self._lookup_exact_model(query, api_key)
            if exact is not None:
                models.insert(0, exact)

        return models

    @staticmethod
    def _lookup_exact_model(model_id: str, api_key: str = "") -> ProviderModel | None:
        url = f"{_HUB_API}/{model_id}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            resp = requests.get(url, params={"expand[]": "gated"}, headers=headers, timeout=10)
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        data = resp.json()
        found_id = data.get("id") or data.get("modelId")
        if not found_id:
            return None
        return ProviderModel(id=found_id, gated=bool(data.get("gated")))

    def chat(
        self, model: str, prompt: str, system: str, temperature: float, api_key: str, extra: dict,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        if not api_key:
            raise ProviderError("HuggingFace API key is required.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": model, "messages": messages, "temperature": temperature}
        try:
            resp = requests.post(
                f"{_ROUTER_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(f"HuggingFace chat call failed: {exc}{response_error_detail(exc)}") from exc
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected HuggingFace response shape: {data}") from exc
        if on_token:
            on_token(text)  # no streaming here (yet) — deliver the whole response at once
        return text
