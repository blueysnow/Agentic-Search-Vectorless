"""Abstract LLM provider interface and factory (adapted from reference ChatGPT_API)."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 10
RETRY_BASE_DELAY_S = 1.0
RETRY_MAX_DELAY_S = 60.0


def _retry_delay(attempt: int) -> float:
    """Exponential backoff with full jitter: uniform(0, min(cap, base * 2^attempt))."""
    exp = min(RETRY_MAX_DELAY_S, RETRY_BASE_DELAY_S * (2**attempt))
    return random.uniform(0, exp)


class LLMError(Exception):
    """Base error for LLM provider failures."""


class LLMAuthError(LLMError):
    """Non-retryable: authentication or permission failure."""


class LLMBadRequestError(LLMError):
    """Non-retryable: invalid request (bad model, malformed input)."""


class LLMRetryExhaustedError(LLMError):
    """All retry attempts exhausted for a retryable error."""


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    finish_reason: str  # finished | max_output_reached


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is retryable (rate limit, timeout, network).

    Non-retryable: auth errors, bad request, permission denied.
    """
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()

    # Non-retryable patterns (raise immediately)
    non_retryable_types = (
        "AuthenticationError",
        "PermissionDeniedError",
        "BadRequestError",
        "NotFoundError",
        "UnprocessableEntityError",
    )
    if exc_type in non_retryable_types:
        return False

    non_retryable_keywords = (
        "authentication",
        "permission denied",
        "invalid api key",
        "unauthorized",
        "invalid_api_key",
    )
    if any(kw in exc_str for kw in non_retryable_keywords):
        return False

    # HTTP status code checks (if available)
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status is not None:
        if status in (401, 403, 400, 404, 422):
            return False

    # Everything else is retryable (rate limit, timeout, connection, 500, 503)
    return True


def _classify_and_raise(exc: Exception) -> None:
    """Raise the appropriate LLMError subclass for non-retryable errors."""
    exc_type = type(exc).__name__
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)

    if exc_type in ("AuthenticationError", "PermissionDeniedError") or status in (
        401,
        403,
    ):
        raise LLMAuthError(str(exc)) from exc
    if exc_type in (
        "BadRequestError",
        "NotFoundError",
        "UnprocessableEntityError",
    ) or status in (400, 404, 422):
        raise LLMBadRequestError(str(exc)) from exc
    # Shouldn't reach here if _is_retryable returned False, but just in case
    raise LLMError(str(exc)) from exc


class LLMProvider(ABC):
    """Provider-agnostic interface -- mirrors plan section 8.3."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",  # text | json
    ) -> LLMResponse: ...

    @abstractmethod
    async def chat_async(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> LLMResponse: ...


class AnthropicProvider(LLMProvider):
    """Claude integration via the Anthropic SDK."""

    def __init__(self, model: str | None = None) -> None:
        import anthropic

        settings = get_settings()
        api_key = settings.anthropic_api_key
        if not api_key:
            raise LLMAuthError("ANTHROPIC_API_KEY is not set")
        self._model = model or settings.llm_retrieval_model
        self._client = anthropic.Anthropic(api_key=api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=api_key)

    def _to_anthropic_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict]]:
        system_prompt: str | None = None
        api_msgs: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                api_msgs.append({"role": m.role, "content": m.content})
        return system_prompt, api_msgs

    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> LLMResponse:
        system_prompt, api_msgs = self._to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._client.messages.create(**kwargs)
                content = resp.content[0].text if resp.content else ""
                reason = (
                    "max_output_reached"
                    if resp.stop_reason == "max_tokens"
                    else "finished"
                )
                return LLMResponse(content=content, finish_reason=reason)
            except Exception as exc:
                if not _is_retryable(exc):
                    _classify_and_raise(exc)
                last_exc = exc
                logger.warning(
                    "Anthropic retry %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(_retry_delay(attempt))
        raise LLMRetryExhaustedError(
            f"Anthropic: {MAX_RETRIES} retries exhausted"
        ) from last_exc

    async def chat_async(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> LLMResponse:
        system_prompt, api_msgs = self._to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._async_client.messages.create(**kwargs)
                content = resp.content[0].text if resp.content else ""
                reason = (
                    "max_output_reached"
                    if resp.stop_reason == "max_tokens"
                    else "finished"
                )
                return LLMResponse(content=content, finish_reason=reason)
            except Exception as exc:
                if not _is_retryable(exc):
                    _classify_and_raise(exc)
                last_exc = exc
                logger.warning(
                    "Anthropic async retry %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(_retry_delay(attempt))
        raise LLMRetryExhaustedError(
            f"Anthropic async: {MAX_RETRIES} retries exhausted"
        ) from last_exc


class OpenAIProvider(LLMProvider):
    """GPT integration via the OpenAI SDK (adapted from reference ChatGPT_API)."""

    def __init__(self, model: str | None = None) -> None:
        import openai

        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise LLMAuthError("OPENAI_API_KEY is not set")
        self._model = model or settings.llm_ingestion_model
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self._client = openai.OpenAI(**client_kwargs)
        self._async_client = openai.AsyncOpenAI(**client_kwargs)

    def _to_openai_messages(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> LLMResponse:
        api_msgs = self._to_openai_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_msgs,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                reason = (
                    "max_output_reached"
                    if resp.choices[0].finish_reason == "length"
                    else "finished"
                )
                return LLMResponse(content=content, finish_reason=reason)
            except Exception as exc:
                if not _is_retryable(exc):
                    _classify_and_raise(exc)
                last_exc = exc
                logger.warning("OpenAI retry %d/%d: %s", attempt + 1, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(_retry_delay(attempt))
        raise LLMRetryExhaustedError(
            f"OpenAI: {MAX_RETRIES} retries exhausted"
        ) from last_exc

    async def chat_async(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> LLMResponse:
        api_msgs = self._to_openai_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_msgs,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._async_client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                reason = (
                    "max_output_reached"
                    if resp.choices[0].finish_reason == "length"
                    else "finished"
                )
                return LLMResponse(content=content, finish_reason=reason)
            except Exception as exc:
                if not _is_retryable(exc):
                    _classify_and_raise(exc)
                last_exc = exc
                logger.warning(
                    "OpenAI async retry %d/%d: %s", attempt + 1, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(_retry_delay(attempt))
        raise LLMRetryExhaustedError(
            f"OpenAI async: {MAX_RETRIES} retries exhausted"
        ) from last_exc


def get_provider(
    provider_name: str | None = None, model: str | None = None
) -> LLMProvider:
    """Factory: return the correct provider based on config or explicit name."""
    name = (provider_name or get_settings().llm_provider).lower()
    if name == "anthropic":
        return AnthropicProvider(model=model)
    if name == "openai":
        return OpenAIProvider(model=model)
    raise ValueError(f"Unknown LLM provider: {name}")
