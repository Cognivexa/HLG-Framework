"""Central registry of all LLM providers, keyed by provider id, plus the
single shared definition of fallback ordering and default-model-picking
logic — used both by the model-selector UI (an empty/unreachable list falls
back to the next configured provider) and by LLMClient (a runtime chat
failure falls back the same way, see app.core.llm_client)."""
from __future__ import annotations

from app.core.llm.anthropic import AnthropicProvider
from app.core.llm.base import LLMProvider, ProviderModel
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

# Applied automatically once a provider has a usable model list and nothing
# is chosen yet — a solid, verified-working general-purpose default per
# provider. Providers with no entry here fall back to whatever model the
# fetch happened to return first (see pick_chat_model/pick_embedding_model).
DEFAULT_CHAT_MODELS: dict[str, str] = {
    "huggingface": "deepseek-ai/DeepSeek-V4-Flash-0731",
}

# For an embeddings-only selector whose configured provider turns out to be
# unreachable/unconfigured: try these in order — ollama_local first since it
# needs no key or host at all, so it's the only one that can just work with
# zero additional setup.
EMBEDDING_FALLBACK_ORDER: tuple[str, ...] = ("ollama_local", "ollama_api", "openai", "gemini")

# For a chat/review selector: if the currently configured provider has no
# key (or, for LLMClient, fails at actual chat time), automatically try
# whichever provider is actually configured — e.g. entering only a
# HuggingFace key should mean every review/fix model picker lands on
# HuggingFace on its own, not stay stuck on a provider that will 403/401 on
# every call. ollama_local goes LAST, not first: it never needs a key, so it
# would otherwise always win the race even when a user who entered exactly
# one cloud API key clearly wants that provider used, not whatever happens
# to be running locally and unconfigured.
CHAT_FALLBACK_ORDER: tuple[str, ...] = ("openai", "anthropic", "gemini", "huggingface", "ollama_api", "ollama_local")


def looks_embedding_only(model_id: str) -> bool:
    return "embed" in model_id.lower()


def pick_chat_model(provider_id: str, models: list[ProviderModel]) -> str:
    """A provider's model list can mix embedding and chat/completion models
    (e.g. local Ollama with both nomic-embed-text and a cloud chat model
    pulled) — picking blindly risks silently configuring a chat pipeline
    with a model that can never answer a prompt."""
    configured_default = DEFAULT_CHAT_MODELS.get(provider_id)
    if configured_default:
        return configured_default
    chat_like = next((m.id for m in models if not looks_embedding_only(m.id)), None)
    if chat_like:
        return chat_like
    return models[0].id if models else ""


def pick_embedding_model(provider_id: str, models: list[ProviderModel]) -> str:
    embed_like = next((m.id for m in models if looks_embedding_only(m.id)), None)
    if embed_like:
        return embed_like
    return models[0].id if models else ""


def get_provider(provider_id: str) -> LLMProvider:
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise KeyError(f"Unknown provider id: {provider_id!r}")
    return provider
