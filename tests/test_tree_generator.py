"""Tests for src/ingestion/tree_builder/tree_generator.py."""

from unittest.mock import MagicMock

import pytest

from src.ingestion.tree_builder.tree_generator import (
    generate_toc_continue,
    generate_toc_init,
    page_list_to_group_text,
    process_no_toc,
)
from src.llm.provider import LLMResponse


def _mock_provider(responses: list[str], finish_reasons: list[str] | None = None):
    provider = MagicMock()
    if finish_reasons is None:
        finish_reasons = ["finished"] * len(responses)
    call_count = {"i": 0}

    def chat_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason=finish_reasons[idx])

    provider.chat = MagicMock(side_effect=chat_side_effect)
    return provider


# --- page_list_to_group_text ---


def test_page_list_to_group_text_small_doc():
    """Small doc fits in one group."""
    page_list = [("Short page.", 5)] * 3
    result = page_list_to_group_text(page_list, max_tokens=100000)
    assert len(result) == 1
    assert "<physical_index_1>" in result[0]
    assert "<physical_index_3>" in result[0]


def test_page_list_to_group_text_splits_large_doc():
    """Large doc gets split into multiple groups."""
    # Each page ~100 tokens, total ~1000, limit 300
    page_list = [("x " * 50, 100)] * 10
    result = page_list_to_group_text(page_list, max_tokens=300)
    assert len(result) > 1


def test_page_list_to_group_text_custom_start_index():
    page_list = [("Text.", 5)] * 2
    result = page_list_to_group_text(page_list, max_tokens=100000, start_index=5)
    assert "<physical_index_5>" in result[0]
    assert "<physical_index_6>" in result[0]


# --- generate_toc_init ---


def test_generate_toc_init_success():
    response_json = (
        '[{"structure": "1", "title": "Intro", "physical_index": "<physical_index_1>"}]'
    )
    provider = _mock_provider([response_json])
    result = generate_toc_init("some text", provider)
    assert len(result) == 1
    assert result[0]["title"] == "Intro"


def test_generate_toc_init_not_finished():
    provider = _mock_provider(["partial"], finish_reasons=["max_output_reached"])
    with pytest.raises(RuntimeError, match="did not finish"):
        generate_toc_init("text", provider)


def test_generate_toc_init_bad_json():
    provider = _mock_provider(["not json"])
    with pytest.raises(ValueError, match="Failed to parse"):
        generate_toc_init("text", provider)


# --- generate_toc_continue ---


def test_generate_toc_continue_success():
    response_json = (
        '[{"structure": "2", "title": "Body", "physical_index": "<physical_index_5>"}]'
    )
    provider = _mock_provider([response_json])
    prev = [
        {"structure": "1", "title": "Intro", "physical_index": "<physical_index_1>"}
    ]
    result = generate_toc_continue("next text", prev, provider)
    assert len(result) == 1
    assert result[0]["title"] == "Body"


# --- process_no_toc ---


def test_process_no_toc_single_group():
    init_response = '[{"structure": "1", "title": "Section", "physical_index": "<physical_index_1>"}]'
    provider = _mock_provider([init_response])
    page_list = [("Short page", 10)]
    result = process_no_toc(page_list, provider)
    assert len(result) == 1
    assert result[0]["physical_index"] == 1  # converted from string to int
