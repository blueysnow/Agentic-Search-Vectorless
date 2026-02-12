"""Pydantic models for the `nodes` collection (plan section 2.3).

CRITICAL: hybrid tree -- parent_node_id, materialized_path, child_node_ids,
depth, sibling_order, cross_references.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class CrossReference(BaseModel):
    target_node_id: str = Field(..., alias="targetNodeId")
    label: str = ""
    type: str = ""  # appendix | table | figure | section

    model_config = {"populate_by_name": True}


class Node(BaseModel):
    """A hierarchical tree node representing a document section."""

    node_id: str = Field(..., alias="nodeId")
    document_id: str = Field(..., alias="documentId")

    # --- Hierarchy (3 patterns) ---
    parent_node_id: str | None = Field(None, alias="parentNodeId")
    materialized_path: str = Field("", alias="materializedPath")  # "/0001/0003/0006"
    child_node_ids: list[str] = Field(default_factory=list, alias="childNodeIds")
    depth: int = 0  # 0 = root
    sibling_order: int = Field(0, alias="siblingOrder")

    # --- Content ---
    title: str = ""
    summary: str = ""

    # --- Page range ---
    start_page: int = Field(0, alias="startPage")
    end_page: int = Field(0, alias="endPage")
    token_count: int = Field(0, alias="tokenCount")

    # --- Search enhancement ---
    keywords: list[str] = Field(default_factory=list)
    content_type: str = Field(
        "section", alias="contentType"
    )  # section|appendix|table|figure|preface|bibliography

    # --- Cross-references ---
    cross_references: list[CrossReference] = Field(
        default_factory=list, alias="crossReferences"
    )

    # --- Flags ---
    is_leaf: bool = Field(False, alias="isLeaf")
    has_table: bool = Field(False, alias="hasTable")
    has_figure: bool = Field(False, alias="hasFigure")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="updatedAt"
    )

    model_config = {"populate_by_name": True}

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
