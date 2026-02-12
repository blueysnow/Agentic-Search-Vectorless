"""Tests for src/ingestion/tree_builder/verifier.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ingestion.tree_builder.verifier import (
    check_title_appearance,
    check_title_appearance_in_start,
    verify_toc,
)
from src.llm.provider import LLMResponse


def _mock_async_provider(responses: list[str]):
    """Create a mock provider with async support."""
    provider = MagicMock()
    call_count = {"i": 0}

    async def async_chat_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason="finished")

    provider.chat_async = AsyncMock(side_effect=async_chat_side_effect)
    return provider


# --- check_title_appearance ---


@pytest.mark.asyncio
async def test_check_title_appearance_yes():
    provider = _mock_async_provider(['{"thinking": "found it", "answer": "yes"}'])
    result = await check_title_appearance(
        "Introduction", "Introduction to the topic...", provider
    )
    assert result == "yes"


@pytest.mark.asyncio
async def test_check_title_appearance_no():
    provider = _mock_async_provider(['{"thinking": "not found", "answer": "no"}'])
    result = await check_title_appearance(
        "Conclusion", "This is about methodology...", provider
    )
    assert result == "no"


@pytest.mark.asyncio
async def test_check_title_appearance_malformed():
    provider = _mock_async_provider(["not json"])
    result = await check_title_appearance("Title", "text", provider)
    assert result == "no"


# --- check_title_appearance_in_start ---


@pytest.mark.asyncio
async def test_check_title_in_start_yes():
    provider = _mock_async_provider(['{"start_begin": "yes"}'])
    result = await check_title_appearance_in_start(
        "Intro", "Intro\nSome text", provider
    )
    assert result == "yes"


@pytest.mark.asyncio
async def test_check_title_in_start_no():
    provider = _mock_async_provider(['{"start_begin": "no"}'])
    result = await check_title_appearance_in_start(
        "Intro", "Previous content\nIntro", provider
    )
    assert result == "no"


# --- verify_toc ---


@pytest.mark.asyncio
async def test_verify_toc_all_correct():
    provider = _mock_async_provider(['{"answer": "yes"}'] * 10)
    structure = [
        {"title": "Intro", "physical_index": 1},
        {"title": "Body", "physical_index": 5},
        {"title": "End", "physical_index": 9},
    ]
    page_list = [("page text",)] * 10
    accuracy, incorrect = await verify_toc(
        structure, page_list, provider, sample_rate=1.0
    )
    assert accuracy == 1.0
    assert incorrect == []


@pytest.mark.asyncio
async def test_verify_toc_some_incorrect():
    # Return "no" for every call -- guarantees all items are incorrect
    provider = _mock_async_provider(
        [
            '{"answer": "no"}',
            '{"answer": "no"}',
            '{"answer": "no"}',
        ]
    )
    structure = [
        {"title": "A", "physical_index": 1},
        {"title": "B", "physical_index": 5},
        {"title": "C", "physical_index": 9},
    ]
    page_list = [("text",)] * 10
    accuracy, incorrect = await verify_toc(
        structure, page_list, provider, sample_rate=1.0
    )
    assert accuracy == 0.0
    assert len(incorrect) == 3
    incorrect_titles = {item["title"] for item in incorrect}
    assert incorrect_titles == {"A", "B", "C"}


@pytest.mark.asyncio
async def test_verify_toc_empty_structure():
    provider = _mock_async_provider([])
    accuracy, incorrect = await verify_toc([], [], provider)
    assert accuracy == 0.0
    assert incorrect == []


@pytest.mark.asyncio
async def test_verify_toc_skips_none_physical_index():
    provider = _mock_async_provider(['{"answer": "yes"}'])
    structure = [
        {"title": "A", "physical_index": None},
        {"title": "B", "physical_index": 5},
    ]
    page_list = [("text",)] * 10
    accuracy, incorrect = await verify_toc(
        structure, page_list, provider, sample_rate=1.0
    )
    # Only one valid item checked
    assert accuracy == 1.0
