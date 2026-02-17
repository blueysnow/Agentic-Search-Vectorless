"""POST /query/stream -- SSE streaming endpoint for chat (bridges frontend/backend gap).

Wraps the existing retrieval pipeline and emits SSE events matching the
frontend's use-chat-stream.ts contract:
  - thinking: retrieval progress steps
  - metadata: retrieval trace data (atlas_hits, tree_hits, etc.)
  - content: answer text chunks
  - citations: page citations from retrieval
  - done: stream complete
  - error: on failure
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import get_settings
from src.db.collections import documents_col, nodes_col
from src.llm.provider import get_provider
from src.retrieval.pipeline import retrieve
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request model -- matches what the Next.js proxy sends
# ---------------------------------------------------------------------------


class StreamRequest(BaseModel):
    """POST /query/stream request body.

    Accepts both the Next.js proxy format (message + document_ids) and the
    standard backend format (query + document_id).
    """

    # Next.js proxy sends 'message'; backend pattern uses 'query'
    message: str | None = None
    query: str | None = None

    # Next.js proxy sends 'document_ids' as array; backend uses 'document_id'
    document_ids: list[str] | None = Field(None, alias="document_ids")
    document_id: str | None = Field(None, alias="documentId")

    session_id: str | None = Field(None, alias="sessionId")

    model_config = {"populate_by_name": True}

    def resolved_query(self) -> str:
        """Return the query text, preferring 'message' (frontend) over 'query' (backend)."""
        return (self.message or self.query or "").strip()

    def resolved_document_id(self) -> str:
        """Return the first document_id, preferring array form."""
        if self.document_ids:
            return self.document_ids[0]
        return self.document_id or ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_document_status(document_id: str) -> dict | None:
    """Sync helper: look up document ingestion status from MongoDB."""
    return documents_col().find_one(
        {"documentId": document_id},
        {"ingestion.status": 1, "_id": 0},
    )


def _sse_event(event_type: str, data: Any) -> str:
    """Format a single SSE event line."""
    payload: dict[str, Any] = {"type": event_type}
    if isinstance(data, str):
        payload["content"] = data
    elif isinstance(data, dict):
        payload["data"] = data
    else:
        payload["content"] = str(data)
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# SSE Generator
# ---------------------------------------------------------------------------


async def _stream_response(request: StreamRequest) -> AsyncGenerator[str, None]:
    """Generate SSE events for a streaming chat response."""
    settings = get_settings()
    query_text = request.resolved_query()
    document_id = request.resolved_document_id()

    if not query_text:
        yield _sse_event("error", "Query text is required")
        yield _sse_event("done", "")
        return

    if not document_id:
        yield _sse_event("error", "Document ID is required")
        yield _sse_event("done", "")
        return

    # Step 1: Emit thinking -- document validation
    yield _sse_event("thinking", f"Checking document {document_id}...")

    # Verify document exists and is ingested
    doc = await asyncio.to_thread(_find_document_status, document_id)
    if doc is None:
        yield _sse_event("error", "Document not found")
        yield _sse_event("done", "")
        return

    ingestion_status = doc.get("ingestion", {}).get("status", "unknown")
    if ingestion_status != "completed":
        yield _sse_event(
            "error", f"Document not ready for querying (status: {ingestion_status})"
        )
        yield _sse_event("done", "")
        return

    # Step 2: Emit thinking -- starting retrieval
    yield _sse_event("thinking", f"Analyzing query: {query_text[:100]}...")

    try:
        llm = get_provider(settings.llm_provider, model=settings.llm_retrieval_model)

        # Step 3: Emit thinking -- running pipeline
        yield _sse_event(
            "thinking", "Running dual retrieval (Atlas Search + Tree Navigation)..."
        )

        result = await asyncio.wait_for(
            retrieve(
                query=query_text,
                document_id=document_id,
                llm_provider=llm,
                session_id=request.session_id,
            ),
            timeout=60.0,
        )

        # Step 4: Emit metadata with retrieval trace
        yield _sse_event(
            "metadata",
            {
                "atlas_hits": result.trace.get("atlas_hits", 0),
                "tree_hits": result.trace.get("tree_hits", 0),
                "merged_candidates": result.trace.get("merged_candidates", 0),
                "iterations": result.trace.get("iterations", 0),
                "navigation_path": result.trace.get("navigation_path", []),
                "nodes_read": result.trace.get("nodes_read", []),
                "session_id": result.session_id,
                "confidence": result.confidence,
            },
        )

        # Step 5: Emit content (the answer)
        answer = (
            result.answer
            or "I could not find an answer to your question in the document."
        )
        yield _sse_event("content", answer)

        # Step 6: Emit citations from nodes_read (page references)
        nodes_read = result.trace.get("nodes_read", [])
        if nodes_read:
            # Batch-fetch startPage for all nodes to avoid N+1 queries
            node_docs = list(
                nodes_col().find(
                    {"documentId": document_id, "nodeId": {"$in": nodes_read}},
                    {"nodeId": 1, "startPage": 1, "title": 1, "_id": 0},
                )
            )
            node_page_map = {
                n["nodeId"]: n.get("startPage", 1) for n in node_docs
            }
            node_title_map = {
                n["nodeId"]: n.get("title", "") for n in node_docs
            }
        else:
            node_page_map = {}
            node_title_map = {}

        seen_nodes: set[str] = set()
        for node_id in nodes_read:
            # De-duplicate: emit one citation per unique node
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)

            page = node_page_map.get(node_id, 1)
            title = node_title_map.get(node_id, node_id)
            yield _sse_event(
                "citation",
                {
                    "page": page,
                    "text": f"Referenced section: {title or node_id}",
                },
            )

        # Step 7: Done
        yield _sse_event("done", "")

    except asyncio.TimeoutError:
        logger.error("stream_retrieval_timeout", document_id=document_id)
        yield _sse_event("error", "Retrieval timed out")
        yield _sse_event("done", "")
    except Exception:
        logger.exception("stream_retrieval_failed", document_id=document_id)
        yield _sse_event("error", "Retrieval failed")
        yield _sse_event("done", "")


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("")
async def stream_query(request: StreamRequest) -> StreamingResponse:
    """Stream a chat response as SSE events."""
    return StreamingResponse(
        _stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
