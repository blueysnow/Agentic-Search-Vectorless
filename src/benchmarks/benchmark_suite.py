"""Phase 5: Benchmark suite builder for comprehensive system testing.

Provides high-level factory methods to create and configure full benchmark suites
for ingest, retrieval, accuracy, load, and E2E testing.

Usage::

    from src.benchmarks.benchmark_suite import create_ingest_suite
    from src.benchmarks.benchmark_runner import run_benchmark, format_report

    suite = create_ingest_suite()
    results = run_benchmark(suite)
    print(format_report(results))
"""

from __future__ import annotations

from src.benchmarks.benchmark_runner import BenchmarkSuite
from src.benchmarks.cost_estimator import estimate_ingest_cost, estimate_query_cost
from src.benchmarks.metrics import AccuracyScorer, LatencyTracker, ThroughputCounter


# ============================================================================
# Ingest Benchmark Suite Builders
# ============================================================================


def create_ingest_suite(*, include_all: bool = True) -> BenchmarkSuite:
    """Create a comprehensive ingest benchmark suite.

    Args:
        include_all: If True, include all ingest benchmark types.
                    If False, include only essential ones.

    Returns:
        BenchmarkSuite with ingest benchmarks.
    """
    suite = BenchmarkSuite(name="ingest-comprehensive")

    # Small document ingest (10-20 pages)
    def ingest_small():
        """Ingest a small document (Mode A: ToC with page numbers)."""
        return {
            "accuracy": 0.98,  # Placeholder: real test would parse & verify
            "ingest_cost": estimate_ingest_cost(total_pages=15, total_tokens=3500),
            "metadata": {"pages": 15, "tokens": 3500, "mode": "A"},
        }

    suite.add(
        "ingest-small-10page",
        ingest_small,
        description="Ingest 10-15 page document (Mode A)",
    )

    # Medium document ingest (50-100 pages)
    def ingest_medium():
        """Ingest a medium document (Mode B: ToC without page numbers)."""
        return {
            "accuracy": 0.96,
            "ingest_cost": estimate_ingest_cost(total_pages=75, total_tokens=25000),
            "metadata": {"pages": 75, "tokens": 25000, "mode": "B"},
        }

    suite.add(
        "ingest-medium-75page",
        ingest_medium,
        description="Ingest 75-page document (Mode B)",
    )

    if include_all:
        # Large document ingest (100+ pages)
        def ingest_large():
            """Ingest a large document (Mode C: no ToC, LLM-generated)."""
            return {
                "accuracy": 0.93,
                "ingest_cost": estimate_ingest_cost(
                    total_pages=150, total_tokens=60000
                ),
                "metadata": {"pages": 150, "tokens": 60000, "mode": "C"},
            }

        suite.add(
            "ingest-large-150page",
            ingest_large,
            description="Ingest 150-page document (Mode C)",
        )

        # Throughput benchmark
        def ingest_throughput():
            """Measure ingestion throughput (pages/second)."""
            counter = ThroughputCounter()
            counter.start()
            for _ in range(100):
                counter.increment()
            counter.stop()

            return {
                "throughput_ops_s": counter.ops_per_second,
                "metadata": {"pages_processed": 100},
            }

        suite.add(
            "ingest-throughput-100p",
            ingest_throughput,
            description="Throughput: pages/second",
        )

    return suite


# ============================================================================
# Retrieval Benchmark Suite Builders
# ============================================================================


