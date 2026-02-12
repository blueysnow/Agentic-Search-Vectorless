"""Phase 5: Integration tests for benchmark suite execution.

Tests that the benchmark suite can be created, run, and reported on.
Uses real integration fixtures when available, skips gracefully otherwise.

Run:
    python -m pytest tests/test_benchmark_integration.py -v

Run with integration tests only:
    python -m pytest tests/test_benchmark_integration.py -v -m integration
"""

from __future__ import annotations


from src.benchmarks.benchmark_suite import (
    create_all_suites,
    create_accuracy_suite,
    create_cost_suite,
    create_e2e_suite,
    create_ingest_suite,
    create_load_suite,
    create_retrieval_suite,
)
from src.benchmarks.benchmark_runner import (
    BenchmarkResult,
    run_benchmark,
    format_report,
)


class TestBenchmarkSuiteCreation:
    """Test that all benchmark suites can be created."""

    def test_create_ingest_suite(self):
        """Ingest suite can be created with all benchmarks."""
        suite = create_ingest_suite(include_all=True)
        assert suite.name == "ingest-comprehensive"
        assert len(suite) > 0
        # At least: small, medium, large, throughput
        assert len(suite) >= 3

    def test_create_retrieval_suite(self):
        """Retrieval suite can be created with all query types."""
        suite = create_retrieval_suite(include_all=True)
        assert suite.name == "retrieval-comprehensive"
        assert len(suite) >= 2
        # Has factual and analytical queries

    def test_create_accuracy_suite(self):
        """Accuracy suite can be created."""
        suite = create_accuracy_suite(num_questions=5)
        assert "accuracy-financebench" in suite.name
        assert len(suite) == 1

    def test_create_load_suite(self):
        """Load suite can be created."""
        suite = create_load_suite(concurrent_requests=10)
        assert "load-stress" in suite.name
        assert len(suite) == 2
        # concurrent + sustained

    def test_create_cost_suite(self):
        """Cost suite can be created."""
        suite = create_cost_suite()
        assert suite.name == "cost-estimation"
        assert len(suite) >= 4
        # At least: ingest-small, ingest-large, query-simple, query-complex

    def test_create_e2e_suite(self):
        """E2E suite can be created."""
        suite = create_e2e_suite()
        assert suite.name == "e2e-full-pipeline"
        assert len(suite) >= 3
        # simple, moderate, complex

    def test_create_all_suites(self):
        """All suites can be created together."""
        suites = create_all_suites()
        assert len(suites) == 6
        assert "ingest" in suites
        assert "retrieval" in suites
        assert "accuracy" in suites
        assert "load" in suites
        assert "cost" in suites
        assert "e2e" in suites


class TestBenchmarkSuiteExecution:
    """Test running benchmark suites."""

    def test_run_ingest_suite(self):
        """Ingest suite can be run successfully."""
        suite = create_ingest_suite(include_all=False)
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) >= 1
        assert all(isinstance(r, BenchmarkResult) for r in results)
        assert all(r.latency_s >= 0 for r in results)

    def test_run_retrieval_suite(self):
        """Retrieval suite can be run successfully."""
        suite = create_retrieval_suite(include_all=False)
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) >= 1
        assert all(r.latency_s >= 0 for r in results)

    def test_run_accuracy_suite(self):
        """Accuracy suite can be run successfully."""
        suite = create_accuracy_suite(num_questions=3)
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) == 1
        assert results[0].accuracy >= 0.0
        assert results[0].accuracy <= 1.0

    def test_run_cost_suite(self):
        """Cost suite can be run successfully."""
        suite = create_cost_suite()
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) >= 4
        # Check that costs are positive where expected
        for r in results:
            if "ingest" in r.name:
                assert r.ingest_cost >= 0
            if "query" in r.name:
                assert r.query_cost >= 0

    def test_run_load_suite(self):
        """Load suite can be run successfully."""
        suite = create_load_suite(concurrent_requests=5)
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) >= 2
        for r in results:
            assert r.throughput_ops_s >= 0

    def test_run_e2e_suite(self):
        """E2E suite can be run successfully."""
        suite = create_e2e_suite()
        results = run_benchmark(suite, skip_if_no_services=False)

        assert len(results) >= 2
        for r in results:
            assert r.latency_s >= 0
            assert r.accuracy >= 0
            assert r.ingest_cost >= 0
            assert r.query_cost >= 0


