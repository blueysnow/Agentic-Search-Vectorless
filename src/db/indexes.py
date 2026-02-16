"""Create all regular MongoDB indexes for the five collections.

Matches plan section 2 exactly, plus a text index as fallback
when search indexes are not yet configured.
"""

from __future__ import annotations

import pymongo
from pymongo.errors import OperationFailure
from pymongo.operations import SearchIndexModel

from src.db.collections import (
    documents_col,
    nodes_col,
    pages_col,
    retrieval_sessions_col,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_indexes() -> list[str]:
    """Create all regular indexes. Returns a list of created index names."""
    created: list[str] = []

    # -- documents --
    docs = documents_col()
    created.append(
        docs.create_index("documentId", unique=True, name="documents_documentId_unique")
    )
    created.append(
        docs.create_index("ingestion.status", name="documents_ingestion_status")
    )
    created.append(
        docs.create_index(
            [("domain", pymongo.ASCENDING), ("createdAt", pymongo.DESCENDING)],
            name="documents_domain_createdAt",
        )
    )

    # -- nodes --
    n = nodes_col()
    created.append(
        n.create_index(
            [("documentId", pymongo.ASCENDING), ("nodeId", pymongo.ASCENDING)],
            unique=True,
            name="nodes_documentId_nodeId_unique",
        )
    )
    created.append(
        n.create_index(
            [
                ("documentId", pymongo.ASCENDING),
                ("parentNodeId", pymongo.ASCENDING),
                ("siblingOrder", pymongo.ASCENDING),
            ],
            name="nodes_parent_sibling",
        )
    )
    created.append(
        n.create_index(
            [
                ("documentId", pymongo.ASCENDING),
                ("materializedPath", pymongo.ASCENDING),
            ],
            name="nodes_materializedPath",
        )
    )
    created.append(
        n.create_index(
            [("documentId", pymongo.ASCENDING), ("depth", pymongo.ASCENDING)],
            name="nodes_depth",
        )
    )
    created.append(
        n.create_index(
            [("documentId", pymongo.ASCENDING), ("isLeaf", pymongo.ASCENDING)],
            name="nodes_isLeaf",
        )
    )
    created.append(
        n.create_index("crossReferences.targetNodeId", name="nodes_crossRef_target")
    )
    created.append(
        n.create_index(
            [("documentId", pymongo.ASCENDING), ("contentType", pymongo.ASCENDING)],
            name="nodes_contentType",
        )
    )

    # -- pages --
    p = pages_col()
    created.append(
        p.create_index(
            [("documentId", pymongo.ASCENDING), ("pageNumber", pymongo.ASCENDING)],
            unique=True,
            name="pages_documentId_pageNumber_unique",
        )
    )
    created.append(
        p.create_index(
            [("documentId", pymongo.ASCENDING), ("nodeId", pymongo.ASCENDING)],
            name="pages_documentId_nodeId",
        )
    )
    created.append(p.create_index("nodeId", name="pages_nodeId"))

    # -- retrieval_sessions --
    rs = retrieval_sessions_col()
    created.append(
        rs.create_index("sessionId", unique=True, name="sessions_sessionId_unique")
    )
    created.append(
        rs.create_index(
            [("userId", pymongo.ASCENDING), ("createdAt", pymongo.DESCENDING)],
            name="sessions_userId_createdAt",
        )
    )
    created.append(
        rs.create_index(
            [("documentId", pymongo.ASCENDING), ("createdAt", pymongo.DESCENDING)],
            name="sessions_documentId_createdAt",
        )
    )

    return created


def ensure_text_index() -> list[str]:
    """Create a MongoDB text index on the nodes collection as fallback.

    This enables $text queries as an alternative to Atlas Search ($search) when
    search indexes are not yet configured. The text index covers title, summary,
    and keywords fields.

    Returns a list of created index names. Idempotent -- silently handles
    'index already exists' errors.
    """
    created: list[str] = []
    n = nodes_col()
    try:
        name = n.create_index(
            [
                ("title", "text"),
                ("summary", "text"),
                ("keywords", "text"),
            ],
            name="nodes_text_search",
            weights={"title": 10, "summary": 5, "keywords": 3},
            default_language="english",
        )
        created.append(name)
        logger.info("text_index_created", index_name=name)
    except OperationFailure as exc:
        # Index already exists or conflicting index -- not fatal
        logger.info("text_index_already_exists", error=str(exc))
    return created


def ensure_search_index() -> list[str]:
    """Create the nodes_fulltext search index for Atlas Search / mongot.

    Uses pymongo's create_search_index() to programmatically create a search
    index with explicit field mappings for title, summary, keywords, documentId,
    and contentType. This enables $search aggregation queries.

    The function is idempotent:
    - Checks if index already exists via list_search_indexes()
    - Handles 'duplicate index' errors gracefully
    - Returns empty list if mongot is not available (non-fatal)

    Returns:
        List of created/existing search index names.
    """
    created: list[str] = []
    n = nodes_col()
    index_name = "nodes_fulltext"

    try:
        # Check if index already exists
        existing = {idx["name"] for idx in n.list_search_indexes()}
        if index_name in existing:
            logger.info("search_index_already_exists", index_name=index_name)
            return [index_name]
    except Exception:
        # list_search_indexes not supported (no mongot) -- try creating anyway
        logger.debug("list_search_indexes_unavailable", exc_info=True)

    try:
        model = SearchIndexModel(
            name=index_name,
            definition={
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "title": [{"type": "string", "analyzer": "lucene.standard"}],
                        "summary": [{"type": "string", "analyzer": "lucene.standard"}],
                        "keywords": [{"type": "string", "analyzer": "lucene.standard"}],
                        "documentId": [
                            {"type": "string", "analyzer": "lucene.keyword"}
                        ],
                        "contentType": [
                            {"type": "string", "analyzer": "lucene.keyword"}
                        ],
                    },
                }
            },
        )
        result = n.create_search_index(model)
        created.append(result)
        logger.info("search_index_created", index_name=result)
    except OperationFailure as exc:
        if exc.code == 68 or "Duplicate" in str(exc):
            logger.info("search_index_duplicate", index_name=index_name, error=str(exc))
            created.append(index_name)
        else:
            logger.warning(
                "search_index_creation_failed", error=str(exc), exc_info=True
            )
    except Exception:
        # mongot not available or search indexes not supported -- non-fatal
        logger.info("search_index_creation_skipped", exc_info=True)

    return created
