"""Pydantic models for the `documents` collection (plan section 2.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestionConfig(BaseModel):
    max_pages_per_node: int = 10
    max_tokens_per_node: int = 20000
    toc_check_pages: int = 20
    add_node_summaries: bool = True
    add_node_text: bool = False


class Ingestion(BaseModel):
    status: str = "pending"  # pending | processing | completed | failed
    model: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    config: IngestionConfig = Field(default_factory=IngestionConfig)
    errors: list[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    author: str = ""
    year: int | None = None
    tags: list[str] = Field(default_factory=list)


class Document(BaseModel):
    """Represents a single ingested document."""

    document_id: str = Field(..., alias="documentId")
    name: str
    type: str  # pdf | markdown | text
    domain: str = ""
    description: str = ""
    total_pages: int = Field(0, alias="totalPages")
    total_nodes: int = Field(0, alias="totalNodes")
    total_tokens: int = Field(0, alias="totalTokens")
    root_node_id: str = Field("0001", alias="rootNodeId")

    ingestion: Ingestion = Field(default_factory=Ingestion)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="updatedAt"
    )

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        """Serialize to a MongoDB-ready dict using camelCase field names."""
        return self.model_dump(by_alias=True)