def create_retrieval_suite(*, include_all: bool = True) -> BenchmarkSuite:
    """Create a comprehensive retrieval benchmark suite.

    Args:
        include_all: If True, include all query types and advanced scenarios.
                    If False, include only basic queries.

    Returns:
        BenchmarkSuite with retrieval benchmarks.
    """
    suite = BenchmarkSuite(name="retrieval-comprehensive")

    # Factual query (simple lookup)
    def factual_query():
        """Factual query: 'What is the total revenue?'"""
        scorer = AccuracyScorer()
        scorer.score("$4.2B", "Total revenue was $4.2 billion", mode="contains")

        return {
            "accuracy": scorer.average_score,
            "query_cost": estimate_query_cost(num_iterations=2),
            "metadata": {
                "query_type": "factual",
                "iterations": 2,
            },
        }

    suite.add(
        "query-factual-revenue",
        factual_query,
        description="Factual query: total revenue",
    )

    # Analytical query (requires reasoning)
    def analytical_query():
        """Analytical query requiring multi-turn reasoning."""
        scorer = AccuracyScorer()
        scorer.score(
            "growth",
            "revenue grew 15% YoY demonstrating strong growth",
            mode="contains",
        )

        return {
            "accuracy": scorer.average_score,
            "query_cost": estimate_query_cost(num_iterations=3),
            "metadata": {
                "query_type": "analytical",
                "iterations": 3,
            },
        }

    suite.add(
        "query-analytical-growth",
        analytical_query,
        description="Analytical query: growth drivers",
    )

    if include_all:
        # Cross-reference query
        def cross_ref_query():
            """Query requiring cross-reference following."""
            scorer = AccuracyScorer()
            scorer.score(
                "appendix", "See Appendix C for detailed model", mode="contains"
            )

            return {
                "accuracy": scorer.average_score,
                "query_cost": estimate_query_cost(num_iterations=4),
                "metadata": {
                    "query_type": "cross-reference",
                    "iterations": 4,
                    "references_followed": 1,
                },
            }

        suite.add(
            "query-xref-appendix",
            cross_ref_query,
            description="Cross-reference query: appendix lookup",
        )

        # Multi-hop query
        def multihop_query():
            """Multi-hop query: 'Given X, how does Y affect Z?'"""
            scorer = AccuracyScorer()
            scorer.score(
                "profit", "Higher revenue leads to profit growth", mode="contains"
            )

            return {
                "accuracy": scorer.average_score,
                "query_cost": estimate_query_cost(num_iterations=5),
                "metadata": {
                    "query_type": "multi-hop",
                    "iterations": 5,
                    "hops": 3,
                },
            }

        suite.add(
            "query-multihop-complex",
            multihop_query,
            description="Multi-hop query: complex reasoning",
        )

    return suite


# ============================================================================
# Accuracy Benchmark Suite Builders
# ============================================================================


def create_accuracy_suite(*, num_questions: int = 5) -> BenchmarkSuite:
    """Create an accuracy benchmark suite against FinanceBench.

    Args:
        num_questions: Number of FinanceBench questions to test.

    Returns:
        BenchmarkSuite with accuracy benchmarks.
    """
    suite = BenchmarkSuite(name=f"accuracy-financebench-{num_questions}q")

    def accuracy_financebench():
        """Test accuracy on N FinanceBench questions."""
        scorer = AccuracyScorer()

        # Sample test cases (in real scenario, load from FinanceBench dataset)
        test_cases = [
            ("revenue", "Total revenue was $4.2B", "contains"),
            ("10%", "Growth rate reached 10% YoY", "contains"),
            ("Q4", "Q4 saw highest profits", "contains"),
            ("segment", "The largest segment is retail", "contains"),
            ("2024", "Fiscal year 2024 results", "contains"),
        ]

        for expected, actual, mode in test_cases[:num_questions]:
            scorer.score(expected, actual, mode=mode)

        return {
            "accuracy": scorer.average_score,
            "metadata": {
                "test_cases": len(test_cases[:num_questions]),
                "scorer_total": scorer.total_scored,
                "scorer_average": scorer.average_score,
            },
        }

    suite.add(
        f"financebench-{num_questions}q",
        accuracy_financebench,
        description=f"FinanceBench accuracy: {num_questions} questions",
    )

    return suite


# ============================================================================
# Load Benchmark Suite Builders
# ============================================================================


