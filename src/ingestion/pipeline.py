"""Ingestion pipeline orchestrator (ref: page_index.py:950-1100).

Three-mode orchestrator with fallback, full tree parsing, and MongoDB persistence.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

from src.config import get_settings
from src.db.collections import documents_col, nodes_col, pages_col
from src.ingestion.enrichment.content_classifier import classify_content_type
from src.ingestion.enrichment.cross_ref_detector import detect_cross_references
from src.ingestion.enrichment.summarizer import (
    generate_doc_description,
    generate_summaries_for_structure,
)
from src.ingestion.tree_builder.splitter import process_large_node_recursively
from src.ingestion.tree_builder.toc_detector import check_toc
from src.ingestion.tree_builder.tree_generator import (
    process_no_toc,
    process_toc_no_page_numbers,
    process_toc_with_page_numbers,
)
from src.ingestion.tree_builder.tree_utils import (
    add_node_text,
    add_preface_if_needed,
    post_processing,
    structure_to_list,
    write_node_id,
)
from src.ingestion.tree_builder.verifier import (
    _check_title_appearance_in_start_concurrent,
    fix_incorrect_toc,
    verify_toc,
)
from src.llm.provider import LLMProvider
from src.models.document import Document, Ingestion
from src.models.node import Node
from src.models.page import Page
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _validate_and_truncate(
    toc_items: list[dict],
    page_list_length: int,
    start_index: int = 1,
) -> list[dict]:
    """Remove items whose physical_index exceeds the document length."""
    max_allowed = page_list_length + start_index - 1
    for item in toc_items:
        if (
            item.get("physical_index") is not None
            and item["physical_index"] > max_allowed
        ):
            item["physical_index"] = None
    return toc_items


async def meta_processor(
    page_list: list[tuple],
    llm_provider: LLMProvider,
    mode: str = "process_no_toc",
    toc_content: str | None = None,
    toc_page_list: list[int] | None = None,
    start_index: int = 1,
) -> list[dict]:
    """3-mode orchestrator with fallback (ref: page_index.py:950-989).

    Modes:
      - process_toc_with_page_numbers (Mode A)
      - process_toc_no_page_numbers (Mode B)
      - process_no_toc (Mode C)

    Falls back: A -> B -> C on low accuracy.
    """
    settings = get_settings()

    if mode == "process_toc_with_page_numbers":
        toc_items = process_toc_with_page_numbers(
            toc_content,
            None,
            page_list,
            llm_provider,
            toc_page_list=toc_page_list,
            toc_check_pages=settings.toc_check_pages,
        )
    elif mode == "process_toc_no_page_numbers":
        toc_items = process_toc_no_page_numbers(
            toc_content, None, page_list, llm_provider
        )
    else:
        toc_items = process_no_toc(page_list, llm_provider, start_index=start_index)

    # Filter None physical_index
    toc_items = [item for item in toc_items if item.get("physical_index") is not None]
    if not toc_items:
        logger.warning("meta_processor_empty_after_filter", mode=mode)
        if mode != "process_no_toc":
            return await meta_processor(
                page_list,
                llm_provider,
                mode="process_no_toc",
                start_index=start_index,
            )
        raise RuntimeError("Tree building failed: no valid toc items after filtering")
    toc_items = _validate_and_truncate(toc_items, len(page_list), start_index)

    # Verify
    accuracy, incorrect = await verify_toc(toc_items, page_list, llm_provider)
    logger.info(
        "meta_processor_verify", mode=mode, accuracy=accuracy, incorrect=len(incorrect)
    )

    if accuracy == 1.0 and not incorrect:
        return toc_items

    if accuracy > 0.6 and incorrect:
        toc_items = await fix_incorrect_toc(
            toc_items, page_list, llm_provider, max_rounds=3
        )
        return toc_items

    # Fallback to simpler mode
    if mode == "process_toc_with_page_numbers":
        return await meta_processor(
            page_list,
            llm_provider,
            mode="process_toc_no_page_numbers",
            toc_content=toc_content,
            toc_page_list=toc_page_list,
            start_index=start_index,
        )
    elif mode == "process_toc_no_page_numbers":
        return await meta_processor(
            page_list,
            llm_provider,
            mode="process_no_toc",
            start_index=start_index,
        )
    else:
        raise RuntimeError("Tree building failed: all modes exhausted")


async def tree_parser(
    page_list: list[tuple],
    llm_provider: LLMProvider,
) -> list[dict]:
    """Full tree parsing pipeline (ref: page_index.py:1021-1055).

    1. Detect ToC
    2. Run meta_processor with appropriate mode
    3. Add preface if needed
    4. Check title start positions
    5. Post-process to tree
    6. Split large nodes
    """
    settings = get_settings()

    check_result = check_toc(
        page_list, llm_provider, max_pages=settings.toc_check_pages
    )
    logger.info("toc_check_result", has_toc=bool(check_result.get("toc_content")))

    if (
        check_result.get("toc_content")
        and check_result["toc_content"].strip()
        and check_result["page_index_given_in_toc"] == "yes"
    ):
        mode = "process_toc_with_page_numbers"
    elif check_result.get("toc_content") and check_result["toc_content"].strip():
        mode = "process_toc_no_page_numbers"
    else:
        mode = "process_no_toc"

    toc_items = await meta_processor(
        page_list,
        llm_provider,
        mode=mode,
        toc_content=check_result.get("toc_content"),
        toc_page_list=check_result.get("toc_page_list"),
        start_index=1,
    )

    toc_items = add_preface_if_needed(toc_items)
    toc_items = await _check_title_appearance_in_start_concurrent(
        toc_items, page_list, llm_provider
    )

    # Filter and build tree
    valid_items = [item for item in toc_items if item.get("physical_index") is not None]
    tree = post_processing(valid_items, len(page_list))

    # Split large nodes
    tasks = [
        process_large_node_recursively(
            node,
            page_list,
            llm_provider,
            max_pages=settings.max_pages_per_node,
            max_tokens=settings.max_tokens_per_node,
        )
        for node in tree
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                "split_node_failed", node_title=tree[i].get("title"), error=str(result)
            )

    return tree


async def page_index_main(
    page_list: list[tuple],
    llm_provider: LLMProvider,
    doc_name: str = "Untitled",
) -> dict:
    """Main entry point (ref: page_index.py:1058-1100).

    Returns dict with doc_name, description, structure.
    """
    settings = get_settings()

    try:
        structure = await tree_parser(page_list, llm_provider)
    except Exception:
        logger.exception("tree_parser_failed", doc_name=doc_name)
        raise

    # Assign node IDs
    write_node_id(structure)

    # Add text to nodes
    add_node_text(structure, page_list)

    # Generate summaries if configured
    description = ""
    if settings.generate_summaries:
        try:
            await generate_summaries_for_structure(structure, llm_provider)
            description = generate_doc_description(structure, llm_provider)
        except Exception:
            logger.exception("summarization_failed", doc_name=doc_name)

    return {
        "doc_name": doc_name,
        "doc_description": description,
        "structure": structure,
    }


# --- MongoDB Persistence ---


def save_document(
    document_id: str,
    name: str,
    doc_type: str,
    total_pages: int,
    total_nodes: int,
    total_tokens: int,
    description: str = "",
    model: str = "",
) -> None:
    """Write document record to MongoDB (status: processing)."""
    doc = Document(
        document_id=document_id,
        name=name,
        type=doc_type,
        description=description,
        total_pages=total_pages,
        total_nodes=total_nodes,
        total_tokens=total_tokens,
        ingestion=Ingestion(
            status="processing",
            model=model,
            started_at=datetime.now(UTC),
        ),
    )
    documents_col().insert_one(doc.to_mongo())


def _collect_nodes(
    document_id: str,
    structure: dict | list,
    parent_node_id: str | None = None,
    materialized_path: str = "",
    depth: int = 0,
) -> list[dict]:
    """Recursively collect node documents for batch insert."""
    nodes_list = structure if isinstance(structure, list) else [structure]
    collected: list[dict] = []

    for sibling_order, node_dict in enumerate(nodes_list):
        node_id = node_dict.get("node_id", "")
        path = f"{materialized_path}/{node_id}" if materialized_path else f"/{node_id}"
        children = node_dict.get("nodes", [])
        child_ids = [c.get("node_id", "") for c in children] if children else []

        title = node_dict.get("title", "")
        content_type = classify_content_type(title, node_dict.get("text", ""))
        cross_refs = detect_cross_references(node_dict.get("text", ""))

        node = Node(
            node_id=node_id,
            document_id=document_id,
            parent_node_id=parent_node_id,
            materialized_path=path,
            child_node_ids=child_ids,
            depth=depth,
            sibling_order=sibling_order,
            title=title,
            summary=node_dict.get("summary", ""),
            start_page=node_dict.get("start_index", 0),
            end_page=node_dict.get("end_index", 0),
            token_count=node_dict.get("token_count", 0),
            keywords=node_dict.get("keywords", []),
            content_type=content_type,
            cross_references=[
                {"targetNodeId": "", "label": r["label"], "type": r["type"]}
                for r in cross_refs
            ],
            is_leaf=not bool(children),
        )
        collected.append(node.to_mongo())

        if children:
            collected.extend(
                _collect_nodes(
                    document_id,
                    children,
                    parent_node_id=node_id,
                    materialized_path=path,
                    depth=depth + 1,
                )
            )

    return collected


def save_nodes(
    document_id: str,
    structure: dict | list,
    parent_node_id: str | None = None,
    materialized_path: str = "",
    depth: int = 0,
) -> int:
    """Recursively save nodes to MongoDB via batch insert. Returns count of nodes saved."""
    docs = _collect_nodes(
        document_id, structure, parent_node_id, materialized_path, depth
    )
    if docs:
        nodes_col().insert_many(docs)
    return len(docs)


def save_pages(
    document_id: str,
    page_list: list[tuple],
    structure: dict | list,
) -> int:
    """Save page content to MongoDB. Returns count of pages saved.

    Maps each page to its owning leaf node based on start_index/end_index.
    """
    # Build page -> node_id mapping from structure
    all_nodes = structure_to_list(structure)
    page_to_node: dict[int, str] = {}
    for node in all_nodes:
        start = node.get("start_index")
        end = node.get("end_index")
        nid = node.get("node_id", "")
        if start is not None and end is not None:
            for p in range(start, end + 1):
                if p not in page_to_node:
                    page_to_node[p] = nid

    pages_to_insert: list[dict] = []
    for i, (text, tokens) in enumerate(page_list):
        page_num = i + 1
        content_hash = f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"
        node_id = page_to_node.get(page_num, "")

        page = Page(
            document_id=document_id,
            page_number=page_num,
            node_id=node_id,
            content=text,
            content_hash=content_hash,
            token_count=tokens,
        )
        pages_to_insert.append(page.to_mongo())

    if pages_to_insert:
        pages_col().insert_many(pages_to_insert)

    return len(pages_to_insert)


def update_document_status(
    document_id: str, status: str, errors: list[str] | None = None
) -> None:
    """Update document ingestion status."""
    update: dict[str, Any] = {
        "$set": {
            "ingestion.status": status,
            "updatedAt": datetime.now(UTC),
        }
    }
    if status == "completed":
        update["$set"]["ingestion.completedAt"] = datetime.now(UTC)
    if errors:
        update["$set"]["ingestion.errors"] = errors
    documents_col().update_one({"documentId": document_id}, update)
