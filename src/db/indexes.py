"""Create all regular MongoDB indexes for the five collections.

Matches plan section 2 exactly (13 indexes).
"""

from __future__ import annotations

import pymongo

from src.db.collections import (
    documents_col,
    nodes_col,
    pages_col,
    retrieval_sessions_col,
)


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
