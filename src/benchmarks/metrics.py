"""Benchmark metrics: latency tracking, throughput counting, accuracy scoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class LatencyTracker:
    """Context manager that measures operation latency in seconds.

    Usage::

        tracker = LatencyTracker()
        with tracker:
            do_work()
        print(tracker.elapsed_s)
    """

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float = 0.0

    def __enter__(self) -> LatencyTracker:
        self._start = time.monotonic()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        self._end = time.monotonic()

    @property
    def elapsed_s(self) -> float:
        """Elapsed time in seconds."""
        if self._end <= self._start:
            return 0.0
        return self._end - self._start

    @property
    def elapsed_ms(self) -> float:
        """Elapsed time in milliseconds."""
        return self.elapsed_s * 1000


@dataclass
class ThroughputCounter:
    """Track operations per second over a measurement window.

    Usage::

        counter = ThroughputCounter()
        counter.start()
        for item in items:
            process(item)
            counter.increment()
        counter.stop()
        print(counter.ops_per_second)
    """

    _count: int = 0
    _start_time: float = 0.0
    _end_time: float = 0.0

    def start(self) -> None:
        """Mark the start of the measurement window."""
        self._start_time = time.monotonic()
        self._count = 0

    def increment(self, n: int = 1) -> None:
        """Record *n* completed operations."""
        self._count += n

    def stop(self) -> None:
        """Mark the end of the measurement window."""
        self._end_time = time.monotonic()

    @property
    def count(self) -> int:
        return self._count

    @property
    def elapsed_s(self) -> float:
        if self._end_time <= self._start_time:
            return 0.0
        return self._end_time - self._start_time

    @property
    def ops_per_second(self) -> float:
        elapsed = self.elapsed_s
        if elapsed <= 0:
            return 0.0
        return self._count / elapsed


@dataclass
class AccuracyScorer:
    """Compare expected vs actual answers using multiple strategies.

    Supported modes:
      - exact: Case-insensitive exact match.
      - contains: Expected answer is a substring of actual.
      - semantic: Placeholder for semantic similarity (always returns 0.0).
    """

    _results: list[dict] = field(default_factory=list)

    def score(
        self,
        expected: str,
        actual: str,
        mode: str = "contains",
    ) -> float:
        """Score a single expected/actual pair.

        Returns a float between 0.0 and 1.0.
        """
        if mode == "exact":
            result = 1.0 if expected.strip().lower() == actual.strip().lower() else 0.0
        elif mode == "contains":
            result = 1.0 if expected.strip().lower() in actual.strip().lower() else 0.0
        elif mode == "semantic":
            # Placeholder -- requires an embedding model to implement properly
            result = 0.0
        else:
            result = 0.0

        self._results.append(
            {"expected": expected, "actual": actual, "mode": mode, "score": result}
        )
        return result

    @property
    def average_score(self) -> float:
        if not self._results:
            return 0.0
        return sum(r["score"] for r in self._results) / len(self._results)

    @property
    def total_scored(self) -> int:
        return len(self._results)
