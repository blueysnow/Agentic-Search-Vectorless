"""Tests for src/ingestion/enrichment/ modules."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ingestion.enrichment.content_classifier import classify_content_type
from src.ingestion.enrichment.cross_ref_detector import detect_cross_references
from src.ingestion.enrichment.keyword_extractor import extract_keywords
from src.ingestion.enrichment.summarizer import (
    generate_doc_description,
    generate_node_summary,
    generate_summaries_for_structure,
)
from src.llm.provider import LLMResponse


def _mock_async_provider(responses: list[str]):
    provider = MagicMock()
    call_count = {"i": 0}

    async def async_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason="finished")

    def sync_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason="finished")

    provider.chat_async = AsyncMock(side_effect=async_side_effect)
    provider.chat = MagicMock(side_effect=sync_side_effect)
    return provider


# --- content_classifier ---


def test_classify_section():
    assert classify_content_type("Introduction") == "section"


def test_classify_appendix():
    assert classify_content_type("Appendix A: Data Tables") == "appendix"


def test_classify_table():
    assert classify_content_type("Table 3.1") == "table"


def test_classify_figure():
    assert classify_content_type("Figure 2: System Architecture") == "figure"


def test_classify_preface():
    assert classify_content_type("Preface") == "preface"


def test_classify_bibliography():
    assert classify_content_type("References") == "bibliography"


def test_classify_abstract():
    assert classify_content_type("Abstract") == "abstract"


# --- cross_ref_detector ---


def test_detect_cross_refs_see_section():
    text = "As discussed in this part, see Section 3.2 for details."
    refs = detect_cross_references(text)
    assert len(refs) == 1
    assert refs[0]["label"] == "3.2"
    assert refs[0]["type"] == "section"


def test_detect_cross_refs_refer_to_chapter():
    text = "Please refer to Chapter 5 for background."
    refs = detect_cross_references(text)
    assert len(refs) == 1
    assert refs[0]["label"] == "5"
    assert refs[0]["type"] == "chapter"


def test_detect_cross_refs_appendix():
    text = "see Appendix B for full data."
    refs = detect_cross_references(text)
    assert len(refs) == 1
    assert refs[0]["type"] == "appendix"


def test_detect_cross_refs_none():
    text = "This is regular text with no cross-references."
    refs = detect_cross_references(text)
    assert refs == []


def test_detect_cross_refs_dedup():
    text = "see Section 3.2 for details. Also see Section 3.2 again."
    refs = detect_cross_references(text)
    assert len(refs) == 1  # Deduplicated


def test_detect_cross_refs_empty():
    assert detect_cross_references("") == []


# --- keyword_extractor ---


@pytest.mark.asyncio
async def test_extract_keywords():
    provider = _mock_async_provider(
        ['["machine learning", "neural networks", "deep learning"]']
    )
    result = await extract_keywords("Machine learning and neural networks...", provider)
    assert len(result) == 3
    assert "machine learning" in result


@pytest.mark.asyncio
async def test_extract_keywords_empty_text():
    provider = _mock_async_provider([""])
    result = await extract_keywords("", provider)
    assert result == []


@pytest.mark.asyncio
async def test_extract_keywords_malformed():
    provider = _mock_async_provider(["not json"])
    result = await extract_keywords("some text", provider)
    assert result == []


# --- summarizer ---


@pytest.mark.asyncio
async def test_generate_node_summary():
    provider = _mock_async_provider(["This section covers machine learning basics."])
    result = await generate_node_summary("ML is a subset of AI...", provider)
    assert "machine learning" in result.lower()


@pytest.mark.asyncio
async def test_generate_summaries_for_structure():
    provider = _mock_async_provider(["Summary A", "Summary B"])
    structure = [
        {"title": "A", "text": "text A"},
        {"title": "B", "text": "text B"},
    ]
    result = await generate_summaries_for_structure(structure, provider)
    assert result[0]["summary"] == "Summary A"
    assert result[1]["summary"] == "Summary B"


def test_generate_doc_description():
    provider = _mock_async_provider(["A comprehensive guide to ML."])
    structure = [
        {"title": "ML Guide", "node_id": "0001", "summary": "Covers ML basics"}
    ]
    result = generate_doc_description(structure, provider)
    assert "ML" in result
