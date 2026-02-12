"""Tests for src/llm/provider.py error handling."""

import pytest

from src.llm.provider import (
    LLMAuthError,
    LLMBadRequestError,
    _classify_and_raise,
    _is_retryable,
)


# --- _is_retryable tests ---


def test_retryable_generic_exception():
    assert _is_retryable(Exception("connection reset")) is True


def test_retryable_timeout():
    assert _is_retryable(TimeoutError("timed out")) is True


def test_not_retryable_auth_by_type_name():
    """Simulate an SDK AuthenticationError by name."""

    class AuthenticationError(Exception):
        pass

    assert _is_retryable(AuthenticationError("invalid key")) is False


def test_not_retryable_bad_request_by_type_name():
    class BadRequestError(Exception):
        pass

    assert _is_retryable(BadRequestError("bad model")) is False


def test_not_retryable_permission_by_type_name():
    class PermissionDeniedError(Exception):
        pass

    assert _is_retryable(PermissionDeniedError("denied")) is False


def test_not_retryable_by_status_code():
    exc = Exception("forbidden")
    exc.status_code = 403  # type: ignore[attr-defined]
    assert _is_retryable(exc) is False


def test_not_retryable_by_keyword():
    assert _is_retryable(Exception("invalid api key provided")) is False


def test_retryable_rate_limit_status():
    exc = Exception("rate limit")
    exc.status_code = 429  # type: ignore[attr-defined]
    assert _is_retryable(exc) is True


def test_retryable_server_error_status():
    exc = Exception("internal server error")
    exc.status_code = 500  # type: ignore[attr-defined]
    assert _is_retryable(exc) is True


# --- _classify_and_raise tests ---


def test_classify_auth_error():
    class AuthenticationError(Exception):
        pass

    with pytest.raises(LLMAuthError):
        _classify_and_raise(AuthenticationError("bad key"))


def test_classify_bad_request_error():
    class BadRequestError(Exception):
        pass

    with pytest.raises(LLMBadRequestError):
        _classify_and_raise(BadRequestError("invalid"))


def test_classify_by_status_401():
    exc = Exception("unauthorized")
    exc.status_code = 401  # type: ignore[attr-defined]
    with pytest.raises(LLMAuthError):
        _classify_and_raise(exc)


def test_classify_by_status_400():
    exc = Exception("bad request")
    exc.status_code = 400  # type: ignore[attr-defined]
    with pytest.raises(LLMBadRequestError):
        _classify_and_raise(exc)


# --- Provider init with empty API keys ---


def test_anthropic_provider_rejects_empty_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    # Clear the lru_cache so Settings re-reads env
    from src.config import get_settings

    get_settings.cache_clear()

    from src.llm.provider import AnthropicProvider

    with pytest.raises(LLMAuthError, match="ANTHROPIC_API_KEY is not set"):
        AnthropicProvider()

    # Restore for other tests
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()


def test_openai_provider_rejects_empty_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from src.config import get_settings

    get_settings.cache_clear()

    from src.llm.provider import OpenAIProvider

    with pytest.raises(LLMAuthError, match="OPENAI_API_KEY is not set"):
        OpenAIProvider()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
