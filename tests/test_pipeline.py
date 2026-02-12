"""Tests for src/ingestion/pipeline.py -- persistence functions and utilities."""

from src.ingestion.pipeline import (
    _validate_and_truncate,
)


# --- _validate_and_truncate ---


def test_validate_truncate_removes_over_max():
    items = [
        {"title": "A", "physical_index": 5},
        {"title": "B", "physical_index": 15},  # exceeds 10 pages
        {"title": "C", "physical_index": 8},
    ]
    result = _validate_and_truncate(items, page_list_length=10)
    assert result[0]["physical_index"] == 5
    assert result[1]["physical_index"] is None  # truncated
    assert result[2]["physical_index"] == 8


def test_validate_truncate_keeps_valid():
    items = [{"title": "A", "physical_index": 3}]
    result = _validate_and_truncate(items, page_list_length=10)
    assert result[0]["physical_index"] == 3


def test_validate_truncate_handles_none():
    items = [{"title": "A", "physical_index": None}]
    result = _validate_and_truncate(items, page_list_length=10)
    assert result[0]["physical_index"] is None


def test_validate_truncate_empty():
    assert _validate_and_truncate([], 10) == []


# --- Prompts existence checks ---


def test_prompts_toc_detection_importable():
    from src.llm.prompts.toc_detection import (
        TOC_DETECTION_PROMPT,
        TOC_CONTINUATION_PROMPT,
        PAGE_NUMBER_DETECTION_PROMPT,
    )

    assert "table of content" in TOC_DETECTION_PROMPT.lower()
    assert "continue" in TOC_CONTINUATION_PROMPT.lower()
    assert (
        "page numbers" in PAGE_NUMBER_DETECTION_PROMPT.lower()
        or "page_index" in PAGE_NUMBER_DETECTION_PROMPT.lower()
    )


def test_prompts_tree_building_importable():
    from src.llm.prompts.tree_building import (
        TOC_TO_JSON_PROMPT,
        TREE_GENERATION_INIT_PROMPT,
        TREE_GENERATION_CONTINUE_PROMPT,
        PAGE_NUMBER_MAPPING_PROMPT,
    )

    assert "table_of_contents" in TOC_TO_JSON_PROMPT
    assert "tree structure" in TREE_GENERATION_INIT_PROMPT.lower()
    assert "continue" in TREE_GENERATION_CONTINUE_PROMPT.lower()
    assert "physical_index" in PAGE_NUMBER_MAPPING_PROMPT.lower()


def test_prompts_verification_importable():
    from src.llm.prompts.verification import (
        TITLE_VERIFICATION_PROMPT,
        TITLE_AT_START_PROMPT,
    )

    assert "title" in TITLE_VERIFICATION_PROMPT.lower()
    assert "beginning" in TITLE_AT_START_PROMPT.lower()


def test_prompts_summarization_importable():
    from src.llm.prompts.summarization import (
        NODE_SUMMARY_PROMPT,
        DOC_DESCRIPTION_PROMPT,
        KEYWORD_EXTRACTION_PROMPT,
    )

    assert "description" in NODE_SUMMARY_PROMPT.lower()
    assert "description" in DOC_DESCRIPTION_PROMPT.lower()
    assert "keyword" in KEYWORD_EXTRACTION_PROMPT.lower()
