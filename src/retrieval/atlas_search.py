"""Atlas Search query builder -- generates $search aggregation pipelines (plan sections 5.3, 8).

Builds compound queries with boosted title/summary, keyword filtering, fuzzy matching,
and document scoping. Returns scored RetrievalCandidate objects.
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.collections import nodes_col
from src.models.retrieval import RetrievalCandidate

logger = logging.getLogger(__name__)

# Default boost weights matching plan section 5.3
TITLE_BOOST = 10.0
SUMMARY_BOOST = 5.0
KEYWORD_BOOST = 3.0


def build_search_pipeline(
    query: str,
    document_id: str,
    *,
    limit: int = 10,
    fuzzy_max_edits: int = 1,
    fuzzy_prefix_length: int = 3,
    content_type_filter: str | None = None,
    use_fuzzy: bool = False,
) -> list[dict[str, Any]]:
    """Build an Atlas Search aggregation pipeline for node search.

    Args:
        query: The user's search query text.
        document_id: Scope search to this document.
        limit: Max results to return.
        fuzzy_max_edits: Max edit distance for fuzzy matching.
        fuzzy_prefix_length: Min prefix before fuzzy kicks in.
        content_type_filter: Optional filter by content type (section, table, etc).
        use_fuzzy: Enable fuzzy matching for typo tolerance.
    """
    should_clauses: list[dict[str, Any]] = []

    # Title search (highest boost)
    title_clause: dict[str, Any] = {
        "text": {
            "query": query,
            "path": "title",
            "score": {"boost": {"value": TITLE_BOOST}},
        }
    }
    if use_fuzzy:
        title_clause["text"]["fuzzy"] = {
            "maxEdits": fuzzy_max_edits,
            "prefixLength": fuzzy_prefix_length,
        }
    should_clauses.append(title_clause)

    # Summary search (medium boost)
    summary_clause: dict[str, Any] = {
        "text": {
            "query": query,
            "path": "summary",
            "score": {"boost": {"value": SUMMARY_BOOST}},
        }
    }
    if use_fuzzy:
        summary_clause["text"]["fuzzy"] = {
            "maxEdits": fuzzy_max_edits,
            "prefixLength": fuzzy_prefix_length,
        }
    should_clauses.append(summary_clause)

    # Keyword search (lower boost)
    should_clauses.append(
        {
            "text": {
                "query": query,
                "path": "keywords",
                "score": {"boost": {"value": KEYWORD_BOOST}},
            }
        }
    )

    must_clauses: list[dict[str, Any]] = [
        {"equals": {"path": "documentId", "value": document_id}}
    ]

    filter_clauses: list[dict[str, Any]] = []
    if content_type_filter:
        filter_clauses.append(
            {"equals": {"path": "contentType", "value": content_type_filter}}
        )

    compound: dict[str, Any] = {
        "must": must_clauses,
        "should": should_clauses,
        "minimumShouldMatch": 1,
    }
    if filter_clauses:
        compound["filter"] = filter_clauses

    pipeline: list[dict[str, Any]] = [
        {"$search": {"index": "nodes_fulltext", "compound": compound}},
        {"$limit": limit},
        {
            "$project": {
                "nodeId": 1,
                "title": 1,
                "summary": 1,
                "depth": 1,
                "startPage": 1,
                "endPage": 1,
                "contentType": 1,
                "keywords": 1,
                "isLeaf": 1,
                "score": {"$meta": "searchScore"},
            }
        },
    ]
    return pipeline


async def atlas_search(
    query: str,
    document_id: str,
    *,
    limit: int = 5,
    use_fuzzy: bool = False,
    content_type_filter: str | None = None,
) -> list[RetrievalCandidate]:
    """Execute Atlas Search and return scored candidates.

    Runs the aggregation pipeline against the nodes collection.
    Returns empty list on failure (non-fatal for dual retrieval).
    """
    pipeline = build_search_pipeline(
        query,
        document_id,
        limit=limit,
        use_fuzzy=use_fuzzy,
        content_type_filter=content_type_filter,
    )

    try:
        results = list(nodes_col().aggregate(pipeline))
    except Exception:
        logger.warning(
            "atlas_search_error",
            extra={
                "query": query,
                "document_id": document_id,
                "error_type": "infrastructure",
            },
            exc_info=True,
        )
        return []

    candidates: list[RetrievalCandidate] = []
    for doc in results:
        candidates.append(
            RetrievalCandidate(
                node_id=doc.get("nodeId", ""),
                atlas_score=float(doc.get("score", 0.0)),
                tree_score=0.0,
                final_score=0.0,
                source="atlas",
            )
        )
    return candidates
