"""Atlas Search (Lucene) index definitions -- nodes_fulltext + pages_fulltext.

These match plan section 3 exactly. dynamic:false, lucene.english for text,
lucene.keyword / token for exact match fields.

NOTE: Atlas Search index creation is an async server-side operation.
The create commands return immediately but the indexes take time to build.
"""

from __future__ import annotations

from pymongo.operations import SearchIndexModel

from src.db.collections import nodes_col, pages_col

NODES_FULLTEXT_DEFINITION: dict = {
    "mappings": {
        "dynamic": False,
        "fields": {
            "title": {
                "type": "string",
                "analyzer": "lucene.english",
                "searchAnalyzer": "lucene.english",
            },
            "summary": {
                "type": "string",
                "analyzer": "lucene.english",
                "searchAnalyzer": "lucene.english",
            },
            "keywords": [
                {"type": "string", "analyzer": "lucene.keyword"},
                {"type": "token", "normalizer": "lowercase"},
            ],
            "documentId": {"type": "token"},
            "nodeId": {"type": "token"},
            "contentType": {"type": "token"},
            "depth": {"type": "number"},
            "startPage": {"type": "number"},
            "endPage": {"type": "number"},
            "tokenCount": {"type": "number"},
            "isLeaf": {"type": "boolean"},
        },
    }
}

PAGES_FULLTEXT_DEFINITION: dict = {
    "mappings": {
        "dynamic": False,
        "fields": {
            "content": {
                "type": "string",
                "analyzer": "lucene.english",
                "searchAnalyzer": "lucene.english",
            },
            "documentId": {"type": "token"},
            "nodeId": {"type": "token"},
            "pageNumber": {"type": "number"},
        },
    }
}


def ensure_search_indexes() -> list[str]:
    """Create Atlas Search indexes if they do not already exist.

    Returns the names of created indexes. Idempotent -- skips if already present.
    """
    created: list[str] = []

    # -- nodes_fulltext --
    existing_nodes = {idx["name"] for idx in nodes_col().list_search_indexes()}
    if "nodes_fulltext" not in existing_nodes:
        model = SearchIndexModel(
            definition=NODES_FULLTEXT_DEFINITION,
            name="nodes_fulltext",
            type="search",
        )
        nodes_col().create_search_index(model)
        created.append("nodes_fulltext")

    # -- pages_fulltext --
    existing_pages = {idx["name"] for idx in pages_col().list_search_indexes()}
    if "pages_fulltext" not in existing_pages:
        model = SearchIndexModel(
            definition=PAGES_FULLTEXT_DEFINITION,
            name="pages_fulltext",
            type="search",
        )
        pages_col().create_search_index(model)
        created.append("pages_fulltext")

    return created
