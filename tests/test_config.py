"""Tests for src/config.py."""

from src.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "test_db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    s = Settings()
    assert s.mongodb_database == "test_db"
    assert s.max_pages_per_node == 10
    assert s.max_tokens_per_node == 20000
    assert s.atlas_search_weight == 0.3
    assert s.tree_navigation_weight == 0.7
    assert s.top_n_candidates == 5
    assert s.log_level == "info"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://custom:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "custom_db")
    monkeypatch.setenv("MAX_PAGES_PER_NODE", "20")
    monkeypatch.setenv("ATLAS_SEARCH_WEIGHT", "0.5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("OPENAI_API_KEY", "k")

    s = Settings()
    assert s.mongodb_uri == "mongodb://custom:27017"
    assert s.max_pages_per_node == 20
    assert s.atlas_search_weight == 0.5


def test_get_settings_returns_instance():
    s = get_settings()
    assert isinstance(s, Settings)
