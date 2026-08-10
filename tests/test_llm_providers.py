"""Tests for the multi-provider LLM layer: each cloud provider's HTTP calls
are mocked (following the same pattern as tests/test_ollama_client.py), plus
the registry and the LLMClient facade's dispatch logic."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core.llm.anthropic import AnthropicProvider
from app.core.llm.base import ProviderError
from app.core.llm.gemini import GeminiProvider
from app.core.llm.huggingface import HuggingFaceProvider
from app.core.llm.openai import OpenAIProvider
from app.core.llm.registry import EMBEDDING_CAPABLE_PROVIDER_IDS, PROVIDERS, get_provider
from app.core.llm_client import LLMClient


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code}")
    return resp


class _FakeModels:
    """Stand-in for AppSettings.models: a plain bag of settable attributes."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeSettings:
    def __init__(self, api_keys=None, models=None):
        self.ollama_host = "http://localhost:11434"
        self.ollama_remote_host = "http://remote:11434"
        self.context_size = 4096
        self.api_keys = api_keys or {}
        self.models = models
        self.save_count = 0

    def save(self):
        self.save_count += 1


# --- Registry -----------------------------------------------------------

def test_registry_contains_all_expected_providers():
    expected = {"ollama_local", "ollama_api", "gemini", "openai", "anthropic", "huggingface"}
    assert set(PROVIDERS.keys()) == expected


def test_anthropic_excluded_from_embedding_capable_providers():
    assert "anthropic" not in EMBEDDING_CAPABLE_PROVIDER_IDS
    assert "openai" in EMBEDDING_CAPABLE_PROVIDER_IDS
    assert "ollama_local" in EMBEDDING_CAPABLE_PROVIDER_IDS


def test_get_provider_raises_for_unknown_id():
    with pytest.raises(KeyError):
        get_provider("not_a_real_provider")


# --- Ollama Remote / Cloud API ---------------------------------------------

def test_ollama_remote_defaults_to_cloud_host_when_unset():
    from app.config.constants import OLLAMA_CLOUD_HOST
    from app.core.llm.ollama_remote import OllamaRemoteProvider

    client = OllamaRemoteProvider()._client(api_key="", extra={})
    assert client.host == OLLAMA_CLOUD_HOST


def test_ollama_remote_uses_custom_host_when_set():
    from app.core.llm.ollama_remote import OllamaRemoteProvider

    client = OllamaRemoteProvider()._client(
        api_key="", extra={"ollama_remote_host": "http://my-server:11434"}
    )
    assert client.host == "http://my-server:11434"


def test_ollama_remote_list_models_works_without_a_configured_host():
    from app.config.constants import OLLAMA_CLOUD_HOST
    from app.core.llm.ollama_remote import OllamaRemoteProvider

    payload = {"models": [{"name": "kimi-k2.7-code"}]}
    with patch("app.core.ollama_client.requests.get", return_value=_mock_response(payload)) as mock_get:
        models = OllamaRemoteProvider().list_models("key", {})
    assert [m.id for m in models] == ["kimi-k2.7-code"]
    assert mock_get.call_args[0][0].startswith(OLLAMA_CLOUD_HOST)


# --- Gemini ---------------------------------------------------------------

def test_gemini_list_models_filters_by_supported_methods():
    provider = GeminiProvider()
    payload = {
        "models": [
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 1.5 Flash"},
            {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/unsupported", "supportedGenerationMethods": ["countTokens"]},
        ]
    }
    with patch("app.core.llm.gemini.requests.get", return_value=_mock_response(payload)):
        models = provider.list_models("key", {})
    ids = {m.id for m in models}
    assert ids == {"gemini-1.5-flash", "embedding-001"}


def test_gemini_chat_extracts_text():
    provider = GeminiProvider()
    payload = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}
    with patch("app.core.llm.gemini.requests.post", return_value=_mock_response(payload)):
        result = provider.chat("gemini-1.5-flash", "hi", "", 0.2, "key", {})
    assert result == "hello"


def test_gemini_chat_requires_api_key():
    provider = GeminiProvider()
    with pytest.raises(ProviderError):
        provider.chat("gemini-1.5-flash", "hi", "", 0.2, "", {})


def test_gemini_embed_extracts_values():
    provider = GeminiProvider()
    payload = {"embedding": {"values": [0.1, 0.2]}}
    with patch("app.core.llm.gemini.requests.post", return_value=_mock_response(payload)):
        result = provider.embed("text-embedding-004", "hi", "key", {})
    assert result == [0.1, 0.2]


# --- OpenAI -----------------------------------------------------------------

def test_openai_list_models():
    provider = OpenAIProvider()
    payload = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
    with patch("app.core.llm.openai.requests.get", return_value=_mock_response(payload)):
        models = provider.list_models("key", {})
    assert {m.id for m in models} == {"gpt-4o", "gpt-4o-mini"}


def test_openai_chat_extracts_message_content():
    provider = OpenAIProvider()
    payload = {"choices": [{"message": {"content": "hi there"}}]}
    with patch("app.core.llm.openai.requests.post", return_value=_mock_response(payload)):
        result = provider.chat("gpt-4o", "hi", "system", 0.2, "key", {})
    assert result == "hi there"


