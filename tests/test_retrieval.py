"""Tests for Phase 3: Retrieval Pipeline -- all 9 modules.

Covers:
1. LLM Prompt Templates (tree_navigation, sufficiency_check, query_analysis)
2. Query Analyzer (src/retrieval/query_analyzer.py)
3. Atlas Search Query Builder (src/retrieval/atlas_search.py)
4. Tree Navigator (src/retrieval/tree_navigator.py)
5. Result Merger (src/retrieval/merger.py)
6. Content Loader (src/retrieval/content_loader.py)
7. LLM Reasoner (src/retrieval/reasoner.py)
8. Session Manager (src/retrieval/session_manager.py)
9. Retrieval Orchestrator (src/retrieval/pipeline.py)
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.provider import LLMResponse
from src.models.retrieval import NextAction, ReasonerResponse, RetrievalCandidate


# ============================================================================
# Helpers
# ============================================================================


def _mock_llm_provider(responses: list[str]):
    """Create a mock LLM provider that returns responses in order."""
    provider = MagicMock()
    call_count = {"i": 0}

    async def async_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason="finished")

    provider.chat_async = AsyncMock(side_effect=async_side_effect)
    provider.chat = MagicMock(
        side_effect=lambda messages, **kwargs: LLMResponse(
            content=responses[min(call_count["i"], len(responses) - 1)],
            finish_reason="finished",
        )
    )
    return provider


# ============================================================================
# 1. Prompt Templates
# ============================================================================


class TestPromptTemplates:
    """Verify all retrieval prompt templates exist and contain expected content."""

    def test_tree_navigation_prompt_importable(self):
        from src.llm.prompts.tree_navigation import (
            TREE_NAVIGATION_PROMPT,
        )

        assert "{query}" in TREE_NAVIGATION_PROMPT
        assert "{sections}" in TREE_NAVIGATION_PROMPT
        assert "{document_name}" in TREE_NAVIGATION_PROMPT
        assert "selectedNodeIds" in TREE_NAVIGATION_PROMPT

    def test_tree_navigation_with_context_prompt(self):
        from src.llm.prompts.tree_navigation import TREE_NAVIGATION_WITH_CONTEXT_PROMPT

        assert "{visited_context}" in TREE_NAVIGATION_WITH_CONTEXT_PROMPT
        assert "{query}" in TREE_NAVIGATION_WITH_CONTEXT_PROMPT
        assert "selectedNodeIds" in TREE_NAVIGATION_WITH_CONTEXT_PROMPT

    def test_sufficiency_check_prompt_importable(self):
        from src.llm.prompts.sufficiency_check import (
            SUFFICIENCY_CHECK_PROMPT,
        )

        assert "{query}" in SUFFICIENCY_CHECK_PROMPT
        assert "{content}" in SUFFICIENCY_CHECK_PROMPT
        assert "sufficient" in SUFFICIENCY_CHECK_PROMPT
        assert "nextAction" in SUFFICIENCY_CHECK_PROMPT

    def test_multi_turn_sufficiency_prompt(self):
        from src.llm.prompts.sufficiency_check import MULTI_TURN_SUFFICIENCY_PROMPT

        assert "{conversation_history}" in MULTI_TURN_SUFFICIENCY_PROMPT
        assert "{query}" in MULTI_TURN_SUFFICIENCY_PROMPT

    def test_query_analysis_prompt_importable(self):
        from src.llm.prompts.query_analysis import QUERY_ANALYSIS_PROMPT

        assert "{query}" in QUERY_ANALYSIS_PROMPT
        assert "query_type" in QUERY_ANALYSIS_PROMPT
        assert "keywords" in QUERY_ANALYSIS_PROMPT
        assert "factual_lookup" in QUERY_ANALYSIS_PROMPT

    def test_prompts_use_xml_delimiters(self):
        """All prompts must use XML delimiters for user content per project patterns."""
        from src.llm.prompts.query_analysis import QUERY_ANALYSIS_PROMPT
        from src.llm.prompts.sufficiency_check import SUFFICIENCY_CHECK_PROMPT
        from src.llm.prompts.tree_navigation import TREE_NAVIGATION_PROMPT

        for prompt in [
            TREE_NAVIGATION_PROMPT,
            SUFFICIENCY_CHECK_PROMPT,
            QUERY_ANALYSIS_PROMPT,
        ]:
            assert "<" in prompt and ">" in prompt, "Prompt must use XML delimiters"


# ============================================================================
# 2. Query Analyzer
# ============================================================================


class TestQueryAnalyzer:

    @pytest.mark.asyncio
    async def test_analyze_query_factual(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["revenue", "2024"],
                        "expected_content_type": "table",
                        "reasoning": "Asking for specific factual data",
                    }
                )
            ]
        )
        result = await analyze_query(
            "What was the revenue in 2024?", "Report", "Annual Report", provider
        )
        assert result.query_type == "factual_lookup"
        assert "revenue" in result.keywords
        assert result.expected_content_type == "table"

    @pytest.mark.asyncio
    async def test_analyze_query_analytical(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "analytical",
                        "keywords": ["impact", "regulations"],
                        "expected_content_type": "section",
                        "reasoning": "Requires analysis",
                    }
                )
            ]
        )
        result = await analyze_query(
            "How did new regulations impact the business?", "Report", "Annual", provider
        )
        assert result.query_type == "analytical"

    @pytest.mark.asyncio
    async def test_analyze_query_empty(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = _mock_llm_provider([""])
        result = await analyze_query("", "Doc", "Desc", provider)
        assert result.keywords == []

    @pytest.mark.asyncio
    async def test_analyze_query_malformed_response(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = _mock_llm_provider(["not valid json at all"])
        result = await analyze_query(
            "What is the GDP?", "Report", "Econ report", provider
        )
        # Should fallback gracefully
        assert result.query_type == "factual_lookup"
        assert len(result.keywords) > 0  # Fallback keywords from query

    @pytest.mark.asyncio
    async def test_analyze_query_llm_failure(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = MagicMock()
        provider.chat_async = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await analyze_query("What happened?", "Doc", "Desc", provider)
        assert result.query_type == "factual_lookup"
        assert len(result.keywords) > 0  # Fallback keywords

    @pytest.mark.asyncio
    async def test_analyze_query_invalid_type(self):
        from src.retrieval.query_analyzer import analyze_query

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "invalid_type_here",
                        "keywords": ["test"],
                        "expected_content_type": "bogus",
                        "reasoning": "",
                    }
                )
            ]
        )
        result = await analyze_query("test query", "Doc", "Desc", provider)
        assert result.query_type == "factual_lookup"  # defaults
        assert result.expected_content_type == "any"  # defaults

    def test_fallback_keywords(self):
        from src.retrieval.query_analyzer import _fallback_keywords

        kws = _fallback_keywords("What is the revenue for 2024?")
        assert "revenue" in kws
        assert "2024" in kws
        assert "what" not in kws
        assert "is" not in kws
        assert "the" not in kws

    def test_fallback_keywords_empty(self):
        from src.retrieval.query_analyzer import _fallback_keywords

        assert _fallback_keywords("") == []

    def test_fallback_keywords_all_stopwords(self):
        from src.retrieval.query_analyzer import _fallback_keywords

        result = _fallback_keywords("what is the")
        assert result == []


# ============================================================================
# 3. Atlas Search Query Builder
# ============================================================================


class TestAtlasSearch:

    def test_build_search_pipeline_basic(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("revenue growth", "doc123", limit=5)
        assert len(pipeline) == 3
        assert "$search" in pipeline[0]
        assert "$limit" in pipeline[1]
        assert pipeline[1]["$limit"] == 5
        assert "$project" in pipeline[2]

    def test_build_search_pipeline_compound_structure(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("test query", "doc1")
        search = pipeline[0]["$search"]
        assert search["index"] == "nodes_fulltext"
        compound = search["compound"]
        assert "must" in compound
        assert "should" in compound
        assert compound["minimumShouldMatch"] == 1

    def test_build_search_pipeline_document_filter(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("test", "doc_abc")
        must = pipeline[0]["$search"]["compound"]["must"]
        assert any(
            c.get("equals", {}).get("path") == "documentId"
            and c.get("equals", {}).get("value") == "doc_abc"
            for c in must
        )

    def test_build_search_pipeline_fuzzy(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("fincial", "doc1", use_fuzzy=True)
        should = pipeline[0]["$search"]["compound"]["should"]
        title_clause = should[0]["text"]
        assert "fuzzy" in title_clause
        assert title_clause["fuzzy"]["maxEdits"] == 1

    def test_build_search_pipeline_content_type_filter(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("data", "doc1", content_type_filter="table")
        compound = pipeline[0]["$search"]["compound"]
        assert "filter" in compound
        assert compound["filter"][0]["equals"]["value"] == "table"

    def test_build_search_pipeline_no_content_type_filter(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("data", "doc1")
        compound = pipeline[0]["$search"]["compound"]
        assert "filter" not in compound

    def test_build_search_pipeline_boost_values(self):
        from src.retrieval.atlas_search import (
            KEYWORD_BOOST,
            SUMMARY_BOOST,
            TITLE_BOOST,
            build_search_pipeline,
        )

        pipeline = build_search_pipeline("test", "doc1")
        should = pipeline[0]["$search"]["compound"]["should"]
        # Title has highest boost
        assert should[0]["text"]["score"]["boost"]["value"] == TITLE_BOOST
        assert should[1]["text"]["score"]["boost"]["value"] == SUMMARY_BOOST
        assert should[2]["text"]["score"]["boost"]["value"] == KEYWORD_BOOST

    def test_build_search_pipeline_project_fields(self):
        from src.retrieval.atlas_search import build_search_pipeline

        pipeline = build_search_pipeline("test", "doc1")
        project = pipeline[2]["$project"]
        for field in ["nodeId", "title", "summary", "depth", "score"]:
            assert field in project

    @pytest.mark.asyncio
    async def test_atlas_search_handles_exception(self):
        from src.retrieval.atlas_search import atlas_search

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_col.return_value.aggregate.side_effect = RuntimeError("DB down")
            results = await atlas_search("test", "doc1")
            assert results == []

    @pytest.mark.asyncio
    async def test_atlas_search_returns_candidates(self):
        from src.retrieval.atlas_search import atlas_search

        mock_results = [
            {"nodeId": "0001", "score": 5.5, "title": "Intro"},
            {"nodeId": "0002", "score": 3.2, "title": "Chapter 1"},
        ]
        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_col.return_value.aggregate.return_value = mock_results
            results = await atlas_search("test", "doc1", limit=5)
            assert len(results) == 2
            assert results[0].node_id == "0001"
            assert results[0].atlas_score == 5.5
            assert results[0].source == "atlas"


# ============================================================================
# 4. Tree Navigator
# ============================================================================


class TestTreeNavigator:

    def test_format_sections(self):
        from src.retrieval.tree_navigator import _format_sections

        nodes = [
            {
                "nodeId": "0001",
                "title": "Introduction",
                "summary": "Overview",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            },
            {
                "nodeId": "0002",
                "title": "Methods",
                "summary": "",
                "startPage": 6,
                "endPage": 10,
                "depth": 0,
            },
        ]
        text = _format_sections(nodes)
        assert "0001" in text
        assert "Introduction" in text
        assert "Overview" in text
        assert "Methods" in text

    def test_format_sections_empty(self):
        from src.retrieval.tree_navigator import _format_sections

        assert _format_sections([]) == ""

    @pytest.mark.asyncio
    async def test_navigate_level_selects_nodes(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "selectedNodeIds": ["0002"],
                        "reasoning": "Methods section most relevant",
                    }
                )
            ]
        )
        nodes = [
            {
                "nodeId": "0001",
                "title": "Introduction",
                "summary": "",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            },
            {
                "nodeId": "0002",
                "title": "Methods",
                "summary": "",
                "startPage": 6,
                "endPage": 10,
                "depth": 0,
            },
        ]
        selected = await _navigate_level(
            "How was the study conducted?", "Report", "Research report", nodes, provider
        )
        assert selected == ["0002"]

    @pytest.mark.asyncio
    async def test_navigate_level_validates_ids(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "selectedNodeIds": ["0099", "0001"],  # 0099 doesn't exist
                        "reasoning": "test",
                    }
                )
            ]
        )
        nodes = [
            {
                "nodeId": "0001",
                "title": "A",
                "summary": "",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            }
        ]
        selected = await _navigate_level("test", "Doc", "Desc", nodes, provider)
        assert selected == ["0001"]
        assert "0099" not in selected

    @pytest.mark.asyncio
    async def test_navigate_level_empty_nodes(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = _mock_llm_provider([""])
        selected = await _navigate_level("test", "Doc", "Desc", [], provider)
        assert selected == []

    @pytest.mark.asyncio
    async def test_navigate_level_parse_failure(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = _mock_llm_provider(["not json"])
        nodes = [
            {
                "nodeId": "0001",
                "title": "A",
                "summary": "",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            }
        ]
        selected = await _navigate_level("test", "Doc", "Desc", nodes, provider)
        assert selected == []

    @pytest.mark.asyncio
    async def test_navigate_level_llm_exception(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = MagicMock()
        provider.chat_async = AsyncMock(side_effect=RuntimeError("LLM error"))
        nodes = [
            {
                "nodeId": "0001",
                "title": "A",
                "summary": "",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            }
        ]
        selected = await _navigate_level("test", "Doc", "Desc", nodes, provider)
        assert selected == []

    @pytest.mark.asyncio
    async def test_navigate_level_limits_to_max_selections(self):
        from src.retrieval.tree_navigator import (
            MAX_SELECTIONS_PER_LEVEL,
            _navigate_level,
        )

        # Return 5 IDs but max is 3
        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "selectedNodeIds": ["0001", "0002", "0003", "0004", "0005"],
                        "reasoning": "all relevant",
                    }
                )
            ]
        )
        nodes = [
            {
                "nodeId": f"000{i}",
                "title": f"S{i}",
                "summary": "",
                "startPage": i,
                "endPage": i + 1,
                "depth": 0,
            }
            for i in range(1, 6)
        ]
        selected = await _navigate_level("test", "Doc", "Desc", nodes, provider)
        assert len(selected) <= MAX_SELECTIONS_PER_LEVEL

    @pytest.mark.asyncio
    async def test_navigate_level_with_context(self):
        from src.retrieval.tree_navigator import _navigate_level

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "selectedNodeIds": ["0001"],
                        "reasoning": "test with context",
                    }
                )
            ]
        )
        nodes = [
            {
                "nodeId": "0001",
                "title": "A",
                "summary": "",
                "startPage": 1,
                "endPage": 5,
                "depth": 0,
            }
        ]
        selected = await _navigate_level(
            "test",
            "Doc",
            "Desc",
            nodes,
            provider,
            visited_context="Previously visited: [0003] Results",
        )
        assert selected == ["0001"]


# ============================================================================
# 5. Result Merger
# ============================================================================


class TestMerger:

    def test_merge_atlas_only(self):
        from src.retrieval.merger import merge_results

        atlas = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
            RetrievalCandidate(
                node_id="0002",
                atlas_score=3.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        result = merge_results(atlas, [], atlas_weight=0.3, tree_weight=0.7)
        assert len(result) == 2
        assert result[0].node_id == "0001"  # Higher atlas score
        assert result[0].source == "atlas"
        assert result[0].final_score > result[1].final_score

    def test_merge_tree_only(self):
        from src.retrieval.merger import merge_results

        tree = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.8,
                final_score=0.0,
                source="tree",
            ),
            RetrievalCandidate(
                node_id="0002",
                atlas_score=0.0,
                tree_score=0.4,
                final_score=0.0,
                source="tree",
            ),
        ]
        result = merge_results([], tree, atlas_weight=0.3, tree_weight=0.7)
        assert len(result) == 2
        assert result[0].node_id == "0001"
        assert result[0].source == "tree"

    def test_merge_both_sources(self):
        from src.retrieval.merger import merge_results

        atlas = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
            RetrievalCandidate(
                node_id="0003",
                atlas_score=2.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        tree = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.9,
                final_score=0.0,
                source="tree",
            ),
            RetrievalCandidate(
                node_id="0002",
                atlas_score=0.0,
                tree_score=0.7,
                final_score=0.0,
                source="tree",
            ),
        ]
        result = merge_results(atlas, tree, atlas_weight=0.3, tree_weight=0.7)
        # 0001 should be top (both sources)
        assert result[0].node_id == "0001"
        assert result[0].source == "both"
        assert result[0].atlas_score > 0
        assert result[0].tree_score > 0

    def test_merge_empty_inputs(self):
        from src.retrieval.merger import merge_results

        result = merge_results([], [])
        assert result == []

    def test_merge_top_n(self):
        from src.retrieval.merger import merge_results

        atlas = [
            RetrievalCandidate(
                node_id=f"000{i}",
                atlas_score=float(i),
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            )
            for i in range(1, 8)
        ]
        result = merge_results(atlas, [], top_n=3)
        assert len(result) == 3

    def test_merge_deduplication(self):
        from src.retrieval.merger import merge_results

        atlas = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            )
        ]
        tree = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.8,
                final_score=0.0,
                source="tree",
            )
        ]
        result = merge_results(atlas, tree)
        assert len(result) == 1
        assert result[0].node_id == "0001"
        assert result[0].source == "both"

    def test_merge_weighted_scoring(self):
        from src.retrieval.merger import merge_results

        atlas = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=10.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        tree = [
            RetrievalCandidate(
                node_id="0002",
                atlas_score=0.0,
                tree_score=1.0,
                final_score=0.0,
                source="tree",
            ),
        ]
        # With atlas_weight=0.3 and tree_weight=0.7, tree-only node should score higher
        result = merge_results(atlas, tree, atlas_weight=0.3, tree_weight=0.7)
        # 0001: atlas_score normalized to 1.0 * 0.3 = 0.3
        # 0002: tree_score normalized to 1.0 * 0.7 = 0.7
        assert result[0].node_id == "0002"
        assert result[0].final_score > result[1].final_score

    def test_normalize_scores_equal(self):
        from src.retrieval.merger import _normalize_scores

        candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
            RetrievalCandidate(
                node_id="0002",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        _normalize_scores(candidates, "atlas_score")
        assert candidates[0].atlas_score == 1.0
        assert candidates[1].atlas_score == 1.0

    def test_normalize_scores_zero(self):
        from src.retrieval.merger import _normalize_scores

        candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        _normalize_scores(candidates, "atlas_score")
        assert candidates[0].atlas_score == 0.0


# ============================================================================
# 6. Content Loader
# ============================================================================


class TestContentLoader:

    def test_format_ancestor_context_empty(self):
        from src.retrieval.content_loader import format_ancestor_context

        result = format_ancestor_context([])
        assert "No ancestor" in result

    def test_format_ancestor_context_with_ancestors(self):
        from src.retrieval.content_loader import format_ancestor_context

        ancestors = [
            {
                "nodeId": "0001",
                "title": "Introduction",
                "summary": "Overview of the doc",
                "depth": 0,
            },
            {
                "nodeId": "0003",
                "title": "Methods",
                "summary": "Research methods",
                "depth": 1,
            },
        ]
        result = format_ancestor_context(ancestors)
        assert "Introduction" in result
        assert "Methods" in result

    def test_format_cross_references_empty(self):
        from src.retrieval.content_loader import format_cross_references

        result = format_cross_references([])
        assert "No cross-references" in result

    def test_format_cross_references_with_refs(self):
        from src.retrieval.content_loader import format_cross_references

        refs = [
            {"label": "A", "type": "appendix", "targetNodeId": "0010"},
            {"label": "3.2", "type": "section", "targetNodeId": "0005"},
        ]
        result = format_cross_references(refs)
        assert "appendix" in result
        assert "section" in result

    def test_load_node_content_with_mock(self):
        from src.retrieval.content_loader import load_node_content

        mock_pages = [
            {"content": "Page 1 content", "pageNumber": 1},
            {"content": "Page 2 content", "pageNumber": 2},
        ]
        with patch("src.retrieval.content_loader.pages_col") as mock_col:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_pages
            mock_col.return_value.find.return_value = mock_cursor
            result = load_node_content("doc1", "0001")
            assert "Page 1 content" in result
            assert "Page 2 content" in result

    def test_load_node_content_empty(self):
        from src.retrieval.content_loader import load_node_content

        with (
            patch("src.retrieval.content_loader.pages_col") as mock_pages_col,
            patch("src.retrieval.content_loader.nodes_col") as mock_nodes_col,
        ):
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = []
            mock_pages_col.return_value.find.return_value = mock_cursor
            mock_nodes_col.return_value.find_one.return_value = None
            result = load_node_content("doc1", "0001")
            assert result == ""

    def test_load_node_ancestors_with_mock(self):
        from src.retrieval.content_loader import load_node_ancestors

        with patch("src.retrieval.content_loader.nodes_col") as mock_col:
            mock_col.return_value.find_one.return_value = {
                "materializedPath": "/0001/0003/0006"
            }
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = [
                {
                    "nodeId": "0001",
                    "title": "Root",
                    "summary": "Root section",
                    "depth": 0,
                },
                {
                    "nodeId": "0003",
                    "title": "Child",
                    "summary": "Child section",
                    "depth": 1,
                },
            ]
            mock_col.return_value.find.return_value = mock_cursor
            result = load_node_ancestors("doc1", "0006")
            assert len(result) == 2
            assert result[0]["nodeId"] == "0001"

    def test_load_node_ancestors_no_node(self):
        from src.retrieval.content_loader import load_node_ancestors

        with patch("src.retrieval.content_loader.nodes_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            result = load_node_ancestors("doc1", "0099")
            assert result == []

    def test_load_candidates_content(self):
        from src.retrieval.content_loader import load_candidates_content

        with (
            patch("src.retrieval.content_loader.pages_col") as mock_pages_col,
            patch("src.retrieval.content_loader.nodes_col") as mock_nodes_col,
        ):
            # Mock pages
            mock_page_cursor = MagicMock()
            mock_page_cursor.sort.return_value = [
                {"content": "Test content", "pageNumber": 1}
            ]
            mock_pages_col.return_value.find.return_value = mock_page_cursor

            # Mock nodes for ancestors
            mock_nodes_col.return_value.find_one.side_effect = [
                {"materializedPath": "/0001"},  # ancestors lookup
                {"crossReferences": []},  # cross refs
            ]
            mock_node_cursor = MagicMock()
            mock_node_cursor.sort.return_value = []
            mock_nodes_col.return_value.find.return_value = mock_node_cursor

            result = load_candidates_content("doc1", ["0001"])
            assert "0001" in result
            assert "content" in result["0001"]


# ============================================================================
# 7. LLM Reasoner
# ============================================================================


class TestReasoner:

    def test_parse_sufficient_response(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {
                "answer": "The revenue was $1.2B in 2024.",
                "confidence": 0.95,
                "sufficient": True,
                "nextAction": None,
            }
        )
        result = _parse_reasoner_response(raw)
        assert result.sufficient is True
        assert result.answer == "The revenue was $1.2B in 2024."
        assert result.confidence == 0.95
        assert result.next_action is None

    def test_parse_insufficient_response(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {
                "answer": None,
                "confidence": 0.3,
                "sufficient": False,
                "nextAction": {
                    "type": "navigate_deeper",
                    "targetNodeId": "0005",
                    "reasoning": "Need to check subsection",
                },
            }
        )
        result = _parse_reasoner_response(raw)
        assert result.sufficient is False
        assert result.answer is None
        assert result.next_action is not None
        assert result.next_action.type == "navigate_deeper"
        assert result.next_action.target_node_id == "0005"

    def test_parse_follow_reference(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {
                "answer": None,
                "confidence": 0.2,
                "sufficient": False,
                "nextAction": {
                    "type": "follow_reference",
                    "targetNodeId": "0010",
                    "reasoning": "See Appendix A for details",
                },
            }
        )
        result = _parse_reasoner_response(raw)
        assert result.next_action.type == "follow_reference"

    def test_parse_invalid_action_type(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {
                "answer": None,
                "confidence": 0.0,
                "sufficient": False,
                "nextAction": {
                    "type": "invalid_type",
                    "targetNodeId": "0001",
                    "reasoning": "",
                },
            }
        )
        result = _parse_reasoner_response(raw)
        assert result.next_action is None  # Invalid type filtered

    def test_parse_malformed_json(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        result = _parse_reasoner_response("not json at all")
        assert result.sufficient is False
        assert result.answer is None
        assert result.confidence == 0.0

    def test_parse_confidence_clamped(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {"answer": "yes", "confidence": 1.5, "sufficient": True, "nextAction": None}
        )
        result = _parse_reasoner_response(raw)
        assert result.confidence == 1.0  # Clamped to max 1.0

        raw2 = json.dumps(
            {
                "answer": "no",
                "confidence": -0.5,
                "sufficient": False,
                "nextAction": None,
            }
        )
        result2 = _parse_reasoner_response(raw2)
        assert result2.confidence == 0.0  # Clamped to min 0.0

    def test_parse_confidence_non_numeric(self):
        from src.retrieval.reasoner import _parse_reasoner_response

        raw = json.dumps(
            {
                "answer": "yes",
                "confidence": "high",
                "sufficient": True,
                "nextAction": None,
            }
        )
        result = _parse_reasoner_response(raw)
        assert result.confidence == 0.0  # Defaults on parse failure

    @pytest.mark.asyncio
    async def test_check_sufficiency(self):
        from src.retrieval.reasoner import check_sufficiency

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "answer": "The answer is 42.",
                        "confidence": 0.9,
                        "sufficient": True,
                        "nextAction": None,
                    }
                )
            ]
        )
        result = await check_sufficiency(
            "What is the answer?",
            "Content about 42",
            "Root > Chapter 1",
            "No cross-refs",
            provider,
        )
        assert result.sufficient is True
        assert result.answer == "The answer is 42."

    @pytest.mark.asyncio
    async def test_check_sufficiency_empty_content(self):
        from src.retrieval.reasoner import check_sufficiency

        provider = _mock_llm_provider([""])
        result = await check_sufficiency("test", "", "context", "refs", provider)
        assert result.sufficient is False
        assert result.answer is None

    @pytest.mark.asyncio
    async def test_check_sufficiency_llm_failure(self):
        from src.retrieval.reasoner import check_sufficiency

        provider = MagicMock()
        provider.chat_async = AsyncMock(side_effect=RuntimeError("LLM error"))
        result = await check_sufficiency(
            "test", "some content", "ctx", "refs", provider
        )
        assert result.sufficient is False

    @pytest.mark.asyncio
    async def test_check_sufficiency_multi_turn(self):
        from src.retrieval.reasoner import check_sufficiency_multi_turn

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "answer": "Follow-up answer",
                        "confidence": 0.85,
                        "sufficient": True,
                        "nextAction": None,
                    }
                )
            ]
        )
        result = await check_sufficiency_multi_turn(
            "Follow-up question?",
            "Content",
            "Context",
            "Q: original\nA: original answer",
            provider,
        )
        assert result.sufficient is True
        assert result.answer == "Follow-up answer"

    @pytest.mark.asyncio
    async def test_check_sufficiency_multi_turn_empty_content(self):
        from src.retrieval.reasoner import check_sufficiency_multi_turn

        provider = _mock_llm_provider([""])
        result = await check_sufficiency_multi_turn(
            "test", "", "ctx", "history", provider
        )
        assert result.sufficient is False


# ============================================================================
# 8. Session Manager
# ============================================================================


class TestSessionManager:

    def test_create_session(self):
        from src.retrieval.session_manager import create_session

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.insert_one = MagicMock()
            session = create_session(
                document_id="doc1", user_id="user1", session_id="sess-123"
            )
            assert session.session_id == "sess-123"
            assert session.document_id == "doc1"
            mock_col.return_value.insert_one.assert_called_once()

    def test_create_session_auto_id(self):
        from src.retrieval.session_manager import create_session

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.insert_one = MagicMock()
            session = create_session(document_id="doc1")
            assert len(session.session_id) > 0  # UUID generated

    def test_get_session_found(self):
        from src.retrieval.session_manager import get_session

        mock_doc = {
            "sessionId": "sess-123",
            "documentId": "doc1",
            "userId": None,
            "turns": [],
            "summary": {
                "totalTurns": 0,
                "totalNodesVisited": 0,
                "avgReasoningDepth": 0.0,
                "totalLatencyMs": 0,
            },
            "createdAt": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
            "_id": "mongo_id",
        }
        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = mock_doc
            session = get_session("sess-123")
            assert session is not None
            assert session.session_id == "sess-123"

    def test_get_session_not_found(self):
        from src.retrieval.session_manager import get_session

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            session = get_session("nonexistent")
            assert session is None

    def test_add_turn(self):
        from src.retrieval.session_manager import add_turn

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = {"turns": []}
            mock_col.return_value.update_one = MagicMock()

            turn = add_turn(
                session_id="sess-123",
                query="What is revenue?",
                answer="Revenue is $1.2B",
                model="claude-opus-4-6",
                latency_ms=1500,
                atlas_search_hits=[{"nodeId": "0001", "score": 5.0, "field": "title"}],
                tree_navigation_path=["0001", "0003"],
                nodes_read=["0001", "0003"],
                total_nodes_visited=2,
                reasoning_depth=1,
            )
            assert turn.turn_number == 1
            assert turn.query == "What is revenue?"
            assert turn.answer == "Revenue is $1.2B"
            mock_col.return_value.update_one.assert_called_once()

    def test_add_turn_increments_turn_number(self):
        from src.retrieval.session_manager import add_turn

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = {
                "turns": [{"turnNumber": 1}, {"turnNumber": 2}]
            }
            mock_col.return_value.update_one = MagicMock()

            turn = add_turn(session_id="sess-123", query="Follow up?", answer="Yes")
            assert turn.turn_number == 3

    def test_get_conversation_history(self):
        from src.retrieval.session_manager import get_conversation_history

        mock_session_data = {
            "sessionId": "sess-123",
            "documentId": "doc1",
            "userId": None,
            "turns": [
                {
                    "turnNumber": 1,
                    "query": "What is GDP?",
                    "answer": "GDP is $25T",
                    "retrievalTrace": {
                        "atlasSearchHits": [],
                        "treeNavigationPath": [],
                        "nodesRead": [],
                        "crossReferencesFollowed": [],
                        "totalNodesVisited": 0,
                        "reasoningDepth": 0,
                    },
                    "model": "",
                    "latencyMs": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            ],
            "summary": {
                "totalTurns": 1,
                "totalNodesVisited": 0,
                "avgReasoningDepth": 0.0,
                "totalLatencyMs": 0,
            },
            "createdAt": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
        }
        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = mock_session_data
            history = get_conversation_history("sess-123")
            assert "What is GDP?" in history
            assert "GDP is $25T" in history

    def test_get_conversation_history_empty(self):
        from src.retrieval.session_manager import get_conversation_history

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            history = get_conversation_history("nonexistent")
            assert history == ""

    def test_get_previously_visited_nodes(self):
        from src.retrieval.session_manager import get_previously_visited_nodes

        mock_session_data = {
            "sessionId": "sess-123",
            "documentId": "doc1",
            "userId": None,
            "turns": [
                {
                    "turnNumber": 1,
                    "query": "Q1",
                    "answer": "A1",
                    "retrievalTrace": {
                        "atlasSearchHits": [],
                        "treeNavigationPath": ["0001", "0003"],
                        "nodesRead": ["0003"],
                        "crossReferencesFollowed": [],
                        "totalNodesVisited": 1,
                        "reasoningDepth": 0,
                    },
                    "model": "",
                    "latencyMs": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            ],
            "summary": {
                "totalTurns": 1,
                "totalNodesVisited": 1,
                "avgReasoningDepth": 0.0,
                "totalLatencyMs": 0,
            },
            "createdAt": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
        }
        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = mock_session_data
            visited = get_previously_visited_nodes("sess-123")
            assert "0001" in visited
            assert "0003" in visited
            # Should be deduplicated
            assert len(visited) == len(set(visited))

    def test_get_previously_visited_nodes_no_session(self):
        from src.retrieval.session_manager import get_previously_visited_nodes

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            visited = get_previously_visited_nodes("nonexistent")
            assert visited == []


# ============================================================================
# 9. Retrieval Pipeline Orchestrator
# ============================================================================


class TestRetrievalPipeline:

    def test_retrieval_result_defaults(self):
        from src.retrieval.pipeline import RetrievalResult

        result = RetrievalResult()
        assert result.answer is None
        assert result.confidence == 0.0
        assert result.session_id == ""
        assert result.trace == {}
        assert result.candidates == []
        assert result.iterations == 0

    def test_retrieval_result_with_values(self):
        from src.retrieval.pipeline import RetrievalResult

        result = RetrievalResult(
            answer="Test answer",
            confidence=0.9,
            session_id="sess-1",
            iterations=2,
        )
        assert result.answer == "Test answer"
        assert result.confidence == 0.9
        assert result.session_id == "sess-1"
        assert result.iterations == 2

    def test_get_document_info(self):
        from src.retrieval.pipeline import _get_document_info

        with patch("src.retrieval.pipeline.documents_col") as mock_col:
            mock_col.return_value.find_one.return_value = {
                "name": "Report",
                "description": "Annual",
            }
            name, desc = _get_document_info("doc1")
            assert name == "Report"
            assert desc == "Annual"

    def test_get_document_info_not_found(self):
        from src.retrieval.pipeline import _get_document_info

        with patch("src.retrieval.pipeline.documents_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            name, desc = _get_document_info("nonexistent")
            assert name == "Unknown"
            assert desc == ""

    @pytest.mark.asyncio
    async def test_retrieve_no_candidates(self):
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                # Query analysis response
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
            ]
        )

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=([], []),
            ),
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }

            result = await retrieve("test query", "doc1", provider)
            assert result.answer is None
            assert result.candidates == []

    @pytest.mark.asyncio
    async def test_retrieve_with_sufficient_answer(self):
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                # Query analysis (call 1)
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["revenue"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
                # Sufficiency check (call 2) -- tree_navigate and atlas_search are fully mocked
                json.dumps(
                    {
                        "answer": "Revenue is $1.2B",
                        "confidence": 0.95,
                        "sufficient": True,
                        "nextAction": None,
                    }
                ),
            ]
        )

        atlas_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]
        tree_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.8,
                final_score=0.0,
                source="tree",
            ),
        ]

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                return_value=atlas_candidates,
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=(tree_candidates, ["0001"]),
            ),
            patch("src.retrieval.pipeline.load_candidates_content") as mock_load,
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Report",
                "description": "Annual",
            }
            mock_load.return_value = {
                "0001": {
                    "content": "Revenue was $1.2B in 2024.",
                    "ancestors": [],
                    "ancestor_context": "Root > Financials",
                    "cross_refs": [],
                    "cross_ref_text": "No cross-references.",
                },
            }

            result = await retrieve("What is the revenue?", "doc1", provider)
            assert result.answer == "Revenue is $1.2B"
            assert result.confidence == 0.95
            assert len(result.candidates) > 0


# ============================================================================
# Additional edge case tests
# ============================================================================


class TestEdgeCases:

    def test_retrieval_candidate_model(self):
        c = RetrievalCandidate(
            node_id="0001",
            atlas_score=1.0,
            tree_score=0.5,
            final_score=0.65,
            source="both",
        )
        assert c.node_id == "0001"
        assert c.final_score == 0.65

    def test_next_action_model(self):
        na = NextAction(
            type="navigate_deeper", target_node_id="0005", reasoning="Need more detail"
        )
        assert na.type == "navigate_deeper"
        assert na.target_node_id == "0005"

    def test_reasoner_response_model(self):
        rr = ReasonerResponse(
            answer="Test",
            confidence=0.8,
            sufficient=True,
            next_action=None,
        )
        assert rr.answer == "Test"
        assert rr.sufficient is True

    def test_query_analysis_class(self):
        from src.retrieval.query_analyzer import QueryAnalysis

        qa = QueryAnalysis(
            query_type="analytical",
            keywords=["revenue", "growth"],
            expected_content_type="table",
            reasoning="Financial query",
        )
        assert qa.query_type == "analytical"
        assert len(qa.keywords) == 2

    def test_query_analysis_invalid_defaults(self):
        from src.retrieval.query_analyzer import QueryAnalysis

        qa = QueryAnalysis(query_type="bogus", expected_content_type="invalid")
        assert qa.query_type == "factual_lookup"
        assert qa.expected_content_type == "any"


# ============================================================================
# Regression tests for reviewer-caught bugs
# ============================================================================


class TestReviewerRegressions:
    """Tests for bugs caught by live-reviewer in pipeline.py."""

    @pytest.mark.asyncio
    async def test_gather_exception_does_not_crash_unpack(self):
        """STOP 1 regression: asyncio.gather exception must not crash tuple unpack."""
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
            ]
        )

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Atlas down"),
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Tree nav down"),
            ),
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }

            # Should NOT raise TypeError from tuple unpack
            result = await retrieve("test query", "doc1", provider)
            assert result.answer is None
            assert result.candidates == []

    @pytest.mark.asyncio
    async def test_gather_one_exception_one_success(self):
        """STOP 1 regression: one task fails, other succeeds -- pipeline continues."""
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
                json.dumps(
                    {
                        "answer": "Found it",
                        "confidence": 0.9,
                        "sufficient": True,
                        "nextAction": None,
                    }
                ),
            ]
        )

        tree_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=0.0,
                tree_score=0.8,
                final_score=0.0,
                source="tree",
            ),
        ]

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Atlas down"),
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=(tree_candidates, ["0001"]),
            ),
            patch("src.retrieval.pipeline.load_candidates_content") as mock_load,
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }
            mock_load.return_value = {
                "0001": {
                    "content": "Some content",
                    "ancestors": [],
                    "ancestor_context": "",
                    "cross_refs": [],
                    "cross_ref_text": "",
                },
            }

            result = await retrieve("test query", "doc1", provider)
            assert result.answer == "Found it"
            assert len(result.candidates) == 1

    @pytest.mark.asyncio
    async def test_iteration_count_tracks_actual_iterations(self):
        """STOP 2 regression: iteration count must reflect actual loop iterations, not always 1."""
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                # Query analysis
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
                # Iteration 1: insufficient, navigate deeper
                json.dumps(
                    {
                        "answer": None,
                        "confidence": 0.3,
                        "sufficient": False,
                        "nextAction": {
                            "type": "navigate_deeper",
                            "targetNodeId": "0003",
                            "reasoning": "need more",
                        },
                    }
                ),
                # Iteration 2: sufficient
                json.dumps(
                    {
                        "answer": "Final answer",
                        "confidence": 0.95,
                        "sufficient": True,
                        "nextAction": None,
                    }
                ),
            ]
        )

        atlas_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                return_value=atlas_candidates,
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=([], []),
            ),
            patch("src.retrieval.pipeline.load_candidates_content") as mock_load,
            patch(
                "src.retrieval.pipeline.load_node_content",
                return_value="Deeper content here",
            ),
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }
            mock_load.return_value = {
                "0001": {
                    "content": "Initial content",
                    "ancestors": [],
                    "ancestor_context": "",
                    "cross_refs": [],
                    "cross_ref_text": "",
                },
            }

            result = await retrieve("test query", "doc1", provider)
            assert result.answer == "Final answer"
            assert result.trace["iterations"] == 2  # Must be 2, not 1


# ============================================================================
# Hunter audit regression tests (H1-H5, M3)
# ============================================================================


class TestHunterRegressions:
    """Regression tests for hunter audit findings."""

    @pytest.mark.asyncio
    async def test_h1_tree_nav_returns_partial_on_mid_level_failure(self):
        """H1: tree_navigate returns partial results when LLM fails mid-navigation."""
        from src.retrieval.tree_navigator import tree_navigate

        call_count = {"i": 0}

        async def llm_side_effect(messages, **kwargs):
            call_count["i"] += 1
            if call_count["i"] == 1:
                # First level succeeds
                return LLMResponse(
                    content=json.dumps(
                        {"selectedNodeIds": ["0001"], "reasoning": "ok"}
                    ),
                    finish_reason="finished",
                )
            # Second level fails
            raise RuntimeError("LLM down mid-navigation")

        provider = MagicMock()
        provider.chat_async = AsyncMock(side_effect=llm_side_effect)

        with (
            patch("src.retrieval.tree_navigator._get_root_nodes") as mock_root,
            patch("src.retrieval.tree_navigator._get_children_batch") as mock_children,
        ):
            mock_root.return_value = [
                {
                    "nodeId": "0001",
                    "title": "Intro",
                    "summary": "",
                    "startPage": 1,
                    "endPage": 5,
                    "depth": 0,
                    "isLeaf": False,
                    "childNodeIds": ["0002"],
                },
            ]
            mock_children.return_value = [
                {
                    "nodeId": "0002",
                    "title": "Sub",
                    "summary": "",
                    "startPage": 2,
                    "endPage": 3,
                    "depth": 1,
                    "isLeaf": True,
                    "childNodeIds": [],
                },
            ]

            candidates, nav_path = await tree_navigate(
                "test", "doc1", "Doc", "Desc", provider
            )
            # Should have partial results from first successful level
            assert len(candidates) >= 1
            assert "0001" in nav_path

    def test_h2_session_add_turn_survives_db_error(self):
        """H2: add_turn does not crash on MongoDB errors."""
        from src.retrieval.session_manager import add_turn

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.side_effect = RuntimeError("DB down")
            mock_col.return_value.update_one = MagicMock()

            # Should not raise
            turn = add_turn(session_id="sess-1", query="test", answer="answer")
            assert turn.turn_number == 1  # Defaults to 1 on error

    def test_h2_session_add_turn_survives_update_error(self):
        """H2: add_turn logs warning but returns turn when update_one fails."""
        from src.retrieval.session_manager import add_turn

        with patch("src.retrieval.session_manager.retrieval_sessions_col") as mock_col:
            mock_col.return_value.find_one.return_value = {"turns": []}
            mock_col.return_value.update_one.side_effect = RuntimeError("Write failed")

            # Should not raise
            turn = add_turn(session_id="sess-1", query="test", answer="answer")
            assert turn.query == "test"

    def test_h3_content_loader_parallel_loading(self):
        """H3: load_candidates_content uses parallel loading."""
        from src.retrieval.content_loader import load_candidates_content

        with (
            patch(
                "src.retrieval.content_loader.load_node_content", return_value="content"
            ),
            patch("src.retrieval.content_loader.load_node_ancestors", return_value=[]),
            patch(
                "src.retrieval.content_loader.load_node_cross_references",
                return_value=[],
            ),
        ):
            result = load_candidates_content("doc1", ["0001", "0002", "0003"])
            assert len(result) == 3
            assert all(
                result[nid]["content"] == "content" for nid in ["0001", "0002", "0003"]
            )

    def test_h3_content_loader_survives_single_failure(self):
        """H3: One node failure doesn't kill the entire batch."""
        from src.retrieval.content_loader import load_candidates_content

        call_count = {"i": 0}

        def side_effect(doc_id, nid):
            call_count["i"] += 1
            if nid == "0002":
                raise RuntimeError("DB error for node 0002")
            return f"content-{nid}"

        with (
            patch(
                "src.retrieval.content_loader.load_node_content",
                side_effect=side_effect,
            ),
            patch("src.retrieval.content_loader.load_node_ancestors", return_value=[]),
            patch(
                "src.retrieval.content_loader.load_node_cross_references",
                return_value=[],
            ),
        ):
            result = load_candidates_content("doc1", ["0001", "0002", "0003"])
            assert len(result) == 3
            assert result["0001"]["content"] == "content-0001"
            assert result["0002"]["content"] == ""  # Failed gracefully
            assert result["0003"]["content"] == "content-0003"

    def test_h3_content_loader_empty_ids(self):
        """H3: Empty node_ids returns empty dict without creating ThreadPool."""
        from src.retrieval.content_loader import load_candidates_content

        result = load_candidates_content("doc1", [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_h5_hallucinated_node_id_skips_iteration(self):
        """H5: Hallucinated node ID with empty content doesn't waste iteration."""
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                # Query analysis
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
                # Iteration 1: insufficient, navigate to hallucinated node
                json.dumps(
                    {
                        "answer": None,
                        "confidence": 0.2,
                        "sufficient": False,
                        "nextAction": {
                            "type": "navigate_deeper",
                            "targetNodeId": "9999",
                            "reasoning": "hallucinated",
                        },
                    }
                ),
                # Iteration 2: sufficient (uses original content since 9999 was empty)
                json.dumps(
                    {
                        "answer": "Got it",
                        "confidence": 0.9,
                        "sufficient": True,
                        "nextAction": None,
                    }
                ),
            ]
        )

        atlas_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                return_value=atlas_candidates,
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=([], []),
            ),
            patch("src.retrieval.pipeline.load_candidates_content") as mock_load,
            patch("src.retrieval.pipeline.load_node_content", return_value=""),
        ):  # 9999 returns empty

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }
            mock_load.return_value = {
                "0001": {
                    "content": "Real content",
                    "ancestors": [],
                    "ancestor_context": "",
                    "cross_refs": [],
                    "cross_ref_text": "",
                },
            }

            result = await retrieve("test query", "doc1", provider)
            assert result.answer == "Got it"

    @pytest.mark.asyncio
    async def test_m3_session_persistence_failure_preserves_answer(self):
        """M3: Session persistence failure after answer computed still returns answer."""
        from src.retrieval.pipeline import retrieve

        provider = _mock_llm_provider(
            [
                json.dumps(
                    {
                        "query_type": "factual_lookup",
                        "keywords": ["test"],
                        "expected_content_type": "any",
                        "reasoning": "",
                    }
                ),
                json.dumps(
                    {
                        "answer": "The answer",
                        "confidence": 0.95,
                        "sufficient": True,
                        "nextAction": None,
                    }
                ),
            ]
        )

        atlas_candidates = [
            RetrievalCandidate(
                node_id="0001",
                atlas_score=5.0,
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            ),
        ]

        with (
            patch("src.retrieval.pipeline.documents_col") as mock_doc_col,
            patch(
                "src.retrieval.pipeline.atlas_search",
                new_callable=AsyncMock,
                return_value=atlas_candidates,
            ),
            patch(
                "src.retrieval.pipeline.tree_navigate",
                new_callable=AsyncMock,
                return_value=([], []),
            ),
            patch("src.retrieval.pipeline.load_candidates_content") as mock_load,
            patch("src.retrieval.pipeline.get_conversation_history", return_value=""),
            patch(
                "src.retrieval.pipeline.get_session",
                side_effect=RuntimeError("DB down"),
            ),
            patch(
                "src.retrieval.pipeline.create_session",
                side_effect=RuntimeError("DB down"),
            ),
            patch(
                "src.retrieval.pipeline.add_turn", side_effect=RuntimeError("DB down")
            ),
        ):

            mock_doc_col.return_value.find_one.return_value = {
                "name": "Doc",
                "description": "Desc",
            }
            mock_load.return_value = {
                "0001": {
                    "content": "Content here",
                    "ancestors": [],
                    "ancestor_context": "",
                    "cross_refs": [],
                    "cross_ref_text": "",
                },
            }

            # Should NOT crash despite session DB failure
            result = await retrieve("test", "doc1", provider, session_id="sess-broken")
            assert result.answer == "The answer"
            assert result.confidence == 0.95
