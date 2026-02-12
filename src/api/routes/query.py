"""POST /query -- query an ingested document (Phase 4).

Runs the retrieval pipeline and returns the answer with trace.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from src.api.models import QueryRequest, QueryResponse, TraceResponse
from src.config import get_settings
from src.db.collections import documents_col
from src.llm.provider import get_provider
from src.retrieval.pipeline import retrieve
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _find_document_status(document_id: str) -> dict | None:
    """Sync helper: look up document ingestion status from MongoDB."""
    return documents_col().find_one(
        {"documentId": document_id},
        {"ingestion.status": 1, "_id": 0},
    )


@router.post("", response_model=QueryResponse)
async def query_document(request: QueryRequest) -> QueryResponse:
    """Query an ingested document and return an answer with retrieval trace."""
    settings = get_settings()

    # Verify document exists and is ingested -- offload sync PyMongo to thread
    doc = await asyncio.to_thread(_find_document_status, request.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    ingestion_status = doc.get("ingestion", {}).get("status", "unknown")
    if ingestion_status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Document not ready for querying (status: {ingestion_status})",
        )

    try:
        llm = get_provider(settings.llm_provider, model=settings.llm_retrieval_model)

        result = await retrieve(
            query=request.query,
            document_id=request.document_id,
            llm_provider=llm,
            session_id=request.session_id,
        )

        trace = TraceResponse(
            atlas_hits=result.trace.get("atlas_hits", 0),
            tree_hits=result.trace.get("tree_hits", 0),
            merged_candidates=result.trace.get("merged_candidates", 0),
            iterations=result.trace.get("iterations", 0),
            navigation_path=result.trace.get("navigation_path", []),
            nodes_read=result.trace.get("nodes_read", []),
        )

        return QueryResponse(
            answer=result.answer,
            confidence=result.confidence,
            session_id=result.session_id,
            trace=trace,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("query_failed", document_id=request.document_id)
        raise HTTPException(status_code=500, detail="Query failed")
