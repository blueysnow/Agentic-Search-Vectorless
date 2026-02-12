"""LLM API cost estimation for ingestion and query operations."""

from __future__ import annotations

# Pricing per 1M tokens (USD) -- updated Feb 2025
# GPT-4o
GPT4O_INPUT_PER_1M = 2.50
GPT4O_OUTPUT_PER_1M = 10.00

# GPT-4o-mini
GPT4O_MINI_INPUT_PER_1M = 0.15
GPT4O_MINI_OUTPUT_PER_1M = 0.60

# Claude Sonnet (claude-sonnet-4-20250514)
CLAUDE_SONNET_INPUT_PER_1M = 3.00
CLAUDE_SONNET_OUTPUT_PER_1M = 15.00

# Claude Haiku (claude-haiku-4-5-20251001)
CLAUDE_HAIKU_INPUT_PER_1M = 0.80
CLAUDE_HAIKU_OUTPUT_PER_1M = 4.00

# Average output tokens per LLM call during ingestion (tree building, verification, enrichment)
_AVG_OUTPUT_TOKENS_PER_INGEST_CALL = 500
# Average number of LLM calls per page during ingestion
_AVG_LLM_CALLS_PER_PAGE = 3

# Average tokens per query iteration (input context + output reasoning)
_AVG_INPUT_TOKENS_PER_QUERY_ITER = 4000
_AVG_OUTPUT_TOKENS_PER_QUERY_ITER = 800
# Average iterations per query
_AVG_ITERATIONS_PER_QUERY = 2


def estimate_ingest_cost(
    total_pages: int,
    total_tokens: int,
    *,
    input_price_per_1m: float = GPT4O_MINI_INPUT_PER_1M,
    output_price_per_1m: float = GPT4O_MINI_OUTPUT_PER_1M,
) -> float:
    """Estimate LLM API cost for ingesting a document.

    Args:
        total_pages: Number of pages in the document.
        total_tokens: Total input tokens across all pages.
        input_price_per_1m: Price per 1M input tokens.
        output_price_per_1m: Price per 1M output tokens.

    Returns:
        Estimated cost in USD.
    """
    if total_pages == 0:
        return 0.0
    num_calls = total_pages * _AVG_LLM_CALLS_PER_PAGE
    input_cost = (
        (total_tokens * num_calls / total_pages) / 1_000_000 * input_price_per_1m
    )
    output_tokens = num_calls * _AVG_OUTPUT_TOKENS_PER_INGEST_CALL
    output_cost = output_tokens / 1_000_000 * output_price_per_1m
    return input_cost + output_cost


def estimate_query_cost(
    num_iterations: int = _AVG_ITERATIONS_PER_QUERY,
    *,
    input_price_per_1m: float = CLAUDE_SONNET_INPUT_PER_1M,
    output_price_per_1m: float = CLAUDE_SONNET_OUTPUT_PER_1M,
) -> float:
    """Estimate LLM API cost for a single query.

    Args:
        num_iterations: Number of reasoning iterations.
        input_price_per_1m: Price per 1M input tokens.
        output_price_per_1m: Price per 1M output tokens.

    Returns:
        Estimated cost in USD.
    """
    # +1 for the initial query analysis call
    total_calls = num_iterations + 1
    input_tokens = total_calls * _AVG_INPUT_TOKENS_PER_QUERY_ITER
    output_tokens = total_calls * _AVG_OUTPUT_TOKENS_PER_QUERY_ITER
    input_cost = input_tokens / 1_000_000 * input_price_per_1m
    output_cost = output_tokens / 1_000_000 * output_price_per_1m
    return input_cost + output_cost


def format_cost_report(
    ingest_cost: float,
    query_cost: float,
    num_queries: int = 1,
) -> str:
    """Generate a human-readable cost report string.

    Args:
        ingest_cost: Estimated ingestion cost in USD.
        query_cost: Estimated per-query cost in USD.
        num_queries: Number of queries to project.

    Returns:
        Formatted cost report.
    """
    total_query_cost = query_cost * num_queries
    total = ingest_cost + total_query_cost
    lines = [
        "=== Cost Estimate Report ===",
        f"Ingestion cost:       ${ingest_cost:.4f}",
        f"Per-query cost:       ${query_cost:.4f}",
        f"Queries projected:    {num_queries}",
        f"Total query cost:     ${total_query_cost:.4f}",
        "---",
        f"Total estimated cost: ${total:.4f}",
        "============================",
    ]
    return "\n".join(lines)
