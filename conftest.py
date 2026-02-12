"""Root conftest for pytest."""

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Provide safe defaults for every test run so nothing accidentally hits real services."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "agentic_search_test")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_INGESTION_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("LLM_RETRIEVAL_MODEL", "claude-opus-4-6")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
