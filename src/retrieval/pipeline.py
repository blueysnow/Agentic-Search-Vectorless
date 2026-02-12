"""Retrieval pipeline orchestrator -- end-to-end async retrieval (plan section 7.1).

Orchestrates: query analysis -> dual retrieval -> merge -> content loading -> reasoning loop.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from src.config import get_settings
from src.db.collections import documents_col
from src.llm.provider import LLMProvider
from src.models.retrieval import ReasonerResponse, RetrievalCandidate
from src.retrieval.atlas_search import atlas_search
from src.retrieval.content_loader import (
    load_candidates_content,
    load_node_content,
)
from src.retrieval.merger import merge_results
from src.retrieval.query_analyzer import QueryAnalysis, analyze_query
from src.retrieval.reasoner import (
    check_sufficiency,
    check_sufficiency_multi_turn,
)
from src.retrieval.session_manager import (
    add_turn,
    create_session,
    get_conversation_history,
    get_session,
)
from src.retrieval.tree_navigator import tree_navigate

logger = logging.getLogger(__name__)


class RetrievalResult:
    """Container for a complete retrieval result."""

    __slots__ = (
        "answer",
        "confidence",
        "session_id",
        "trace",
        "candidates",
        "query_analysis",
        "iterations",
    )

    def __init__(
        self,
        answer: str | None = None,
        confidence: float = 0.0,
        session_id: str = "",
        trace: dict[str, Any] | None = None,
        candidates: list[RetrievalCandidate] | None = None,
        query_analysis: QueryAnalysis | None = None,
        iterations: int = 0,
    ) -> None:
        self.answer = answer
        self.confidence = confidence
        self.session_id = session_id
        self.trace = trace or {}
        self.candidates = candidates or []
        self.query_analysis = query_analysis
        self.iterations = iterations


def _get_document_info(document_id: str) -> tuple[str, str]:
    """Load document name and description from MongoDB."""
    doc = documents_col().find_one(
        {"documentId": document_id},
        {"name": 1, "description": 1, "_id": 0},
    )
    if doc is None:
        return ("Unknown", "")
    return (doc.get("name", "Unknown"), doc.get("description", ""))


async def retrieve(
    query: str,
    document_id: str,
    llm_provider: LLMProvider,
    *,
    session_id: str | None = None,
) -> RetrievalResult:
    """Execute the full retrieval pipeline.

    Steps:
    1. Query analysis (LLM classifies query type, extracts keywords)
    2. Dual retrieval (Atlas Search + tree navigation in parallel)
    3. Merge & deduplicate results
    4. Load content for top candidates
    5. LLM reasoning loop (check sufficiency, navigate deeper if needed)
    6. Log session turn

    Args:
        query: The user's question.
        document_id: The document to search.
        llm_provider: The LLM provider for reasoning calls.
        session_id: Optional session ID for multi-turn conversations.

    Returns:
        RetrievalResult with answer, confidence, trace, and session info.
    """
    settings = get_settings()
    start_time = time.monotonic()

    # Load document info
    doc_name, doc_description = _get_document_info(document_id)

    # Step 1: Query Analysis
    analysis = await analyze_query(query, doc_name, doc_description, llm_provider)

    # Step 2: Dual Retrieval (parallel)
    content_type_filter = (
        analysis.expected_content_type
        if analysis.expected_content_type != "any"
        else None
    )

    atlas_task = atlas_search(
        query,
        document_id,
        limit=settings.top_n_candidates,
        content_type_filter=content_type_filter,
    )
    tree_task = tree_navigate(
        query,
        document_id,
        doc_name,
        doc_description,
        llm_provider,
    )

    atlas_raw, tree_raw = await asyncio.gather(
        atlas_task, tree_task, return_exceptions=True
    )

    # Handle exceptions from parallel tasks
    if isinstance(atlas_raw, Exception):
        logger.error("atlas_search_exception", extra={"error": str(atlas_raw)})
        atlas_results: list[RetrievalCandidate] = []
    else:
        atlas_results = atlas_raw

    if isinstance(tree_raw, Exception):
        logger.error("tree_navigate_exception", extra={"error": str(tree_raw)})
        tree_results: list[RetrievalCandidate] = []
        nav_path: list[str] = []
    else:
        tree_results, nav_path = tree_raw

    # Step 3: Merge results
    candidates = merge_results(
        atlas_results,
        tree_results,
        atlas_weight=settings.atlas_search_weight,
        tree_weight=settings.tree_navigation_weight,
        top_n=settings.top_n_candidates,
    )

    if not candidates:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return RetrievalResult(
            answer=None,
            confidence=0.0,
            session_id=session_id or "",
            trace={"atlas_hits": 0, "tree_hits": 0, "iterations": 0},
            candidates=[],
            query_analysis=analysis,
            iterations=0,
        )

    # Step 4: Load content for top candidates
    candidate_ids = [c.node_id for c in candidates]
    content_map = load_candidates_content(document_id, candidate_ids)

    # Step 5: Reasoning loop
    nodes_read: list[str] = []
    cross_refs_followed: list[dict[str, Any]] = []
    final_response: ReasonerResponse | None = None
    actual_iterations = 0

    # Check for multi-turn context
    conversation_history = ""
    if session_id:
        conversation_history = get_conversation_history(session_id)

    for iteration in range(settings.max_retrieval_iterations):
        actual_iterations = iteration + 1
        # Build combined content from top candidates
        combined_content_parts: list[str] = []
        combined_ancestor_context = ""
        combined_cross_refs = ""

        for cid in candidate_ids:
            cdata = content_map.get(cid, {})
            if cdata.get("content"):
                combined_content_parts.append(f"[Section {cid}]:\n{cdata['content']}")
                nodes_read.append(cid)
            if not combined_ancestor_context and cdata.get("ancestor_context"):
                combined_ancestor_context = cdata["ancestor_context"]
            if not combined_cross_refs and cdata.get("cross_ref_text"):
                combined_cross_refs = cdata["cross_ref_text"]

        combined_content = "\n\n---\n\n".join(combined_content_parts)

        if conversation_history:
            response = await check_sufficiency_multi_turn(
                query=query,
                content=combined_content,
                ancestor_context=combined_ancestor_context,
                conversation_history=conversation_history,
                llm_provider=llm_provider,
            )
        else:
            response = await check_sufficiency(
                query=query,
                content=combined_content,
                ancestor_context=combined_ancestor_context,
                cross_ref_text=combined_cross_refs,
                llm_provider=llm_provider,
            )

        final_response = response

        if response.sufficient:
            break

        # Follow next action
        if response.next_action is None:
            break

        action = response.next_action
        if action.type == "follow_reference" and action.target_node_id:
            ref_content = load_node_content(document_id, action.target_node_id)
            if ref_content:
                content_map[action.target_node_id] = {
                    "content": ref_content,
                    "ancestor_context": "",
                    "cross_ref_text": "",
                }
                candidate_ids = [action.target_node_id] + candidate_ids
                cross_refs_followed.append(
                    {
                        "from": candidate_ids[1] if len(candidate_ids) > 1 else "",
                        "to": action.target_node_id,
                        "label": action.reasoning,
                    }
                )
            else:
                # H5 fix: hallucinated node ID -- skip this iteration
                logger.warning(
                    "follow_ref_empty_content",
                    extra={"target": action.target_node_id, "iteration": iteration},
                )
        elif action.type == "navigate_deeper" and action.target_node_id:
            deeper_content = load_node_content(document_id, action.target_node_id)
            if deeper_content:
                content_map[action.target_node_id] = {
                    "content": deeper_content,
                    "ancestor_context": combined_ancestor_context,
                    "cross_ref_text": "",
                }
                candidate_ids = [action.target_node_id] + candidate_ids
            else:
                # H5 fix: hallucinated node ID -- skip this iteration
                logger.warning(
                    "navigate_deeper_empty_content",
                    extra={"target": action.target_node_id, "iteration": iteration},
                )
        else:
            break

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    # Build trace
    atlas_hit_dicts = [
        {"nodeId": c.node_id, "score": c.atlas_score, "field": ""}
        for c in (atlas_results if isinstance(atlas_results, list) else [])
    ]

    trace: dict[str, Any] = {
        "atlas_hits": len(atlas_hit_dicts),
        "tree_hits": len(tree_results) if isinstance(tree_results, list) else 0,
        "merged_candidates": len(candidates),
        "iterations": actual_iterations if final_response else 0,
        "navigation_path": nav_path if isinstance(nav_path, list) else [],
        "nodes_read": nodes_read,
    }

    # Step 6: Session management (wrapped in try/except -- M3 fix:
    # session persistence must never crash after answer is computed)
    actual_session_id = session_id or ""
    if session_id:
        try:
            existing = get_session(session_id)
            if existing is None:
                create_session(document_id=document_id, session_id=session_id)

            add_turn(
                session_id=session_id,
                query=query,
                answer=(
                    final_response.answer
                    if final_response and final_response.answer
                    else ""
                ),
                latency_ms=elapsed_ms,
                atlas_search_hits=atlas_hit_dicts,
                tree_navigation_path=nav_path if isinstance(nav_path, list) else [],
                nodes_read=nodes_read,
                cross_references_followed=cross_refs_followed,
                total_nodes_visited=len(nodes_read),
                reasoning_depth=trace.get("iterations", 0),
            )
        except Exception:
            logger.exception(
                "session_persistence_failed", extra={"session_id": session_id}
            )

    return RetrievalResult(
        answer=final_response.answer if final_response else None,
        confidence=final_response.confidence if final_response else 0.0,
        session_id=actual_session_id,
        trace=trace,
        candidates=candidates,
        query_analysis=analysis,
        iterations=trace.get("iterations", 0),
    )
