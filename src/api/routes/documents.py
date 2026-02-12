"""GET /documents -- list and retrieve documents (Phase 4)."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Path, Query

from src.api.models import (
    DocumentListResponse,
    DocumentResponse,
    IngestionStatusResponse,
)
from src.db.collections import documents_col
from src.utils.logger import get_logger

logger = get_logger(__name__)

_DOCUMENT_ID_PATTERN = r"^[a-zA-Z0-9-]+$"

router = APIRouter()

_PATH_RE = re.compile(r"(/[a-zA-Z0-9_./-]+){3,}")


def _sanitize_errors(errors: list[str]) -> list[str]:
    """Strip internal file paths from error messages before returning to clients."""
    return [_PATH_RE.sub("[path]", e) for e in errors]


def _doc_to_response(doc: dict) -> DocumentResponse:
    """Convert a MongoDB document dict to a DocumentResponse."""
    ingestion_raw = doc.get("ingestion", {})
    return DocumentResponse(
        document_id=doc.get("documentId", ""),
        name=doc.get("name", ""),
        type=doc.get("type", ""),
        domain=doc.get("domain", ""),
        description=doc.get("description", ""),
        total_pages=doc.get("totalPages", 0),
        total_nodes=doc.get("totalNodes", 0),
        total_tokens=doc.get("totalTokens", 0),
        ingestion=IngestionStatusResponse(
            status=ingestion_raw.get("status", "unknown"),
            model=ingestion_raw.get("model", ""),
            started_at=ingestion_raw.get("startedAt"),
            completed_at=ingestion_raw.get("completedAt"),
            errors=_sanitize_errors(ingestion_raw.get("errors", [])),
        ),
        created_at=doc.get("createdAt"),
        updated_at=doc.get("updatedAt"),
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    domain: str | None = None,
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> DocumentListResponse:
    """List all documents, with optional filtering by domain and ingestion status."""
    query: dict = {}
    if domain:
        query["domain"] = domain
    if status:
        query["ingestion.status"] = status

    cursor = (
        documents_col()
        .find(query, {"_id": 0})
        .sort([("createdAt", -1)])
        .skip(skip)
        .limit(limit)
    )
    docs = list(cursor)
    total = documents_col().count_documents(query)

    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str = Path(
        ..., min_length=1, max_length=100, pattern=_DOCUMENT_ID_PATTERN
    ),
) -> DocumentResponse:
    """Get a single document by its document_id."""
    doc = documents_col().find_one({"documentId": document_id}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_response(doc)
