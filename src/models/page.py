"""Pydantic models for the `pages` collection (plan section 2.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Page(BaseModel):
    """Raw page/section content, stored separately from nodes."""

    document_id: str = Field(..., alias="documentId")
    page_number: int = Field(..., alias="pageNumber")  # 1-indexed
    node_id: str = Field(..., alias="nodeId")

    content: str = ""
    content_hash: str = Field("", alias="contentHash")  # sha256:...
    token_count: int = Field(0, alias="tokenCount")

    has_table: bool = Field(False, alias="hasTable")
    has_figure: bool = Field(False, alias="hasFigure")
    language: str = "en"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt"
    )

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
