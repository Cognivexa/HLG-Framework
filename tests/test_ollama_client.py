"""Tests for the local Ollama HTTP client (network calls are mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core.ollama_client import OllamaClient, OllamaError


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code}")
    return resp


def _mock_stream_response(lines, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.iter_lines.return_value = iter(lines)
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_is_available_true():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.get", return_value=_mock_response({}, 200)):
        assert client.is_available() is True


def test_is_available_false_on_connection_error():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.get", side_effect=requests.ConnectionError()):
        assert client.is_available() is False


def test_list_models_parses_details():
    client = OllamaClient()
    payload = {"models": [{"name": "llama3.1", "size": 123, "details": {"parameter_size": "8B", "family": "llama"}}]}
    with patch("app.core.ollama_client.requests.get", return_value=_mock_response(payload)):
        models = client.list_models()
    assert len(models) == 1
    assert models[0].name == "llama3.1"
    assert models[0].parameter_size == "8B"


def test_list_models_returns_empty_on_error():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.get", side_effect=requests.ConnectionError()):
        assert client.list_models() == []


def test_chat_requires_model():
    client = OllamaClient()
    with pytest.raises(OllamaError):
        client.chat(model="", prompt="hi")


def test_chat_returns_message_content():
    client = OllamaClient()
    payload = {"message": {"content": "hello there"}}
    with patch("app.core.ollama_client.requests.post", return_value=_mock_response(payload)):
        result = client.chat(model="llama3.1", prompt="hi")
    assert result == "hello there"


def test_chat_wraps_request_exception():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(OllamaError):
            client.chat(model="llama3.1", prompt="hi")


def test_embed_requires_model():
    client = OllamaClient()
    with pytest.raises(OllamaError):
        client.embed(model="", text="hi")


def test_embed_returns_vector():
    client = OllamaClient()
    payload = {"embedding": [0.1, 0.2, 0.3]}
    with patch("app.core.ollama_client.requests.post", return_value=_mock_response(payload)):
        vector = client.embed(model="nomic-embed-text", text="hi")
    assert vector == [0.1, 0.2, 0.3]


def test_embed_raises_on_empty_embedding():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.post", return_value=_mock_response({"embedding": []})):
        with pytest.raises(OllamaError):
            client.embed(model="nomic-embed-text", text="hi")


def test_chat_stream_accumulates_and_calls_on_token():
    client = OllamaClient()
    lines = [
        json.dumps({"message": {"content": "Hello"}, "done": False}),
        json.dumps({"message": {"content": " world"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]
    resp = _mock_stream_response(lines)
    tokens = []
    with patch("app.core.ollama_client.requests.post", return_value=resp):
        result = client.chat_stream(model="llama3.1", prompt="hi", on_token=tokens.append)
    assert result == "Hello world"
    assert tokens == ["Hello", " world"]


def test_chat_stream_works_without_on_token():
    client = OllamaClient()
    lines = [json.dumps({"message": {"content": "hi there"}, "done": True})]
    resp = _mock_stream_response(lines)
    with patch("app.core.ollama_client.requests.post", return_value=resp):
        result = client.chat_stream(model="llama3.1", prompt="hi")
    assert result == "hi there"


def test_chat_stream_skips_unparseable_lines():
    client = OllamaClient()
    lines = ["not json", json.dumps({"message": {"content": "ok"}, "done": True})]
    resp = _mock_stream_response(lines)
    with patch("app.core.ollama_client.requests.post", return_value=resp):
        result = client.chat_stream(model="llama3.1", prompt="hi")
    assert result == "ok"


def test_chat_stream_requires_model():
    client = OllamaClient()
    with pytest.raises(OllamaError):
        client.chat_stream(model="", prompt="hi")


def test_chat_stream_wraps_request_exception():
    client = OllamaClient()
    with patch("app.core.ollama_client.requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(OllamaError):
            client.chat_stream(model="llama3.1", prompt="hi")
