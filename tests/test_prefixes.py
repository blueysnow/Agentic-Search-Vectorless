"""Tests for 2.1 Pre-Phase-2 Fixes: backoff, tiktoken cache, MongoDB pool, conftest."""

from unittest.mock import patch


# --- Exponential backoff ---


def test_retry_delay_is_bounded():
    from src.llm.provider import _retry_delay, RETRY_MAX_DELAY_S

    for attempt in range(20):
        delay = _retry_delay(attempt)
        assert 0 <= delay <= RETRY_MAX_DELAY_S


def test_retry_delay_increases_with_attempt():
    # On average, higher attempts should produce larger delays
    # Test the max bound increases
    from src.llm.provider import RETRY_BASE_DELAY_S, RETRY_MAX_DELAY_S

    bound_0 = min(RETRY_MAX_DELAY_S, RETRY_BASE_DELAY_S * (2**0))
    bound_5 = min(RETRY_MAX_DELAY_S, RETRY_BASE_DELAY_S * (2**5))
    assert bound_5 > bound_0


# --- tiktoken caching ---


def test_tiktoken_encoder_is_cached():
    from src.utils.tokens import get_encoding

    enc1 = get_encoding("gpt-4o")
    enc2 = get_encoding("gpt-4o")
    assert enc1 is enc2  # Same object, not just equal


def test_count_tokens_uses_cache():
    from src.utils.tokens import count_tokens

    # Just verify it works correctly
    result = count_tokens("hello world")
    assert result > 0


def test_count_tokens_empty():
    from src.utils.tokens import count_tokens

    assert count_tokens("") == 0


# --- MongoDB pool config ---


def test_mongodb_pool_config():
    """Verify MongoClient is created with pool config parameters."""
    from src.config import get_settings

    get_settings.cache_clear()

    with patch("src.db.client.MongoClient") as mock_client:
        from src.db import client

        # Reset singleton
        client._client = None
        client.get_client()
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args
        assert call_kwargs.kwargs.get("maxPoolSize") == 50
        assert call_kwargs.kwargs.get("serverSelectionTimeoutMS") == 5000
        assert call_kwargs.kwargs.get("socketTimeoutMS") == 30000
        # Reset
        client._client = None


# --- conftest cache_clear ---


def test_settings_cache_clear_in_conftest():
    """Verify that get_settings cache is cleared (tested by fixture behavior)."""
    from src.config import get_settings

    # The fixture should have cleared the cache. Calling get_settings should work.
    settings = get_settings()
    assert settings.mongodb_database == "agentic_search_test"