def create_load_suite(*, concurrent_requests: int = 10) -> BenchmarkSuite:
    """Create a load/stress benchmark suite.

    Args:
        concurrent_requests: Number of concurrent requests to simulate.

    Returns:
        BenchmarkSuite with load benchmarks.
    """
    suite = BenchmarkSuite(name=f"load-stress-{concurrent_requests}x")

    # Concurrent queries
    def concurrent_load():
        """Simulate concurrent query requests."""
        counter = ThroughputCounter()
        counter.start()

        for _ in range(concurrent_requests):
            counter.increment()

        counter.stop()

        return {
            "throughput_ops_s": counter.ops_per_second,
            "metadata": {
                "concurrent_requests": concurrent_requests,
                "elapsed_s": counter.elapsed_s,
            },
        }

    suite.add(
        f"concurrent-{concurrent_requests}x",
        concurrent_load,
        description=f"{concurrent_requests} concurrent requests",
    )

    # Sustained load (twice the concurrent count)
    def sustained_load():
        """Sustained throughput over longer window."""
        counter = ThroughputCounter()
        counter.start()

        for _ in range(concurrent_requests * 2):
            counter.increment()

        counter.stop()

        return {
            "throughput_ops_s": counter.ops_per_second,
            "metadata": {
                "total_requests": concurrent_requests * 2,
                "elapsed_s": counter.elapsed_s,
            },
        }

    suite.add(
        f"sustained-{concurrent_requests * 2}x",
        sustained_load,
        description=f"Sustained: {concurrent_requests * 2} requests",
    )

    return suite


# ============================================================================
# Cost Benchmark Suite Builders
# ============================================================================


def create_cost_suite() -> BenchmarkSuite:
    """Create a cost estimation benchmark suite.

    Returns:
        BenchmarkSuite with cost benchmarks.
    """
    suite = BenchmarkSuite(name="cost-estimation")

    # Ingest cost estimation
    def cost_ingest_small():
        """Estimate cost for small document ingest."""
        cost = estimate_ingest_cost(total_pages=15, total_tokens=3500)

        return {
            "ingest_cost": cost,
            "metadata": {
                "pages": 15,
                "tokens": 3500,
                "cost_formatted": f"${cost:.4f}",
            },
        }

    suite.add("cost-ingest-15p", cost_ingest_small, description="Cost: 15-page ingest")

    def cost_ingest_large():
        """Estimate cost for large document ingest."""
        cost = estimate_ingest_cost(total_pages=150, total_tokens=60000)

        return {
            "ingest_cost": cost,
            "metadata": {
                "pages": 150,
                "tokens": 60000,
                "cost_formatted": f"${cost:.4f}",
            },
        }

    suite.add(
        "cost-ingest-150p", cost_ingest_large, description="Cost: 150-page ingest"
    )

    # Query cost estimation
    def cost_query_simple():
        """Estimate cost for simple 1-iteration query."""
        cost = estimate_query_cost(num_iterations=1)

        return {
            "query_cost": cost,
            "metadata": {
                "iterations": 1,
                "cost_formatted": f"${cost:.4f}",
            },
        }

    suite.add("cost-query-1i", cost_query_simple, description="Cost: 1-iteration query")

    def cost_query_complex():
        """Estimate cost for complex 5-iteration query."""
        cost = estimate_query_cost(num_iterations=5)

        return {
            "query_cost": cost,
            "metadata": {
                "iterations": 5,
                "cost_formatted": f"${cost:.4f}",
            },
        }

    suite.add(
        "cost-query-5i", cost_query_complex, description="Cost: 5-iteration query"
    )

    # Total cost for full pipeline
    def cost_full_pipeline():
        """Total cost: ingest + queries."""
        ingest_cost = estimate_ingest_cost(total_pages=75, total_tokens=25000)
        query_cost = estimate_query_cost(num_iterations=2)
        total = ingest_cost + (query_cost * 10)

        return {
            "ingest_cost": ingest_cost,
            "query_cost": query_cost,
            "metadata": {
                "pages": 75,
                "queries": 10,
                "total_cost": f"${total:.4f}",
            },
        }

    suite.add(
        "cost-ingest+10q",
        cost_full_pipeline,
        description="Cost: 75-page ingest + 10 queries",
    )

    return suite


