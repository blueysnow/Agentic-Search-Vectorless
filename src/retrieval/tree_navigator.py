"""Tree navigator -- LLM reads ToC and selects branches top-down (plan section 7.2).

The LLM navigates the document tree from root to leaf:
1. Load root-level nodes (depth=0)
2. LLM selects 1-3 most relevant branches
3. Load children of selected branches
4. LLM narrows further
5. Repeat until leaf or max_depth reached
"""

from __future__ import annotations

import logging
from typing import Any

from src.db.collections import nodes_col
from src.llm.prompts.tree_navigation import (
    TREE_NAVIGATION_PROMPT,
    TREE_NAVIGATION_WITH_CONTEXT_PROMPT,
)
from src.llm.provider import LLMProvider, Message
from src.models.retrieval import RetrievalCandidate
from src.utils.json_utils import extract_json

logger = logging.getLogger(__name__)

MAX_NAVIGATION_DEPTH = 5
MAX_SELECTIONS_PER_LEVEL = 3


def _format_sections(nodes: list[dict[str, Any]]) -> str:
    """Format node list into a readable section listing for the LLM."""
    lines: list[str] = []
    for n in nodes:
        node_id = n.get("nodeId", n.get("node_id", ""))
        title = n.get("title", "Untitled")
        summary = n.get("summary", "")
        start_page = n.get("startPage", n.get("start_page", 0))
        end_page = n.get("endPage", n.get("end_page", 0))
        depth = n.get("depth", 0)
        indent = "  " * depth
        line = f"{indent}- [{node_id}] {title} (pages {start_page}-{end_page})"
        if summary:
            line += f"\n{indent}  Summary: {summary}"
        lines.append(line)
    return "\n".join(lines)


def _get_children(document_id: str, parent_node_id: str) -> list[dict[str, Any]]:
    """Load children of a node from MongoDB, ordered by sibling_order."""
    return list(
        nodes_col()
        .find(
            {"documentId": document_id, "parentNodeId": parent_node_id},
            {
                "nodeId": 1,
                "title": 1,
                "summary": 1,
                "startPage": 1,
                "endPage": 1,
                "depth": 1,
                "isLeaf": 1,
                "childNodeIds": 1,
                "_id": 0,
            },
        )
        .sort([("siblingOrder", 1)])
    )


def _get_root_nodes(document_id: str) -> list[dict[str, Any]]:
    """Load root-level nodes (depth=0) from MongoDB."""
    return list(
        nodes_col()
        .find(
            {"documentId": document_id, "depth": 0},
            {
                "nodeId": 1,
                "title": 1,
                "summary": 1,
                "startPage": 1,
                "endPage": 1,
                "depth": 1,
                "isLeaf": 1,
                "childNodeIds": 1,
                "_id": 0,
            },
        )
        .sort([("siblingOrder", 1)])
    )


async def _navigate_level(
    query: str,
    document_name: str,
    document_description: str,
    nodes: list[dict[str, Any]],
    llm_provider: LLMProvider,
    visited_context: str = "",
) -> list[str]:
    """Ask the LLM to select relevant nodes from a list.

    Returns list of selected node IDs.
    """
    if not nodes:
        return []

    sections_text = _format_sections(nodes)

    if visited_context:
        prompt = TREE_NAVIGATION_WITH_CONTEXT_PROMPT.format(
            document_name=document_name,
            document_description=document_description,
            visited_context=visited_context,
            sections=sections_text,
            query=query,
        )
    else:
        prompt = TREE_NAVIGATION_PROMPT.format(
            document_name=document_name,
            document_description=document_description,
            sections=sections_text,
            query=query,
        )

    try:
        response = await llm_provider.chat_async(
            [Message(role="user", content=prompt)],
            temperature=0.0,
        )
    except Exception:
        logger.exception("tree_nav_llm_failed")
        return []

    parsed = extract_json(response.content)
    if parsed is None or not isinstance(parsed, dict):
        logger.warning("tree_nav_parse_failed", extra={"raw": response.content})
        return []

    selected = parsed.get("selectedNodeIds", [])
    if not isinstance(selected, list):
        return []

    # Validate against available node IDs
    available_ids = {n.get("nodeId", n.get("node_id", "")) for n in nodes}
    valid_selected = [nid for nid in selected if nid in available_ids]
    return valid_selected[:MAX_SELECTIONS_PER_LEVEL]


async def tree_navigate(
    query: str,
    document_id: str,
    document_name: str,
    document_description: str,
    llm_provider: LLMProvider,
    *,
    max_depth: int = MAX_NAVIGATION_DEPTH,
) -> tuple[list[RetrievalCandidate], list[str]]:
    """Navigate the document tree top-down, returning candidates and the navigation path.

    Returns:
        tuple of (candidates, navigation_path) where navigation_path is the list
        of node IDs visited in order.
    """
    navigation_path: list[str] = []
    candidates: list[RetrievalCandidate] = []
    visited_titles: list[str] = []

    # Start at root
    current_nodes = _get_root_nodes(document_id)
    if not current_nodes:
        logger.warning("tree_nav_no_root_nodes", extra={"document_id": document_id})
        return [], []

    for depth_level in range(max_depth):
        if not current_nodes:
            break

        visited_context = ""
        if visited_titles:
            visited_context = "\n".join(f"- {t}" for t in visited_titles)

        selected_ids = await _navigate_level(
            query=query,
            document_name=document_name,
            document_description=document_description,
            nodes=current_nodes,
            llm_provider=llm_provider,
            visited_context=visited_context,
        )

        if not selected_ids:
            # LLM failed or returned nothing -- return partial results from
            # successful depth levels rather than discarding everything (H1 fix)
            logger.warning(
                "tree_nav_level_empty",
                extra={"depth": depth_level, "candidates_so_far": len(candidates)},
            )
            break

        navigation_path.extend(selected_ids)

        # Score based on depth (deeper = more specific = higher score)
        depth_score = (depth_level + 1) / max_depth
        for nid in selected_ids:
            node_data = next(
                (
                    n
                    for n in current_nodes
                    if n.get("nodeId", n.get("node_id", "")) == nid
                ),
                None,
            )
            if node_data:
                visited_titles.append(f"[{nid}] {node_data.get('title', '')}")
                candidates.append(
                    RetrievalCandidate(
                        node_id=nid,
                        atlas_score=0.0,
                        tree_score=depth_score,
                        final_score=0.0,
                        source="tree",
                    )
                )

        # Check if all selected nodes are leaves
        selected_nodes = [
            n
            for n in current_nodes
            if n.get("nodeId", n.get("node_id", "")) in selected_ids
        ]
        all_leaves = all(
            n.get("isLeaf", n.get("is_leaf", False))
            or not n.get("childNodeIds", n.get("child_node_ids", []))
            for n in selected_nodes
        )
        if all_leaves:
            break

        # Load children for next level
        next_level_nodes: list[dict[str, Any]] = []
        for nid in selected_ids:
            children = _get_children(document_id, nid)
            next_level_nodes.extend(children)

        current_nodes = next_level_nodes

    return candidates, navigation_path
