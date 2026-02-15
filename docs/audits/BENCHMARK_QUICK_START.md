# Phase 5 Benchmark Quick Start

## Run All Phase 5 Benchmarks

```bash
# All benchmark tests (90 tests)
python -m pytest tests/test_benchmarks.py tests/test_benchmark_integration.py -v

# Quick run
python -m pytest tests/test_benchmarks.py tests/test_benchmark_integration.py -q
```

## Run Specific Benchmark Suites

```bash
# Ingest benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_ingest_suite -v

# Retrieval benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_retrieval_suite -v

# Accuracy benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_accuracy_suite -v

# Load benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_load_suite -v

# Cost benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_cost_suite -v

# E2E benchmarks
python -m pytest tests/test_benchmark_integration.py::TestBenchmarkSuiteExecution::test_run_e2e_suite -v
```

## Use Benchmark Suites in Code

```python
from src.benchmarks.benchmark_suite import create_all_suites
from src.benchmarks.benchmark_runner import run_benchmark, format_report

# Create all benchmark suites
suites = create_all_suites()

# Run ingest suite
results = run_benchmark(suites["ingest"])
print(format_report(results))

# Run retrieval suite
results = run_benchmark(suites["retrieval"])
print(format_report(results))

# Run all suites
for name, suite in suites.items():
    results = run_benchmark(suite)
    print(f"\n{name.upper()} BENCHMARKS:")
    print(format_report(results))
```

## Custom Benchmark Suite

```python
from src.benchmarks.benchmark_suite import (
    create_ingest_suite,
    create_retrieval_suite,
    create_load_suite,
)
from src.benchmarks.benchmark_runner import run_benchmark, format_report

# Create minimal suite
ingest = create_ingest_suite(include_all=False)  # Only essential tests
retrieval = create_retrieval_suite(include_all=False)

# Create with options
load = create_load_suite(concurrent_requests=20)

# Run and report
for suite in [ingest, retrieval, load]:
    results = run_benchmark(suite)
    print(format_report(results))
```

## Benchmark Metrics

Each benchmark returns:

```python
{
    "accuracy": 0.95,              # 0.0-1.0
    "latency_s": 1.234,            # seconds
    "throughput_ops_s": 100.0,     # operations per second
    "ingest_cost": 0.01,           # USD
    "query_cost": 0.005,           # USD
    "metadata": {                  # custom data
        "pages": 75,
        "tokens": 25000,
        "iterations": 2,
    }
}
```

## Test Coverage

**RED Phase (Test Definitions):**
- 14 benchmark case definitions in `tests/test_benchmarks.py`
- TestPhase5IngestBenchmarks (3 tests)
- TestPhase5RetrievalBenchmarks (3 tests)
- TestPhase5AccuracyBenchmarks (1 test)
- TestPhase5LoadBenchmarks (2 tests)
- TestPhase5CostBenchmarks (3 tests)
- TestPhase5E2EBenchmarks (2 tests)

**GREEN Phase (Implementation):**
- 27 integration tests in `tests/test_benchmark_integration.py`
- 6 factory methods in `src/benchmarks/benchmark_suite.py`
- All existing framework tests pass (63 tests)

**Total:** 90 Phase 5 tests + 427 total system tests = ALL PASSING

## Real MongoDB + LLM Integration

To run benchmarks against real MongoDB Atlas and Gemini LLM:

```bash
# Requires .env with:
# MONGODB_URI=mongodb+srv://...
# OPENAI_API_KEY=sk-...
# LLM_INGESTION_MODEL=gemini-2.0-flash

python -m pytest tests/test_real_integration.py -v -m integration
```

## Documentation

See `docs/PHASE_5_BENCHMARK_SUITE.md` for full specifications.
