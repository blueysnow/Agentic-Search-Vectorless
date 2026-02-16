"""Atlas Search query builder -- generates $search aggregation pipelines (plan sections 5.3, 8).

Builds compound queries with boosted title/summary, keyword filtering, fuzzy matching,
and document scoping. Returns scored RetrievalCandidate objects.

Includes a $text fallback for when search indexes are not yet configured.
At startup, detect_search_backend() determines whether Atlas Search indexes exist.
If not, atlas_search() transparently delegates to text_search() using standard $text indexes.
"""

from __future__ import annotations

from typing import Any

from src.db.collections import nodes_col
from src.models.retrieval import RetrievalCandidate
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default boost weights matching plan section 5.3
TITLE_BOOST = 10.0
SUMMARY_BOOST = 5.0
KEYWORD_BOOST = 3.0

# Phrase boost for exact multi-word matches (higher than individual word boosts)
PHRASE_BOOST = 15.0

# Shingle (bigram) phrase boost for overlapping word pairs
SHINGLE_BOOST = 7.0

# Search backend: "atlas" (Atlas Search $search) or "text" ($text fallback).
# Set at startup by detect_search_backend() or manually for testing.
_search_backend: str = "atlas"


def _generate_shingles(query: str) -> list[str]:
    """Break a multi-word query into overlapping bigrams (shingles).

    Only generates shingles when query has 3+ words. Two-word queries are
    already a single phrase, and single-word queries have no pairs.

    Examples:
        "revenue growth in Germany Q3" -> ["revenue growth", "growth in", "in Germany", "Germany Q3"]
        "revenue growth" -> []
        "revenue" -> []
    """
    words = query.split()
    if len(words) < 3:
        return []
    return [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]


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

    # Phrase clauses for exact multi-word matches (higher boost than individual words)
    words = query.split()
    if len(words) >= 2:
        should_clauses.append(
            {
                "phrase": {
                    "query": query,
                    "path": "title",
                    "score": {"boost": {"value": PHRASE_BOOST}},
                }
            }
        )
        should_clauses.append(
            {
                "phrase": {
                    "query": query,
                    "path": "summary",
                    "score": {"boost": {"value": PHRASE_BOOST}},
                }
            }
        )

    # Shingle (bigram) phrase clauses for overlapping word pairs
    shingles = _generate_shingles(query)
    for shingle in shingles:
        should_clauses.append(
            {
                "phrase": {
                    "query": shingle,
                    "path": "title",
                    "score": {"boost": {"value": SHINGLE_BOOST}},
                }
            }
        )
        should_clauses.append(
            {
                "phrase": {
                    "query": shingle,
                    "path": "summary",
                    "score": {"boost": {"value": SHINGLE_BOOST}},
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


def detect_search_backend() -> str:
    """Detect whether Atlas Search indexes are configured.

    Tries to list search indexes on the nodes collection. If that succeeds and
    'nodes_fulltext' exists, Atlas Search is used. Otherwise falls back to
    standard MongoDB $text search.

    Returns:
        "atlas" or "text"
    """
    try:
        indexes = list(nodes_col().list_search_indexes())
        for idx in indexes:
            if idx["name"] == "nodes_fulltext":
                status = idx.get("status", "READY")
                if status in ("READY", "STEADY"):
                    return "atlas"
                logger.info(
                    "atlas_search_index_not_ready",
                    backend="text",
                    status=status,
                )
                return "text"
        logger.info("atlas_search_index_not_found", backend="text")
        return "text"
    except Exception:
        logger.info("atlas_search_not_available", backend="text", exc_info=True)
        return "text"


def init_search_backend() -> None:
    """Detect and set the module-level _search_backend at startup."""
    global _search_backend
    _search_backend = detect_search_backend()
    logger.info("search_backend_initialized", backend=_search_backend)


async def text_search(
    query: str,
    document_id: str,
    *,
    limit: int = 5,
    content_type_filter: str | None = None,
) -> list[RetrievalCandidate]:
    """Execute a standard MongoDB $text search as fallback when search indexes are not configured.

    Uses the text index on {title, summary, keywords} created by ensure_text_index().
    Returns RetrievalCandidate objects with the same interface as atlas_search().
    """
    filter_query: dict[str, Any] = {
        "$text": {"$search": query},
        "documentId": document_id,
    }
    if content_type_filter:
        filter_query["contentType"] = content_type_filter

    projection: dict[str, Any] = {
        "nodeId": 1,
        "title": 1,
        "summary": 1,
        "depth": 1,
        "startPage": 1,
        "endPage": 1,
        "contentType": 1,
        "keywords": 1,
        "isLeaf": 1,
        "score": {"$meta": "textScore"},
    }

    try:
        results = list(
            nodes_col()
            .find(filter_query, projection)
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
    except Exception:
        logger.warning(
            "text_search_error",
            query=query,
            document_id=document_id,
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
                source="text",
            )
        )
    return candidates


async def atlas_search(
    query: str,
    document_id: str,
    *,
    limit: int = 5,
    use_fuzzy: bool = False,
    content_type_filter: str | None = None,
) -> list[RetrievalCandidate]:
    """Execute search and return scored candidates.

    Uses Atlas Search ($search) when available, falls back to $text search
    when search indexes are not configured. Returns empty list on failure
    (non-fatal for dual retrieval).
    """
    # $text fallback: use when search indexes are not configured
    if _search_backend == "text":
        if use_fuzzy:
            logger.debug("fuzzy_not_supported_text_backend", query=query)
        return await text_search(
            query,
            document_id,
            limit=limit,
            content_type_filter=content_type_filter,
        )

    # Atlas Search path
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
            query=query,
            document_id=document_id,
            error_type="infrastructure",
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