def test_openai_embed_extracts_vector():
    provider = OpenAIProvider()
    payload = {"data": [{"embedding": [0.5, 0.6]}]}
    with patch("app.core.llm.openai.requests.post", return_value=_mock_response(payload)):
        result = provider.embed("text-embedding-3-small", "hi", "key", {})
    assert result == [0.5, 0.6]


def test_openai_requires_api_key_for_chat():
    provider = OpenAIProvider()
    with pytest.raises(ProviderError):
        provider.chat("gpt-4o", "hi", "", 0.2, "", {})


# --- Anthropic ---------------------------------------------------------------

def test_anthropic_list_models():
    provider = AnthropicProvider()
    payload = {"data": [{"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"}]}
    with patch("app.core.llm.anthropic.requests.get", return_value=_mock_response(payload)):
        models = provider.list_models("key", {})
    assert models[0].id == "claude-sonnet-4-5"
    assert models[0].display_name == "Claude Sonnet 4.5"


def test_anthropic_chat_concatenates_text_blocks():
    provider = AnthropicProvider()
    payload = {"content": [{"type": "text", "text": "part one "}, {"type": "text", "text": "part two"}]}
    with patch("app.core.llm.anthropic.requests.post", return_value=_mock_response(payload)):
        result = provider.chat("claude-sonnet-4-5", "hi", "system", 0.2, "key", {})
    assert result == "part one part two"


def test_anthropic_does_not_support_embeddings():
    provider = AnthropicProvider()
    assert provider.supports_embeddings is False
    with pytest.raises(ProviderError):
        provider.embed("some-model", "hi", "key", {})


# --- HuggingFace ---------------------------------------------------------------

def test_huggingface_list_models_searches_hub():
    provider = HuggingFaceProvider()
    payload = [{"id": "meta-llama/Llama-3.1-8B-Instruct"}, {"id": "mistralai/Mistral-7B-Instruct-v0.3"}]
    with patch("app.core.llm.huggingface.requests.get", return_value=_mock_response(payload)) as mock_get:
        models = provider.list_models("", {"search": "llama"})
    assert {m.id for m in models} == {"meta-llama/Llama-3.1-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"}
    assert mock_get.call_args.kwargs["params"]["search"] == "llama"


def test_huggingface_chat_requires_api_key():
    provider = HuggingFaceProvider()
    with pytest.raises(ProviderError):
        provider.chat("some-model", "hi", "", 0.2, "", {})


def test_huggingface_chat_extracts_message_content():
    provider = HuggingFaceProvider()
    payload = {"choices": [{"message": {"content": "hf response"}}]}
    with patch("app.core.llm.huggingface.requests.post", return_value=_mock_response(payload)):
        result = provider.chat("some-model", "hi", "", 0.2, "key", {})
    assert result == "hf response"


# --- LLMClient facade ---------------------------------------------------------------

def test_llm_client_dispatches_to_correct_provider_with_stored_key():
    settings = _FakeSettings(api_keys={"openai": "sk-test-key"})
    client = LLMClient(settings)
    payload = {"choices": [{"message": {"content": "dispatched ok"}}]}
    with patch("app.core.llm.openai.requests.post", return_value=_mock_response(payload)) as mock_post:
        result = client.chat("openai", "gpt-4o", "hi")
    assert result == "dispatched ok"
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test-key"


def test_llm_client_uses_empty_key_when_not_configured():
    settings = _FakeSettings(api_keys={})
    client = LLMClient(settings)
    with pytest.raises(ProviderError):
        client.chat("openai", "gpt-4o", "hi")


# --- Runtime chat-failure fallback (opt-in via settings_attrs) --------------

def test_llm_client_falls_back_to_next_configured_provider_on_chat_failure():
    settings = _FakeSettings(
        api_keys={"openai": "sk-broken", "anthropic": "sk-works"},
        models=_FakeModels(loop_fix_provider="openai", loop_fix_model="gpt-4o"),
    )
    client = LLMClient(settings)

    anthropic_models_payload = {"data": [{"id": "claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"}]}
    anthropic_chat_payload = {"content": [{"type": "text", "text": "fallback response"}]}

    with patch("app.core.llm.openai.requests.post", side_effect=requests.HTTPError("400 Client Error")), \
         patch("app.core.llm.anthropic.requests.get", return_value=_mock_response(anthropic_models_payload)), \
         patch("app.core.llm.anthropic.requests.post", return_value=_mock_response(anthropic_chat_payload)):
        result = client.chat(
            "openai", "gpt-4o", "hi",
            settings_attrs=("loop_fix_provider", "loop_fix_model"),
        )

    assert result == "fallback response"
    assert settings.models.loop_fix_provider == "anthropic"
    assert settings.models.loop_fix_model == "claude-sonnet-4-5"
    assert settings.save_count == 1


def test_llm_client_does_not_fall_back_when_settings_attrs_omitted():
    settings = _FakeSettings(api_keys={"openai": "sk-broken", "anthropic": "sk-works"})
    client = LLMClient(settings)

    with patch("app.core.llm.openai.requests.post", side_effect=requests.HTTPError("400 Client Error")):
        with pytest.raises(ProviderError):
            client.chat("openai", "gpt-4o", "hi")
