"""Create all regular MongoDB indexes for the five collections.

Matches plan section 2 exactly, plus a text index as fallback
when search indexes are not yet configured.
"""

from __future__ import annotations

import pymongo
from pymongo.errors import OperationFailure

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
