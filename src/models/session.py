"""Pydantic models for the `retrieval_sessions` collection (plan section 2.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AtlasSearchHit(BaseModel):
    node_id: str = Field(..., alias="nodeId")
    score: float = 0.0
    field: str = ""

    model_config = {"populate_by_name": True}


class CrossReferenceFollowed(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    label: str = ""

    model_config = {"populate_by_name": True}


class RetrievalTrace(BaseModel):
    atlas_search_hits: list[AtlasSearchHit] = Field(
        default_factory=list, alias="atlasSearchHits"
    )
    tree_navigation_path: list[str] = Field(
        default_factory=list, alias="treeNavigationPath"
    )
    nodes_read: list[str] = Field(default_factory=list, alias="nodesRead")
    cross_references_followed: list[CrossReferenceFollowed] = Field(
        default_factory=list, alias="crossReferencesFollowed"
    )
    total_nodes_visited: int = Field(0, alias="totalNodesVisited")
    reasoning_depth: int = Field(0, alias="reasoningDepth")

    model_config = {"populate_by_name": True}


class Turn(BaseModel):
    turn_number: int = Field(..., alias="turnNumber")
    query: str = ""
    retrieval_trace: RetrievalTrace = Field(
        default_factory=RetrievalTrace, alias="retrievalTrace"
    )
    answer: str = ""
    model: str = ""
    latency_ms: int = Field(0, alias="latencyMs")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"populate_by_name": True}


class SessionSummary(BaseModel):
    total_turns: int = Field(0, alias="totalTurns")
    total_nodes_visited: int = Field(0, alias="totalNodesVisited")
    avg_reasoning_depth: float = Field(0.0, alias="avgReasoningDepth")
    total_latency_ms: int = Field(0, alias="totalLatencyMs")

    model_config = {"populate_by_name": True}


class RetrievalSession(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    document_id: str | None = Field(None, alias="documentId")
    user_id: str | None = Field(None, alias="userId")

    turns: list[Turn] = Field(default_factory=list)
    summary: SessionSummary = Field(default_factory=SessionSummary)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="updatedAt"
    )

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
