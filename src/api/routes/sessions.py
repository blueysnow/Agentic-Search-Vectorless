"""Session routes -- list, get, delete sessions (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from src.api.models import (
    SessionListItemResponse,
    SessionListResponse,
    SessionResponse,
    TurnResponse,
)
from src.retrieval.session_manager import delete_session, get_session, list_sessions

_SESSION_ID_PATTERN = r"^[a-zA-Z0-9-]+$"

router = APIRouter()


@router.get("/", response_model=SessionListResponse)
def list_all_sessions(
    document_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SessionListResponse:
    """List sessions with optional filtering."""
    sessions = list_sessions(document_id=document_id, limit=limit, offset=offset)
    items = [
        SessionListItemResponse(
            session_id=s.session_id,
            document_id=s.document_id,
            total_turns=s.summary.total_turns,
            first_query=s.turns[0].query if s.turns else None,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=items, total=len(items))


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_by_id(
    session_id: str = Path(
        ..., min_length=1, max_length=100, pattern=_SESSION_ID_PATTERN
    ),
) -> SessionResponse:
    """Get a retrieval session by its session_id."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = [
        TurnResponse(
            turn_number=t.turn_number,
            query=t.query,
            answer=t.answer,
            latency_ms=t.latency_ms,
            timestamp=t.timestamp,
        )
        for t in session.turns
    ]

    return SessionResponse(
        session_id=session.session_id,
        document_id=session.document_id,
        turns=turns,
        total_turns=session.summary.total_turns,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/{session_id}", status_code=204)
def delete_session_by_id(
    session_id: str = Path(
        ..., min_length=1, max_length=100, pattern=_SESSION_ID_PATTERN
    ),
) -> None:
    """Delete a retrieval session by its session_id."""
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
