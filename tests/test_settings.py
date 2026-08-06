"""Tests for AppSettings JSON persistence."""
from __future__ import annotations

import app.config.settings as settings_module
from app.config.settings import AppSettings


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(settings_module, "CONFIG_DIR", tmp_path)

    settings = AppSettings()
    settings.projects = ["C:\\some\\project"]
    settings.models.harness_review_model = "llama3.1"
    settings.retry_limit = 5
    settings.save()

    loaded = AppSettings.load()
    assert loaded.projects == ["C:\\some\\project"]
    assert loaded.models.harness_review_model == "llama3.1"
    assert loaded.retry_limit == 5


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "CONFIG_FILE", tmp_path / "missing.json")
    loaded = AppSettings.load()
    assert loaded.projects == []
    assert loaded.retry_limit == 3


def test_load_tolerates_corrupt_json(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", config_file)
    loaded = AppSettings.load()
    assert loaded.projects == []


def test_load_migrates_old_localhost_default_to_127_0_0_1(tmp_path, monkeypatch):
    # "localhost" resolves ~2s slower than 127.0.0.1 on some Windows setups;
    # anyone with an older config.json should be transparently upgraded.
    config_file = tmp_path / "config.json"
    config_file.write_text('{"ollama_host": "http://localhost:11434"}', encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", config_file)
    monkeypatch.setattr(settings_module, "CONFIG_DIR", tmp_path)

    loaded = AppSettings.load()
    assert loaded.ollama_host == "http://127.0.0.1:11434"

    reloaded = AppSettings.load()
    assert reloaded.ollama_host == "http://127.0.0.1:11434"


def test_load_leaves_custom_ollama_host_untouched(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"ollama_host": "http://192.168.1.50:11434"}', encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", config_file)
    monkeypatch.setattr(settings_module, "CONFIG_DIR", tmp_path)

    loaded = AppSettings.load()
    assert loaded.ollama_host == "http://192.168.1.50:11434"


def test_add_and_remove_project(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(settings_module, "CONFIG_DIR", tmp_path)

    settings = AppSettings()
    settings.add_project(str(tmp_path))
    assert str(tmp_path) in settings.projects

    settings.remove_project(str(tmp_path))
    assert str(tmp_path) not in settings.projects