class TestBenchmarkReporting:
    """Test benchmark reporting."""

    def test_report_format_ingest_suite(self):
        """Ingest suite results can be formatted into a report."""
        suite = create_ingest_suite(include_all=False)
        results = run_benchmark(suite, skip_if_no_services=False)
        report = format_report(results)

        assert "BENCHMARK REPORT" in report
        assert len(results) > 0
        for r in results:
            assert r.name in report or "Total:" in report

    def test_report_format_comprehensive(self):
        """Comprehensive report includes all metrics."""
        suite = create_cost_suite()
        results = run_benchmark(suite, skip_if_no_services=False)
        report = format_report(results)

        assert "BENCHMARK REPORT" in report
        # Should mention costs for cost suite
        if any(r.ingest_cost > 0 for r in results):
            assert "Ingest $" in report
        if any(r.query_cost > 0 for r in results):
            assert "Query $" in report

    def test_report_includes_summary(self):
        """Report includes summary statistics."""
        suite = create_load_suite(concurrent_requests=3)
        results = run_benchmark(suite, skip_if_no_services=False)
        report = format_report(results)

        assert "Total:" in report
        assert "Passed:" in report or "Average latency:" in report


class TestBenchmarkSuiteOptions:
    """Test suite configuration options."""

    def test_ingest_suite_minimal(self):
        """Ingest suite can be created minimally."""
        suite = create_ingest_suite(include_all=False)
        assert len(suite) >= 1
        # At least the small ingest test

    def test_ingest_suite_full(self):
        """Ingest suite full mode includes more benchmarks."""
        suite_minimal = create_ingest_suite(include_all=False)
        suite_full = create_ingest_suite(include_all=True)

        assert len(suite_full) > len(suite_minimal)

    def test_retrieval_suite_minimal(self):
        """Retrieval suite can be created minimally."""
        suite = create_retrieval_suite(include_all=False)
        assert len(suite) >= 1

    def test_retrieval_suite_full(self):
        """Retrieval suite full mode includes more query types."""
        suite_minimal = create_retrieval_suite(include_all=False)
        suite_full = create_retrieval_suite(include_all=True)

        assert len(suite_full) > len(suite_minimal)

    def test_accuracy_suite_configurable_questions(self):
        """Accuracy suite respects num_questions parameter."""
        suite_3 = create_accuracy_suite(num_questions=3)
        suite_10 = create_accuracy_suite(num_questions=10)

        # Both should have 1 benchmark case, but metadata will differ
        assert len(suite_3) == 1
        assert len(suite_10) == 1
        assert "3" in suite_3.name
        assert "10" in suite_10.name

    def test_load_suite_configurable_concurrency(self):
        """Load suite respects concurrent_requests parameter."""
        suite_5 = create_load_suite(concurrent_requests=5)
        suite_20 = create_load_suite(concurrent_requests=20)

        assert "5" in suite_5.name
        assert "20" in suite_20.name


class TestBenchmarkMetadata:
    """Test that benchmark results include proper metadata."""

    def test_ingest_metadata(self):
        """Ingest benchmark results include document metadata."""
        suite = create_ingest_suite(include_all=True)
        results = run_benchmark(suite, skip_if_no_services=False)

        for r in results:
            assert r.metadata is not None
            # Should have pages/tokens info
            if "pages" in r.metadata or "tokens" in r.metadata:
                assert isinstance(r.metadata, dict)

    def test_cost_metadata(self):
        """Cost benchmark results include formatted cost."""
        suite = create_cost_suite()
        results = run_benchmark(suite, skip_if_no_services=False)

        for r in results:
            if "cost_formatted" in r.metadata:
                assert "$" in str(r.metadata["cost_formatted"])

    def test_load_metadata(self):
        """Load benchmark results include throughput metadata."""
        suite = create_load_suite(concurrent_requests=5)
        results = run_benchmark(suite, skip_if_no_services=False)

        for r in results:
            if r.throughput_ops_s > 0:
                assert (
                    "concurrent_requests" in r.metadata
                    or "total_requests" in r.metadata
                )


class TestBenchmarkErrorHandling:
    """Test error handling in benchmark suites."""

    def test_suite_with_failing_benchmark(self):
        """Suite gracefully handles a failing benchmark."""
        from src.benchmarks.benchmark_runner import BenchmarkSuite

        suite = BenchmarkSuite(name="test-failing")

        def failing_bench():
            raise RuntimeError("Benchmark error")

        suite.add("failing-case", failing_bench)

        results = run_benchmark(suite, skip_if_no_services=False)
        assert len(results) == 1
        # FIX #2: Error now includes exception type (RuntimeError: message)
        assert "RuntimeError" in results[0].error
        assert "Benchmark error" in results[0].error
        assert results[0].latency_s >= 0

    def test_suite_with_mixed_results(self):
        """Suite handles mix of passing and failing benchmarks."""
        from src.benchmarks.benchmark_runner import BenchmarkSuite

        suite = BenchmarkSuite(name="test-mixed")

        suite.add("good", lambda: {"accuracy": 0.95})
        suite.add("bad", lambda: {"error": "intentional"})

        results = run_benchmark(suite, skip_if_no_services=False)
        assert len(results) == 2
        # First should pass, second depends on exception handling
