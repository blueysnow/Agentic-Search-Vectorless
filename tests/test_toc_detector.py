"""Tests for src/ingestion/tree_builder/toc_detector.py."""

from unittest.mock import MagicMock


from src.ingestion.tree_builder.toc_detector import (
    check_toc,
    detect_page_index,
    find_toc_pages,
    toc_detector_single_page,
    toc_extractor,
)
from src.llm.provider import LLMResponse


def _mock_provider(responses: list[str], finish_reasons: list[str] | None = None):
    """Create a mock LLMProvider that returns predefined responses."""
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


# --- toc_detector_single_page ---


def test_toc_detector_single_page_yes():
    provider = _mock_provider(['{"thinking": "has ToC", "toc_detected": "yes"}'])
    result = toc_detector_single_page("Chapter 1 ... 3\nChapter 2 ... 15", provider)
    assert result == "yes"


def test_toc_detector_single_page_no():
    provider = _mock_provider(['{"thinking": "no ToC", "toc_detected": "no"}'])
    result = toc_detector_single_page("Regular text content", provider)
    assert result == "no"


def test_toc_detector_single_page_malformed_json():
    provider = _mock_provider(["not json at all"])
    result = toc_detector_single_page("some text", provider)
    assert result == "no"


# --- find_toc_pages ---


def test_find_toc_pages_consecutive():
    """Finds consecutive ToC pages and stops."""
    responses = [
        '{"toc_detected": "yes"}',
        '{"toc_detected": "yes"}',
        '{"toc_detected": "no"}',
    ]
    provider = _mock_provider(responses)
    page_list = [("page text",)] * 5
    result = find_toc_pages(page_list, provider, max_pages=20)
    assert result == [0, 1]


def test_find_toc_pages_none_found():
    responses = ['{"toc_detected": "no"}'] * 5
    provider = _mock_provider(responses)
    page_list = [("page text",)] * 5
    result = find_toc_pages(page_list, provider, max_pages=5)
    assert result == []


def test_find_toc_pages_respects_max_pages():
    responses = ['{"toc_detected": "no"}'] * 3
    provider = _mock_provider(responses)
    page_list = [("text",)] * 10
    result = find_toc_pages(page_list, provider, max_pages=3)
    assert result == []
    # Should only have called LLM 3 times
    assert provider.chat.call_count == 3


# --- detect_page_index ---


def test_detect_page_index_yes():
    provider = _mock_provider(['{"page_index_given_in_toc": "yes"}'])
    result = detect_page_index("Ch 1 ... 3\nCh 2 ... 15", provider)
    assert result == "yes"


def test_detect_page_index_no():
    provider = _mock_provider(['{"page_index_given_in_toc": "no"}'])
    result = detect_page_index("Chapter 1\nChapter 2", provider)
    assert result == "no"


# --- toc_extractor ---


def test_toc_extractor_with_page_index():
    provider = _mock_provider(['{"page_index_given_in_toc": "yes"}'])
    page_list = [("Chapter 1 ........... 3\nChapter 2 ........... 15",)]
    result = toc_extractor(page_list, [0], provider)
    assert result["page_index_given_in_toc"] == "yes"
    # Dots should be replaced with colons
    assert "........" not in result["toc_content"]


# --- check_toc ---


def test_check_toc_no_toc():
    responses = ['{"toc_detected": "no"}'] * 20
    provider = _mock_provider(responses)
    page_list = [("text",)] * 5
    result = check_toc(page_list, provider, max_pages=5)
    assert result["toc_content"] is None
    assert result["toc_page_list"] == []
    assert result["page_index_given_in_toc"] == "no"


def test_check_toc_found_with_page_index():
    responses = [
        '{"toc_detected": "yes"}',  # page 0
        '{"toc_detected": "no"}',  # page 1 -- ToC ends
        '{"page_index_given_in_toc": "yes"}',  # detect_page_index
    ]
    provider = _mock_provider(responses)
    page_list = [("Ch1...3\nCh2...15",), ("Regular text",)]
    result = check_toc(page_list, provider, max_pages=20)
    assert result["page_index_given_in_toc"] == "yes"
    assert result["toc_page_list"] == [0]
