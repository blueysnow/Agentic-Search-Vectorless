"""Pydantic request/response models for the REST API (Phase 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_QUERY_LENGTH = 10_000
MAX_DOCUMENT_NAME_LENGTH = 500
MAX_CONTENT_LENGTH = 50_000_000  # ~50 MB text cap

# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    """POST /documents request body."""

    name: str = Field(..., min_length=1, max_length=MAX_DOCUMENT_NAME_LENGTH)
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    doc_type: str = Field("text", alias="docType", pattern=r"^(pdf|markdown|text)$")
    domain: str = ""

    model_config = {"populate_by_name": True}


class IngestResponse(BaseModel):
    """POST /documents response body."""

    document_id: str = Field(..., alias="documentId")
    name: str
    status: str
    total_pages: int = Field(0, alias="totalPages")
    total_nodes: int = Field(0, alias="totalNodes")
    total_tokens: int = Field(0, alias="totalTokens")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """POST /query request body."""

    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    document_id: str = Field(..., alias="documentId", min_length=1)
    session_id: str | None = Field(None, alias="sessionId")

    model_config = {"populate_by_name": True}

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            msg = "query must not be blank"
            raise ValueError(msg)
        return stripped


class TraceResponse(BaseModel):
    """Retrieval trace included in query response."""

    atlas_hits: int = Field(0, alias="atlasHits")
    tree_hits: int = Field(0, alias="treeHits")
    merged_candidates: int = Field(0, alias="mergedCandidates")
    iterations: int = 0
    navigation_path: list[str] = Field(default_factory=list, alias="navigationPath")
    nodes_read: list[str] = Field(default_factory=list, alias="nodesRead")

    model_config = {"populate_by_name": True}


class QueryResponse(BaseModel):
    """POST /query response body."""

    answer: str | None = None
    confidence: float = 0.0
    session_id: str = Field("", alias="sessionId")
    trace: TraceResponse = Field(default_factory=TraceResponse)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class IngestionStatusResponse(BaseModel):
    """Ingestion sub-object for document responses."""

    status: str = "pending"
    model: str = ""
    started_at: datetime | None = Field(None, alias="startedAt")
    completed_at: datetime | None = Field(None, alias="completedAt")
    errors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DocumentResponse(BaseModel):
    """GET /documents/{id} response body."""

    document_id: str = Field(..., alias="documentId")
    name: str
    type: str
    domain: str = ""
    description: str = ""
    total_pages: int = Field(0, alias="totalPages")
    total_nodes: int = Field(0, alias="totalNodes")
    total_tokens: int = Field(0, alias="totalTokens")
    ingestion: IngestionStatusResponse = Field(default_factory=IngestionStatusResponse)
    created_at: datetime | None = Field(None, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class DocumentListResponse(BaseModel):
    """GET /documents response body."""

    documents: list[DocumentResponse] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class TurnResponse(BaseModel):
    """A single turn in a session."""

    turn_number: int = Field(..., alias="turnNumber")
    query: str = ""
    answer: str = ""
    latency_ms: int = Field(0, alias="latencyMs")
    timestamp: datetime | None = None

    model_config = {"populate_by_name": True}


class SessionResponse(BaseModel):
    """GET /sessions/{id} response body."""

    session_id: str = Field(..., alias="sessionId")
    document_id: str | None = Field(None, alias="documentId")
    turns: list[TurnResponse] = Field(default_factory=list)
    total_turns: int = Field(0, alias="totalTurns")
    created_at: datetime | None = Field(None, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response body."""

    error: str
    detail: str = ""
    status_code: int = Field(500, alias="statusCode")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """GET /health response body."""

    status: str = "ok"
    mongodb: str = "unknown"
    version: str = "0.1.0"
