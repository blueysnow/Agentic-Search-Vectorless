"""Session manager -- multi-turn conversation tracking in MongoDB (plan section 7.3).

Manages retrieval sessions with turns, traces, and summaries.
Persists to the retrieval_sessions collection.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from src.db.collections import retrieval_sessions_col
from src.models.session import (
    AtlasSearchHit,
    CrossReferenceFollowed,
    RetrievalSession,
    RetrievalTrace,
    Turn,
)

logger = logging.getLogger(__name__)


def create_session(
    document_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> RetrievalSession:
    """Create a new retrieval session and persist it to MongoDB.

    Returns the created session object.
    """
    sid = session_id or str(uuid.uuid4())
    session = RetrievalSession(
        session_id=sid,
        document_id=document_id,
        user_id=user_id,
    )
    retrieval_sessions_col().insert_one(session.to_mongo())
    return session


def list_sessions(
    document_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RetrievalSession]:
    """List sessions with optional filtering."""
    query: dict = {}
    if document_id:
        query["documentId"] = document_id
    cursor = (
        retrieval_sessions_col()
        .find(query)
        .sort("createdAt", -1)
        .skip(offset)
        .limit(limit)
    )
    results = []
    for doc in cursor:
        doc.pop("_id", None)
        results.append(RetrievalSession(**doc))
    return results


def delete_session(session_id: str) -> bool:
    """Delete a session from MongoDB by session_id.

    Returns True if a session was deleted, False if not found.
    """
    result = retrieval_sessions_col().delete_one({"sessionId": session_id})
    return result.deleted_count > 0


def get_session(session_id: str) -> RetrievalSession | None:
    """Load a session from MongoDB by session_id.

    Returns None if session not found.
    """
    doc = retrieval_sessions_col().find_one({"sessionId": session_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return RetrievalSession(**doc)


def add_turn(
    session_id: str,
    query: str,
    answer: str,
    *,
    model: str = "",
    latency_ms: int = 0,
    atlas_search_hits: list[dict[str, Any]] | None = None,
    tree_navigation_path: list[str] | None = None,
    nodes_read: list[str] | None = None,
    cross_references_followed: list[dict[str, Any]] | None = None,
    total_nodes_visited: int = 0,
    reasoning_depth: int = 0,
) -> Turn:
    """Add a turn to an existing session.

    Creates the RetrievalTrace and Turn, pushes to session's turns array,
    and updates summary statistics.
    """
    # Build trace
    trace = RetrievalTrace(
        atlas_search_hits=[AtlasSearchHit(**h) for h in (atlas_search_hits or [])],
        tree_navigation_path=tree_navigation_path or [],
        nodes_read=nodes_read or [],
        cross_references_followed=[
            CrossReferenceFollowed(**c) for c in (cross_references_followed or [])
        ],
        total_nodes_visited=total_nodes_visited,
        reasoning_depth=reasoning_depth,
    )

    # Get current turn count
    try:
        session_doc = retrieval_sessions_col().find_one(
            {"sessionId": session_id},
            {"turns": 1, "_id": 0},
        )
    except Exception:
        logger.exception(
            "session_get_turn_count_failed", extra={"session_id": session_id}
        )
        session_doc = None
    turn_number = len(session_doc.get("turns", [])) + 1 if session_doc else 1

    turn = Turn(
        turn_number=turn_number,
        query=query,
        retrieval_trace=trace,
        answer=answer,
        model=model,
        latency_ms=latency_ms,
    )

    # Push turn and update summary atomically
    try:
        now = datetime.now(UTC)
        retrieval_sessions_col().update_one(
            {"sessionId": session_id},
            {
                "$push": {"turns": turn.model_dump(by_alias=True)},
                "$set": {"updatedAt": now},
                "$inc": {
                    "summary.totalTurns": 1,
                    "summary.totalNodesVisited": total_nodes_visited,
                    "summary.totalLatencyMs": latency_ms,
                },
            },
        )
    except Exception:
        logger.exception("session_add_turn_failed", extra={"session_id": session_id})

    return turn


def get_conversation_history(session_id: str, max_turns: int = 5) -> str:
    """Format recent conversation history for multi-turn context.

    Returns a formatted string of recent Q&A pairs.
    """
    session = get_session(session_id)
    if session is None or not session.turns:
        return ""

    recent_turns = session.turns[-max_turns:]
    lines: list[str] = []
    for t in recent_turns:
        lines.append(f"Q: {t.query}")
        if t.answer:
            lines.append(f"A: {t.answer}")
        lines.append("")  # blank line separator

    return "\n".join(lines).strip()


def get_previously_visited_nodes(session_id: str) -> list[str]:
    """Get list of all node IDs visited across all turns in this session."""
    session = get_session(session_id)
    if session is None:
        return []

    visited: list[str] = []
    for turn in session.turns:
        visited.extend(turn.retrieval_trace.nodes_read)
        visited.extend(turn.retrieval_trace.tree_navigation_path)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for nid in visited:
        if nid not in seen:
            seen.add(nid)
            result.append(nid)
    return result
