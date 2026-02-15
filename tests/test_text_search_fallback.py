"""Tests for MongoDB Community Edition text search fallback.

Covers:
1. text_search() function returns RetrievalCandidate objects
2. text_search() handles empty results gracefully
3. text_search() handles DB errors gracefully
4. ensure_text_index() creates the correct text index
5. atlas_search() falls back to text_search() when $search fails
6. detect_search_backend() detects Atlas vs Community
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from src.models.retrieval import RetrievalCandidate


class TestTextSearch:
    """Test the $text fallback for MongoDB Community Edition."""

    @pytest.mark.asyncio
    async def test_text_search_returns_candidates(self):
        """text_search() returns RetrievalCandidate objects from $text query."""
        from src.retrieval.atlas_search import text_search

        mock_results = [
            {"nodeId": "0001", "title": "Intro", "score": 5.5},
            {"nodeId": "0002", "title": "Chapter 1", "score": 3.2},
        ]
        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_results
            mock_col.return_value.find.return_value = mock_cursor
            results = await text_search("test query", "doc1", limit=5)
            assert len(results) == 2
            assert all(isinstance(r, RetrievalCandidate) for r in results)
            assert results[0].node_id == "0001"
            assert results[0].source == "text"

    @pytest.mark.asyncio
    async def test_text_search_empty_results(self):
        """text_search() returns empty list when no matches found."""
        from src.retrieval.atlas_search import text_search

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.limit.return_value = []
            mock_col.return_value.find.return_value = mock_cursor
            results = await text_search("nonexistent query", "doc1")
            assert results == []

    @pytest.mark.asyncio
    async def test_text_search_handles_db_error(self):
        """text_search() returns empty list on DB error (non-fatal)."""
        from src.retrieval.atlas_search import text_search

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_col.return_value.find.side_effect = RuntimeError("DB down")
            results = await text_search("test", "doc1")
            assert results == []

    @pytest.mark.asyncio
    async def test_text_search_with_content_type_filter(self):
        """text_search() applies content type filter when provided."""
        from src.retrieval.atlas_search import text_search

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.limit.return_value = []
            mock_col.return_value.find.return_value = mock_cursor
            await text_search("test", "doc1", content_type_filter="table")
            # Verify the filter includes contentType
            call_args = mock_col.return_value.find.call_args
            query = call_args[0][0]
            assert query.get("contentType") == "table"


class TestEnsureTextIndex:
    """Test text index creation for Community Edition."""

    def test_ensure_text_index_creates_index(self):
        """ensure_text_index() creates a text index on title, summary, keywords."""
        from src.db.indexes import ensure_text_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.create_index.return_value = "nodes_text_search"
            result = ensure_text_index()
            assert "nodes_text_search" in result
            # Verify the index specification
            call_args = mock_col.return_value.create_index.call_args
            index_spec = call_args[0][0]
            assert ("title", "text") in index_spec
            assert ("summary", "text") in index_spec
            assert ("keywords", "text") in index_spec

    def test_ensure_text_index_idempotent(self):
        """ensure_text_index() is idempotent -- doesn't fail if index exists."""
        from src.db.indexes import ensure_text_index
        from pymongo.errors import OperationFailure

        with patch("src.db.indexes.nodes_col") as mock_col:
            # Simulate "index already exists" error
            mock_col.return_value.create_index.side_effect = OperationFailure(
                "Index already exists with a different name"
            )
            # Should not raise
            result = ensure_text_index()
            assert isinstance(result, list)


class TestSearchBackendDetection:
    """Test Atlas Search availability detection."""

    def test_detect_atlas_search_available(self):
        """detect_search_backend() returns 'atlas' when Atlas Search works."""
        from src.retrieval.atlas_search import detect_search_backend

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_col.return_value.list_search_indexes.return_value = [
                {"name": "nodes_fulltext"}
            ]
            backend = detect_search_backend()
            assert backend == "atlas"

    def test_detect_community_edition(self):
        """detect_search_backend() returns 'community' when Atlas Search unavailable."""
        from src.retrieval.atlas_search import detect_search_backend

        with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
            mock_col.return_value.list_search_indexes.side_effect = Exception(
                "not supported"
            )
            backend = detect_search_backend()
            assert backend == "community"


class TestAtlasSearchFallback:
    """Test that atlas_search() falls back to text_search() on Community Edition."""

    @pytest.mark.asyncio
    async def test_atlas_search_uses_text_fallback_on_community(self):
        """When _search_backend is 'community', atlas_search uses text_search."""
        from src.retrieval import atlas_search as atlas_mod

        # Force community mode
        original = atlas_mod._search_backend
        atlas_mod._search_backend = "community"
        try:
            with patch.object(
                atlas_mod, "text_search", new_callable=AsyncMock
            ) as mock_text:
                mock_text.return_value = [
                    RetrievalCandidate(
                        node_id="0001",
                        atlas_score=0.0,
                        tree_score=0.0,
                        final_score=0.0,
                        source="text",
                    )
                ]
                results = await atlas_mod.atlas_search("test", "doc1")
                mock_text.assert_called_once()
                assert len(results) == 1
                assert results[0].source == "text"
        finally:
            atlas_mod._search_backend = original

    @pytest.mark.asyncio
    async def test_atlas_search_uses_aggregation_on_atlas(self):
        """When _search_backend is 'atlas', atlas_search uses $search pipeline."""
        from src.retrieval import atlas_search as atlas_mod

        original = atlas_mod._search_backend
        atlas_mod._search_backend = "atlas"
        try:
            with patch("src.retrieval.atlas_search.nodes_col") as mock_col:
                mock_col.return_value.aggregate.return_value = [
                    {"nodeId": "0001", "score": 5.0}
                ]
                results = await atlas_mod.atlas_search("test", "doc1")
                assert len(results) == 1
                mock_col.return_value.aggregate.assert_called_once()
        finally:
            atlas_mod._search_backend = original
