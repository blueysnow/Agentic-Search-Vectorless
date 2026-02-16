"""Tests for search index creation via createSearchIndex().

Covers:
1. ensure_search_index() creates nodes_fulltext search index
2. ensure_search_index() is idempotent (index already exists)
3. ensure_search_index() handles errors gracefully (mongot not available)
4. ensure_search_index() defines correct field mappings
5. ensure_search_index() checks existing indexes before creating
"""

from unittest.mock import patch

from pymongo.errors import OperationFailure


class TestEnsureSearchIndex:
    """Test search index creation for mongot integration."""

    def test_creates_nodes_fulltext_index(self):
        """ensure_search_index() calls createSearchIndex with correct name and definition."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            # list_search_indexes returns empty (no existing index)
            mock_col.return_value.list_search_indexes.return_value = []
            mock_col.return_value.create_search_index.return_value = "nodes_fulltext"
            result = ensure_search_index()
            assert "nodes_fulltext" in result

            # Verify createSearchIndex was called
            mock_col.return_value.create_search_index.assert_called_once()
            call_args = mock_col.return_value.create_search_index.call_args

            # Verify index model has correct name (pymongo exposes .document dict)
            index_model = call_args[0][0]
            assert index_model.document["name"] == "nodes_fulltext"

    def test_search_index_field_mappings(self):
        """ensure_search_index() defines mappings for title, summary, keywords, documentId, contentType."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.list_search_indexes.return_value = []
            mock_col.return_value.create_search_index.return_value = "nodes_fulltext"
            ensure_search_index()

            call_args = mock_col.return_value.create_search_index.call_args
            index_model = call_args[0][0]
            definition = index_model.document["definition"]

            # Must have mappings
            assert "mappings" in definition
            mappings = definition["mappings"]

            # dynamic: false for explicit field control
            assert mappings.get("dynamic") is False

            # Must define fields for title, summary, keywords, documentId, contentType
            fields = mappings["fields"]
            assert "title" in fields
            assert "summary" in fields
            assert "keywords" in fields
            assert "documentId" in fields
            assert "contentType" in fields

    def test_idempotent_index_exists_via_duplicate_error(self):
        """ensure_search_index() handles 'duplicate index' OperationFailure gracefully."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            # list_search_indexes fails (e.g. mongot just started)
            mock_col.return_value.list_search_indexes.side_effect = Exception(
                "not ready"
            )
            # create_search_index raises duplicate
            mock_col.return_value.create_search_index.side_effect = OperationFailure(
                "Duplicate Index", code=68
            )
            # Should not raise
            result = ensure_search_index()
            assert isinstance(result, list)
            assert "nodes_fulltext" in result

    def test_handles_mongot_not_available(self):
        """ensure_search_index() returns empty list when mongot is not running."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.list_search_indexes.side_effect = Exception(
                "mongot not available"
            )
            mock_col.return_value.create_search_index.side_effect = Exception(
                "mongot not available"
            )
            result = ensure_search_index()
            assert result == []

    def test_skips_create_when_index_already_exists(self):
        """ensure_search_index() checks if index exists before creating."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            # Index already exists
            mock_col.return_value.list_search_indexes.return_value = [
                {"name": "nodes_fulltext"}
            ]
            result = ensure_search_index()
            # Should NOT call create_search_index
            mock_col.return_value.create_search_index.assert_not_called()
            assert "nodes_fulltext" in result
