"""Benchmark runner: define, execute, and report benchmark suites."""

from __future__ import annotations

import structlog
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from src.benchmarks.metrics import LatencyTracker

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark execution."""

    name: str
    latency_s: float = 0.0
    accuracy: float = 0.0
    throughput_ops_s: float = 0.0
    ingest_cost: float = 0.0
    query_cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    error: str = ""


@dataclass
class BenchmarkCase:
    """A single benchmark definition."""

    name: str
    fn: Callable[[], dict[str, Any]]
    description: str = ""


class BenchmarkSuite:
    """A collection of benchmark cases."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._cases: list[BenchmarkCase] = []

    def add(
        self, name: str, fn: Callable[[], dict[str, Any]], description: str = ""
    ) -> None:
        """Register a benchmark case."""
        self._cases.append(BenchmarkCase(name=name, fn=fn, description=description))

    @property
    def cases(self) -> list[BenchmarkCase]:
        return list(self._cases)

    def __len__(self) -> int:
        return len(self._cases)


def _check_services_available() -> bool:
    """Check if MongoDB and LLM services are reachable.

    Returns False if either is unavailable, allowing benchmarks to be skipped.

    FIX #1: Differentiates exception types and logs config errors at WARNING level.
    """
    try:
        from src.db.client import get_client

        client = get_client()
        client.admin.command("ping")
    except TimeoutError as exc:
        # Network timeout - transient issue, log at WARNING
        logger.warning(
            "service_check_failed",
            component="mongodb",
            error_type=type(exc).__name__,
            error_message=str(exc),
            note="Connection timeout - check network connectivity",
        )
        return False
    except (ValueError, KeyError) as exc:
        # Configuration error - config issue, log at ERROR
        logger.error(
            "service_check_failed",
            component="mongodb",
            error_type=type(exc).__name__,
            error_message=str(exc),
            note="Configuration error - check MongoDB URI format",
        )
        return False
    except Exception as exc:
        # Other failures (auth, etc) - log at WARNING with type
        logger.warning(
            "service_check_failed",
            component="mongodb",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return False

    try:
        from src.config import get_settings

        settings = get_settings()
        if not settings.anthropic_api_key and not settings.openai_api_key:
            logger.info(
                "service_check_skipped",
                component="llm_config",
                reason="No LLM API keys configured (optional)",
            )
            return False
    except (ValueError, KeyError) as exc:
        # Configuration parsing error
        logger.error(
            "service_check_failed",
            component="llm_config",
            error_type=type(exc).__name__,
            error_message=str(exc),
            note="Configuration error - check .env or settings",
        )
        return False
    except Exception as exc:
        # Other failures
        logger.warning(
            "service_check_failed",
            component="llm_config",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return False

    return True


def run_benchmark(
    suite: BenchmarkSuite,
    *,
    skip_if_no_services: bool = True,
) -> list[BenchmarkResult]:
    """Execute all benchmarks in a suite.

    Args:
        suite: The benchmark suite to run.
        skip_if_no_services: If True, skip benchmarks when MongoDB/LLM are unavailable.

    Returns:
        List of BenchmarkResult objects.
    """
    results: list[BenchmarkResult] = []

    if skip_if_no_services and not _check_services_available():
        logger.info("benchmark_skipped_no_services", suite=suite.name)
        for case in suite.cases:
            results.append(
                BenchmarkResult(
                    name=case.name,
                    skipped=True,
                    error="Services unavailable (MongoDB or LLM)",
                )
            )
        return results

    for case in suite.cases:
        logger.info("benchmark_running", name=case.name)
        tracker = LatencyTracker()
        try:
            with tracker:
                output = case.fn()

            # FIX #3: Validate output structure before extracting values
            if not isinstance(output, dict):
                error_msg = (
                    f"Benchmark output must be dict, got {type(output).__name__}"
                )
                logger.error(
                    "benchmark_failed",
                    name=case.name,
                    reason="invalid_output_type",
                    error_type=type(output).__name__,
                    latency_s=tracker.elapsed_s,
                )
                result = BenchmarkResult(
                    name=case.name,
                    latency_s=tracker.elapsed_s,
                    error=error_msg,
                )
                results.append(result)
                continue

            # Check for required/optional keys and warn on missing
            required_keys = [
                "accuracy",
                "latency_s",
                "throughput_ops_s",
                "ingest_cost",
                "query_cost",
            ]
            missing_keys = [k for k in required_keys if k not in output]
            if missing_keys:
                logger.warning(
                    "benchmark_incomplete_output",
                    name=case.name,
                    missing_keys=missing_keys,
                    note="Missing keys will default to 0.0",
                )

            # Validate value ranges
            accuracy = output.get("accuracy", 0.0)
            if not (0.0 <= accuracy <= 1.0):
                logger.warning(
                    "benchmark_invalid_value",
                    name=case.name,
                    field="accuracy",
                    value=accuracy,
                    note="Expected 0.0-1.0 range",
                )

            throughput = output.get("throughput_ops_s", 0.0)
            if throughput < 0:
                logger.warning(
                    "benchmark_invalid_value",
                    name=case.name,
                    field="throughput_ops_s",
                    value=throughput,
                    note="Expected >= 0.0",
                )

            result = BenchmarkResult(
                name=case.name,
                latency_s=tracker.elapsed_s,
                accuracy=accuracy,
                throughput_ops_s=throughput,
                ingest_cost=output.get("ingest_cost", 0.0),
                query_cost=output.get("query_cost", 0.0),
                metadata=output.get("metadata", {}),
            )
            logger.info(
                "benchmark_completed", name=case.name, latency_s=tracker.elapsed_s
            )
        except Exception as exc:
            # FIX #2: Capture exception type + traceback, not just message
            exc_type = type(exc).__name__
            exc_traceback = traceback.format_exc()
            error_msg = f"{exc_type}: {str(exc)}"

            result = BenchmarkResult(
                name=case.name,
                latency_s=tracker.elapsed_s,
                error=error_msg,
            )
            logger.error(
                "benchmark_failed",
                name=case.name,
                error_type=exc_type,
                error_message=str(exc),
                traceback=exc_traceback,
                latency_s=tracker.elapsed_s,
            )

        results.append(result)

    return results


def format_report(results: list[BenchmarkResult]) -> str:
    """Generate a human-readable benchmark report.

    Args:
        results: List of BenchmarkResult from run_benchmark.

    Returns:
        Formatted report string.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("BENCHMARK REPORT")
    lines.append("=" * 60)

    for r in results:
        lines.append("")
        lines.append(f"--- {r.name} ---")
        if r.skipped:
            lines.append(f"  SKIPPED: {r.error}")
            continue
        if r.error:
            lines.append(f"  FAILED: {r.error}")
            lines.append(f"  Latency: {r.latency_s:.3f}s")
            continue

        lines.append(f"  Latency:    {r.latency_s:.3f}s")
        if r.accuracy > 0:
            lines.append(f"  Accuracy:   {r.accuracy:.2%}")
        if r.throughput_ops_s > 0:
            lines.append(f"  Throughput: {r.throughput_ops_s:.1f} ops/s")
        if r.ingest_cost > 0:
            lines.append(f"  Ingest $:   ${r.ingest_cost:.4f}")
        if r.query_cost > 0:
            lines.append(f"  Query $:    ${r.query_cost:.4f}")
        if r.metadata:
            for k, v in r.metadata.items():
                lines.append(f"  {k}: {v}")

    lines.append("")
    lines.append("=" * 60)

    # Summary
    completed = [r for r in results if not r.skipped and not r.error]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if r.error and not r.skipped]
    lines.append(
        f"Total: {len(results)} | Passed: {len(completed)} | Failed: {len(failed)} | Skipped: {len(skipped)}"
    )
    if completed:
        avg_latency = sum(r.latency_s for r in completed) / len(completed)
        lines.append(f"Average latency: {avg_latency:.3f}s")
    lines.append("=" * 60)

    return "\n".join(lines)