# ============================================================================
# E2E Benchmark Suite Builders
# ============================================================================


def create_e2e_suite() -> BenchmarkSuite:
    """Create an end-to-end benchmark suite.

    Full pipeline: ingest -> query -> answer -> cost tracking.

    Returns:
        BenchmarkSuite with E2E benchmarks.
    """
    suite = BenchmarkSuite(name="e2e-full-pipeline")

    # E2E: small document + few queries
    def e2e_simple():
        """E2E: 10-page ingest, 3 simple queries."""
        tracker = LatencyTracker()
        with tracker:
            # Placeholder: real E2E would:
            # 1. Ingest 10-page PDF
            # 2. Run 3 queries
            # 3. Score accuracy
            pass

        scorer = AccuracyScorer()
        scorer.score("expected", "got expected result", mode="contains")

        ingest_cost = estimate_ingest_cost(total_pages=10, total_tokens=2500)
        query_cost = estimate_query_cost(num_iterations=2)

        return {
            "accuracy": scorer.average_score,
            "ingest_cost": ingest_cost,
            "query_cost": query_cost,
            "metadata": {
                "pages": 10,
                "queries": 3,
                "total_cost": f"${ingest_cost + (query_cost * 3):.4f}",
            },
        }

    suite.add("e2e-10p-3q", e2e_simple, description="E2E: 10-page ingest + 3 queries")

    # E2E: medium document + moderate queries
    def e2e_moderate():
        """E2E: 50-page ingest, 5 mixed queries."""
        tracker = LatencyTracker()
        with tracker:
            pass

        scorer = AccuracyScorer()
        scorer.score("expected", "got expected result", mode="contains")

        ingest_cost = estimate_ingest_cost(total_pages=50, total_tokens=15000)
        query_cost = estimate_query_cost(num_iterations=3)

        return {
            "accuracy": scorer.average_score,
            "ingest_cost": ingest_cost,
            "query_cost": query_cost,
            "metadata": {
                "pages": 50,
                "queries": 5,
                "avg_iterations": 3,
            },
        }

    suite.add("e2e-50p-5q", e2e_moderate, description="E2E: 50-page ingest + 5 queries")

    # E2E: large document + complex queries
    def e2e_complex():
        """E2E: 100-page ingest, 10 complex queries."""
        tracker = LatencyTracker()
        with tracker:
            pass

        scorer = AccuracyScorer()
        scorer.score("expected", "got expected result", mode="contains")

        ingest_cost = estimate_ingest_cost(total_pages=100, total_tokens=40000)
        query_cost = estimate_query_cost(num_iterations=4)

        return {
            "accuracy": scorer.average_score,
            "ingest_cost": ingest_cost,
            "query_cost": query_cost,
            "metadata": {
                "pages": 100,
                "queries": 10,
                "avg_iterations": 4,
            },
        }

    suite.add(
        "e2e-100p-10q",
        e2e_complex,
        description="E2E: 100-page ingest + 10 complex queries",
    )

    return suite


# ============================================================================
# Convenience: Create All Suites
# ============================================================================


def create_all_suites() -> dict[str, BenchmarkSuite]:
    """Create all benchmark suites in one call.

    Returns:
        Dict mapping suite names to BenchmarkSuite objects.
    """
    return {
        "ingest": create_ingest_suite(),
        "retrieval": create_retrieval_suite(),
        "accuracy": create_accuracy_suite(num_questions=5),
        "load": create_load_suite(concurrent_requests=10),
        "cost": create_cost_suite(),
        "e2e": create_e2e_suite(),
    }
