"""Central registry of all LLM providers, keyed by provider id."""
from __future__ import annotations

from app.core.llm.anthropic import AnthropicProvider
from app.core.llm.base import LLMProvider
from app.core.llm.gemini import GeminiProvider
from app.core.llm.huggingface import HuggingFaceProvider
from app.core.llm.ollama_local import OllamaLocalProvider
from app.core.llm.ollama_remote import OllamaRemoteProvider
from app.core.llm.openai import OpenAIProvider

PROVIDERS: dict[str, LLMProvider] = {
    p.id: p
    for p in (
        OllamaLocalProvider(),
        OllamaRemoteProvider(),
        GeminiProvider(),
        OpenAIProvider(),
        AnthropicProvider(),
        HuggingFaceProvider(),
    )
}

EMBEDDING_CAPABLE_PROVIDER_IDS: tuple[str, ...] = tuple(pid for pid, p in PROVIDERS.items() if p.supports_embeddings)


def get_provider(provider_id: str) -> LLMProvider:
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise KeyError(f"Unknown provider id: {provider_id!r}")
    return provider
