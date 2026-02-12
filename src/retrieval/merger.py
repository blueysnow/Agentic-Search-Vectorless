"""Result merger -- weighted merge of Atlas Search + tree navigation (plan section 8.2).

Combines candidates from both retrieval paths using configurable weights.
Default: atlas_weight=0.3, tree_weight=0.7 (tree is more reliable for complex queries).
"""

from __future__ import annotations

import logging

from src.models.retrieval import RetrievalCandidate

logger = logging.getLogger(__name__)


def _normalize_scores(candidates: list[RetrievalCandidate], score_attr: str) -> None:
    """Normalize scores in-place to [0, 1] range via min-max normalization."""
    scores = [getattr(c, score_attr) for c in candidates]
    if not scores:
        return
    min_s = min(scores)
    max_s = max(scores)
    spread = max_s - min_s
    if spread == 0:
        # All scores equal -- set all to 1.0 if nonzero, else 0.0
        for c in candidates:
            setattr(c, score_attr, 1.0 if max_s > 0 else 0.0)
        return
    for c in candidates:
        raw = getattr(c, score_attr)
        setattr(c, score_attr, (raw - min_s) / spread)


def merge_results(
    atlas_candidates: list[RetrievalCandidate],
    tree_candidates: list[RetrievalCandidate],
    *,
    atlas_weight: float = 0.3,
    tree_weight: float = 0.7,
    top_n: int = 5,
) -> list[RetrievalCandidate]:
    """Merge Atlas Search and tree navigation results with weighted scoring.

    1. Normalize each source's scores to [0, 1].
    2. Merge by node_id, combining scores.
    3. Compute final_score = atlas_score * atlas_weight + tree_score * tree_weight.
    4. Sort by final_score descending, return top N.
    """
    # Normalize within each source
    if atlas_candidates:
        _normalize_scores(atlas_candidates, "atlas_score")
    if tree_candidates:
        _normalize_scores(tree_candidates, "tree_score")

    # Merge into a dict keyed by node_id
    merged: dict[str, RetrievalCandidate] = {}

    for c in atlas_candidates:
        merged[c.node_id] = RetrievalCandidate(
            node_id=c.node_id,
            atlas_score=c.atlas_score,
            tree_score=0.0,
            final_score=0.0,
            source="atlas",
        )

    for c in tree_candidates:
        if c.node_id in merged:
            existing = merged[c.node_id]
            existing.tree_score = c.tree_score
            existing.source = "both"
        else:
            merged[c.node_id] = RetrievalCandidate(
                node_id=c.node_id,
                atlas_score=0.0,
                tree_score=c.tree_score,
                final_score=0.0,
                source="tree",
            )

    # Compute final scores
    for candidate in merged.values():
        candidate.final_score = (
            candidate.atlas_score * atlas_weight + candidate.tree_score * tree_weight
        )

    # Sort by final_score descending
    sorted_candidates = sorted(
        merged.values(), key=lambda c: c.final_score, reverse=True
    )
    return sorted_candidates[:top_n]
