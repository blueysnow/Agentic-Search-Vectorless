"""Query analysis -- LLM classifies query type and extracts keywords (plan section 7.1 step 1)."""

from __future__ import annotations

import logging

from src.llm.prompts.query_analysis import QUERY_ANALYSIS_PROMPT
from src.llm.provider import LLMProvider, Message
from src.utils.json_utils import extract_json

logger = logging.getLogger(__name__)

VALID_QUERY_TYPES = frozenset(
    {"factual_lookup", "analytical", "comparison", "multi_hop", "definitional"}
)
VALID_CONTENT_TYPES = frozenset({"section", "table", "figure", "appendix", "any"})


class QueryAnalysis:
    """Structured result of query analysis."""

    __slots__ = ("query_type", "keywords", "expected_content_type", "reasoning")

    def __init__(
        self,
        query_type: str = "factual_lookup",
        keywords: list[str] | None = None,
        expected_content_type: str = "any",
        reasoning: str = "",
    ) -> None:
        self.query_type = (
            query_type if query_type in VALID_QUERY_TYPES else "factual_lookup"
        )
        self.keywords = keywords or []
        self.expected_content_type = (
            expected_content_type
            if expected_content_type in VALID_CONTENT_TYPES
            else "any"
        )
        self.reasoning = reasoning


async def analyze_query(
    query: str,
    document_name: str,
    document_description: str,
    llm_provider: LLMProvider,
) -> QueryAnalysis:
    """Classify the query and extract keywords using the LLM.

    Returns a QueryAnalysis with sensible defaults on LLM failure.
    """
    if not query.strip():
        return QueryAnalysis(keywords=[])

    prompt = QUERY_ANALYSIS_PROMPT.format(
        query=query,
        document_name=document_name,
        document_description=document_description,
    )

    try:
        response = await llm_provider.chat_async(
            [Message(role="user", content=prompt)],
            temperature=0.0,
        )
    except Exception:
        logger.exception("query_analysis_llm_failed", extra={"query": query})
        # Fallback: extract simple keywords from the query
        return QueryAnalysis(keywords=_fallback_keywords(query))

    parsed = extract_json(response.content)
    if parsed is None or not isinstance(parsed, dict):
        logger.warning("query_analysis_parse_failed", extra={"raw": response.content})
        return QueryAnalysis(keywords=_fallback_keywords(query))

    return QueryAnalysis(
        query_type=parsed.get("query_type", "factual_lookup"),
        keywords=parsed.get("keywords", []),
        expected_content_type=parsed.get("expected_content_type", "any"),
        reasoning=parsed.get("reasoning", ""),
    )


def _fallback_keywords(query: str) -> list[str]:
    """Extract naive keywords from a query string (stopword-light)."""
    stopwords = frozenset(
        {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "what",
            "which",
            "who",
            "whom",
            "how",
            "where",
            "when",
            "why",
            "do",
            "does",
            "did",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "and",
            "or",
            "but",
            "not",
            "this",
            "that",
            "it",
            "its",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "can",
            "could",
            "will",
            "would",
            "shall",
            "should",
            "may",
            "might",
            "about",
        }
    )
    words = query.lower().split()
    return [
        w.strip("?.,!;:\"'")
        for w in words
        if w.strip("?.,!;:\"'") not in stopwords and len(w) > 1
    ]
