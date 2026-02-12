"""Pydantic models for retrieval pipeline results (plan section 5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalCandidate(BaseModel):
    """A merged candidate from Atlas Search + tree navigation."""

    node_id: str = Field(..., alias="nodeId")
    atlas_score: float = Field(0.0, alias="atlasScore")
    tree_score: float = Field(0.0, alias="treeScore")
    final_score: float = Field(0.0, alias="finalScore")
    source: str = ""  # atlas | tree | both

    model_config = {"populate_by_name": True}


class NextAction(BaseModel):
    type: str = ""  # navigate_deeper | follow_reference | search_different_section
    target_node_id: str = Field("", alias="targetNodeId")
    reasoning: str = ""

    model_config = {"populate_by_name": True}


class ReasonerResponse(BaseModel):
    """Structured response from the LLM reasoner (plan section 5.1 step 5)."""

    answer: str | None = None
    confidence: float = 0.0
    sufficient: bool = False
    next_action: NextAction | None = Field(None, alias="nextAction")

    model_config = {"populate_by_name": True}
