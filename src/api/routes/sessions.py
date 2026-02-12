"""GET /sessions -- retrieve session history (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from src.api.models import SessionResponse, TurnResponse
from src.retrieval.session_manager import get_session

_SESSION_ID_PATTERN = r"^[a-zA-Z0-9-]+$"

router = APIRouter()


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
