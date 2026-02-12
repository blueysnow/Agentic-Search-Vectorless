"""Tests for src/ingestion/tree_builder/toc_transformer.py."""

from unittest.mock import MagicMock


from src.ingestion.tree_builder.toc_transformer import (
    _convert_page_to_int,
    toc_index_extractor,
    toc_transformer,
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


# --- _convert_page_to_int ---


def test_convert_page_to_int():
    data = [{"title": "A", "page": "5"}, {"title": "B", "page": 10}]
    result = _convert_page_to_int(data)
    assert result[0]["page"] == 5
    assert result[1]["page"] == 10


def test_convert_page_to_int_invalid():
    data = [{"title": "A", "page": "N/A"}]
    result = _convert_page_to_int(data)
    assert result[0]["page"] == "N/A"  # stays as string


# --- toc_transformer ---


def test_toc_transformer_complete_on_first_try():
    toc_json = '{"table_of_contents": [{"structure": "1", "title": "Intro", "page": 1}, {"structure": "2", "title": "Body", "page": 5}]}'
    # First call: transform, second call: completeness check
    responses = [toc_json, '{"completed": "yes"}']
    provider = _mock_provider(responses)
    result = toc_transformer("Chapter 1: Intro ... 1\nChapter 2: Body ... 5", provider)
    assert len(result) == 2
    assert result[0]["title"] == "Intro"
    assert result[0]["page"] == 1


# --- toc_index_extractor ---


def test_toc_index_extractor():
    response_json = (
        '[{"structure": "1", "title": "Intro", "physical_index": "<physical_index_3>"}]'
    )
    provider = _mock_provider([response_json])
    toc_json = [{"structure": "1", "title": "Intro"}]
    page_list = [("page 1 text", 100), ("page 2 text", 100), ("page 3 text", 100)]
    result = toc_index_extractor(
        toc_json, page_list, provider, start_page_index=0, num_pages=3
    )
    assert len(result) == 1
    assert result[0]["physical_index"] == "<physical_index_3>"


def test_toc_index_extractor_malformed_response():
    provider = _mock_provider(["not valid json"])
    toc_json = [{"structure": "1", "title": "Intro"}]
    page_list = [("page text", 100)]
    result = toc_index_extractor(toc_json, page_list, provider)
    # Should return original toc_json on failure
    assert result == toc_json
