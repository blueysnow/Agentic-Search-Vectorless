"""Large node splitting: recursively split nodes that exceed size limits (ref: page_index.py:992-1019)."""

from __future__ import annotations

import asyncio

from src.llm.provider import LLMProvider
from src.utils.logger import get_logger

from .tree_generator import process_no_toc
from .tree_utils import post_processing
from .verifier import _check_title_appearance_in_start_concurrent

logger = get_logger(__name__)


async def process_large_node_recursively(
    node: dict,
    page_list: list[tuple],
    llm_provider: LLMProvider,
    max_pages: int = 10,
    max_tokens: int = 20000,
) -> dict:
    """Recursively split nodes exceeding page/token limits (ref: page_index.py:992-1019).

    If a node spans too many pages or tokens, run Mode C (process_no_toc) on its
    content to generate sub-structure, then recurse into children.
    """
    start_idx = node.get("start_index")
    end_idx = node.get("end_index")

    if start_idx is None or end_idx is None:
        return node

    node_page_list = page_list[start_idx - 1 : end_idx]
    page_span = end_idx - start_idx
    token_num = sum(p[1] for p in node_page_list)

    if page_span > max_pages and token_num >= max_tokens:
        logger.info(
            "splitting_large_node",
            title=node.get("title"),
            start=start_idx,
            end=end_idx,
            tokens=token_num,
        )

        sub_toc = process_no_toc(node_page_list, llm_provider, start_index=start_idx)
        sub_toc = await _check_title_appearance_in_start_concurrent(
            sub_toc, page_list, llm_provider
        )

        # Filter items with valid physical_index
        valid_items = [
            item for item in sub_toc if item.get("physical_index") is not None
        ]

        if (
            valid_items
            and node.get("title", "").strip() == valid_items[0].get("title", "").strip()
        ):
            # First sub-node matches parent title, skip it
            node["nodes"] = post_processing(valid_items[1:], end_idx)
            if len(valid_items) > 1:
                node["end_index"] = valid_items[1].get("start_index", end_idx)
        else:
            node["nodes"] = post_processing(valid_items, end_idx)
            if valid_items:
                node["end_index"] = valid_items[0].get("start_index", end_idx)

    # Recurse into children
    if "nodes" in node and node["nodes"]:
        tasks = [
            process_large_node_recursively(
                child, page_list, llm_provider, max_pages, max_tokens
            )
            for child in node["nodes"]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "split_child_failed",
                    title=node["nodes"][j].get("title"),
                    error=str(result),
                )

    return node
