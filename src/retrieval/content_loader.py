"""Content loader -- fetch page content for selected nodes (plan section 7.1 step 4).

Loads page content from the pages collection and ancestor context from nodes.
Handles batched MongoDB reads for efficiency.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.db.collections import nodes_col, pages_col

logger = logging.getLogger(__name__)

_LOAD_TIMEOUT_S = 10.0
_MAX_WORKERS = 5


def load_node_content(document_id: str, node_id: str) -> str:
    """Load the concatenated page content for a single node.

    Queries the pages collection for all pages belonging to this node,
    ordered by page number, and concatenates their content.
    """
    pages = list(
        pages_col()
        .find(
            {"documentId": document_id, "nodeId": node_id},
            {"content": 1, "pageNumber": 1, "_id": 0},
        )
        .sort([("pageNumber", 1)])
    )
    if not pages:
        # Fallback: try loading by page range from the node
        node = nodes_col().find_one(
            {"documentId": document_id, "nodeId": node_id},
            {"startPage": 1, "endPage": 1, "_id": 0},
        )
        if node and node.get("startPage") and node.get("endPage"):
            pages = list(
                pages_col()
                .find(
                    {
                        "documentId": document_id,
                        "pageNumber": {
                            "$gte": node["startPage"],
                            "$lte": node["endPage"],
                        },
                    },
                    {"content": 1, "pageNumber": 1, "_id": 0},
                )
                .sort([("pageNumber", 1)])
            )

    return "\n\n".join(p.get("content", "") for p in pages)


def load_node_ancestors(document_id: str, node_id: str) -> list[dict[str, Any]]:
    """Load ancestor nodes for context (titles and summaries).

    Uses the materialized path to find all ancestors from root to parent.
    """
    node = nodes_col().find_one(
        {"documentId": document_id, "nodeId": node_id},
        {"materializedPath": 1, "_id": 0},
    )
    if not node or not node.get("materializedPath"):
        return []

    path = node["materializedPath"]
    ancestor_ids = [aid for aid in path.strip("/").split("/") if aid and aid != node_id]
    if not ancestor_ids:
        return []

    ancestors = list(
        nodes_col()
        .find(
            {"documentId": document_id, "nodeId": {"$in": ancestor_ids}},
            {"nodeId": 1, "title": 1, "summary": 1, "depth": 1, "_id": 0},
        )
        .sort([("depth", 1)])
    )
    return ancestors


def format_ancestor_context(ancestors: list[dict[str, Any]]) -> str:
    """Format ancestor nodes into a readable context string."""
    if not ancestors:
        return "No ancestor context available."
    lines: list[str] = []
    for a in ancestors:
        depth = a.get("depth", 0)
        indent = "  " * depth
        title = a.get("title", "")
        summary = a.get("summary", "")
        line = f"{indent}> {title}"
        if summary:
            line += f": {summary}"
        lines.append(line)
    return "\n".join(lines)


def load_node_cross_references(document_id: str, node_id: str) -> list[dict[str, Any]]:
    """Load cross-references from a node."""
    node = nodes_col().find_one(
        {"documentId": document_id, "nodeId": node_id},
        {"crossReferences": 1, "_id": 0},
    )
    if not node:
        return []
    return node.get("crossReferences", [])


def format_cross_references(cross_refs: list[dict[str, Any]]) -> str:
    """Format cross-references into a readable string."""
    if not cross_refs:
        return "No cross-references."
    lines: list[str] = []
    for ref in cross_refs:
        label = ref.get("label", "")
        ref_type = ref.get("type", "")
        target = ref.get("targetNodeId", "")
        line = f"- {ref_type}: {label}"
        if target:
            line += f" (node {target})"
        lines.append(line)
    return "\n".join(lines)


def _load_single_candidate(document_id: str, nid: str) -> tuple[str, dict[str, Any]]:
    """Load content, ancestors, and cross-refs for a single node.

    Returns (node_id, data_dict). Catches exceptions to prevent one
    node failure from killing the entire batch.
    """
    try:
        content = load_node_content(document_id, nid)
        ancestors = load_node_ancestors(document_id, nid)
        cross_refs = load_node_cross_references(document_id, nid)
        return nid, {
            "content": content,
            "ancestors": ancestors,
            "ancestor_context": format_ancestor_context(ancestors),
            "cross_refs": cross_refs,
            "cross_ref_text": format_cross_references(cross_refs),
        }
    except Exception:
        logger.exception("load_candidate_failed", extra={"node_id": nid})
        return nid, {
            "content": "",
            "ancestors": [],
            "ancestor_context": format_ancestor_context([]),
            "cross_refs": [],
            "cross_ref_text": format_cross_references([]),
        }


def load_candidates_content(
    document_id: str,
    node_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Batch-load content, ancestors, and cross-refs for multiple candidate nodes.

    Uses ThreadPoolExecutor for parallel MongoDB reads with timeout (H3 fix).
    Returns dict mapping node_id to {content, ancestors, ancestor_context,
    cross_refs, cross_ref_text}.
    """
    if not node_ids:
        return {}

    result: dict[str, dict[str, Any]] = {}
    workers = min(_MAX_WORKERS, len(node_ids))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_load_single_candidate, document_id, nid): nid
            for nid in node_ids
        }
        for future in as_completed(futures, timeout=_LOAD_TIMEOUT_S):
            try:
                nid, data = future.result()
                result[nid] = data
            except Exception:
                nid = futures[future]
                logger.exception("load_candidate_future_failed", extra={"node_id": nid})
                result[nid] = {
                    "content": "",
                    "ancestors": [],
                    "ancestor_context": format_ancestor_context([]),
                    "cross_refs": [],
                    "cross_ref_text": format_cross_references([]),
                }

    return result
