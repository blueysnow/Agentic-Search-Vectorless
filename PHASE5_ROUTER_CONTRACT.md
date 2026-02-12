# Phase 5 Router Contract - Silent Failure Audit
## Task #6: CC100X Hunter

**Audit Date:** 2026-02-12
**Auditor:** hunter
**Status:** COMPLETE

---

## ROUTER CONTRACT

```json
{
  "task_id": 6,
  "task_name": "CC100X hunter: Silent failure audit on Phase 5",
  "status": "COMPLETE",
  "contract": {
    "STATUS": "FAIL",
    "CRITICAL_ISSUES": 3,
    "BLOCKING": true,
    "REQUIRES_REMEDIATION": true,
    "DEPLOYMENT_RECOMMENDATION": "DO_NOT_DEPLOY",
    "SEVERITY": "CRITICAL"
  },
  "findings": {
    "empty_exception_handlers": 0,
    "log_only_failures": 2,
    "generic_error_messages": 1,
    "swallowed_exceptions": 2,
    "partial_test_coverage": 5,
    "total_issues": 10
  }
}
```

---

## CRITICAL ISSUES (3)

### Issue #1: Service Check Silently Masks Root Causes
**File:** `src/benchmarks/benchmark_runner.py:67-78`
**Type:** Log-only failure + Swallowed exception
**Severity:** CRITICAL (HIGH)

**Evidence:**
```python
try:
    from src.db.client import get_client
    client = get_client()
    client.admin.command("ping")
except Exception as exc:
    logger.debug("service_check_failed", component="mongodb", error=str(exc))  # ← DEBUG only
    return False  # ← Silently returns without context

try:
    from src.config import get_settings
    settings = get_settings()
    if not settings.anthropic_api_key and not settings.openai_api_key:
        return False
except Exception as exc:
    logger.debug("service_check_failed", component="llm_config", error=str(exc))  # ← DEBUG only
    return False
```

**Problem:**
- Uses DEBUG log level (invisible in production)
- Bare `Exception` catches hide error types
- No distinction between network (transient) vs config (fatal) failures
- Benchmarks skip silently with generic "Services unavailable" message

**Impact:** Production benchmarks appear to pass when services are actually down or misconfigured.

---

### Issue #2: Generic Error Messages Prevent Debugging
**File:** `src/benchmarks/benchmark_runner.py:126-132`
**Type:** Generic error message + Swallowed exception details
**Severity:** CRITICAL (MEDIUM-HIGH)

**Evidence:**
```python
except Exception as exc:
    result = BenchmarkResult(
        name=case.name,
        latency_s=tracker.elapsed_s,
        error=str(exc),  # ← Only string conversion, no type info
    )
    logger.error("benchmark_failed", name=case.name, error=str(exc))  # ← Same opaque error
```

**Problem:**
- Stores only exception string representation without type
- No traceback captured
- Custom exceptions may produce unhelpful strings
- `str(exc)` can be truncated or produce "None"

**Impact:** Downstream consumers (dashboards, reports, alerting) receive opaque error messages. Post-mortem analysis impossible without re-running failed benchmarks.

---

### Issue #3: No Validation of Benchmark Output Structure
**File:** `src/benchmarks/benchmark_runner.py:119-123`
**Type:** Partial test coverage + Data integrity gap
**Severity:** CRITICAL (MEDIUM)

**Evidence:**
```python
output = case.fn()  # ← No type checking

result = BenchmarkResult(
    name=case.name,
    latency_s=tracker.elapsed_s,
    accuracy=output.get("accuracy", 0.0),  # ← Assumes dict; crashes if None/string
    throughput_ops_s=output.get("throughput_ops_s", 0.0),
    ingest_cost=output.get("ingest_cost", 0.0),
    query_cost=output.get("query_cost", 0.0),
    metadata=output.get("metadata", {}),
)
```

**Problem:**
- No assertion that `output` is a dict
- If callable returns `None`, `.get()` raises `AttributeError` (caught as generic error)
- If callable returns incomplete dict, missing fields silently become 0.0
- No way to distinguish "benchmark broken" from "benchmark returned zero"

**Example Failure:**
```python
def buggy_benchmark():
    pass  # Returns None

# Result: error="'NoneType' object has no attribute 'get'"
# But no indication this is a contract violation
```

**Impact:** Buggy benchmarks appear as failed-but-normal errors in reports. Data integrity issues masked by silent defaults (0.0).

---

## ADDITIONAL ISSUES (7)

### Issue #4: Config Validation Not Explicitly Handled
**File:** `src/benchmarks/benchmark_runner.py:71-75`
**Type:** Log-only failure
**Severity:** MEDIUM

Missing API keys treated same as service unavailability. Ops confusion: is service down or config missing?

---

### Issue #5: No Exception Type Tracking in Tests
**File:** `tests/test_benchmarks.py:433-445`
**Type:** Partial test coverage
**Severity:** MEDIUM

Test only verifies `error == "benchmark exploded"` string. Doesn't validate exception type capture or traceback info.

---

### Issue #6: Service Check Not Unit Tested
**File:** `tests/test_benchmarks.py` (entire file)
**Type:** Partial test coverage
**Severity:** MEDIUM

`_check_services_available()` function not directly tested. Tests mock it with boolean return, never test actual exception paths.

---

### Issue #7: No Malformed Input Tests
**File:** `tests/test_benchmarks.py`
**Type:** Partial test coverage
**Severity:** MEDIUM

No test for benchmarks returning None, string, or incomplete dict. No test for output validation enforcement.

---

### Issue #8: No Error Aggregation Tests
**File:** `tests/test_benchmark_integration.py:287-299`
**Type:** Partial test coverage
**Severity:** MEDIUM

Test verifies mixed results exist but doesn't validate that error details are preserved for each failure.

---

### Issue #9: Generic Exception in Format Report
**File:** `src/benchmarks/benchmark_runner.py:181-183`
**Type:** Log-only failure
**Severity:** LOW-MEDIUM

Error classification only checks string field, not exception type. Can't distinguish error categories.

```python
completed = [r for r in results if not r.skipped and not r.error]
skipped = [r for r in results if r.skipped]
failed = [r for r in results if r.error and not r.skipped]
```

---

### Issue #10: No Timeout Handling in Metrics
**File:** `src/benchmarks/metrics.py`
**Type:** Partial test coverage
**Severity:** LOW-MEDIUM

`LatencyTracker` and `ThroughputCounter` have no timeout protection. No guard against zero-division in edge cases.

---

## ROUTER CONTRACT VIOLATIONS

### 1. Explicit Error Handling Contract
```
REQUIREMENT: Exceptions must be distinguished by type for proper categorization.
STATUS: ❌ VIOLATED
EVIDENCE: benchmark_runner.py:67, 76, 126
IMPACT: Cannot distinguish network failures from config errors from logic errors
```

### 2. Observability Contract
```
REQUIREMENT: Error details (type, message, traceback) must be captured for post-mortem analysis.
STATUS: ❌ VIOLATED
EVIDENCE: benchmark_runner.py:130 (only str(exc) stored)
IMPACT: Impossible to debug failures without re-running
```

### 3. Data Integrity Contract
```
REQUIREMENT: Input/output structures must be validated before processing.
STATUS: ❌ VIOLATED
EVIDENCE: benchmark_runner.py:114 (no output type check)
IMPACT: Buggy benchmarks appear as normal errors; data loss masked by 0.0 defaults
```

### 4. Test Coverage Contract
```
REQUIREMENT: Error paths must have explicit test coverage.
STATUS: ❌ VIOLATED
EVIDENCE: tests/test_benchmarks.py (5 gaps identified)
IMPACT: New error scenarios break without test failure detection
```

---

## REMEDIATION REQUIRED

### Priority 1 - BLOCKING (Fix Before Deployment)

**1A. Differentiate Exception Types in Service Check**
```python
# Current (broken):
except Exception as exc:
    logger.debug(...)
    return False

# Required:
except ConnectionError as exc:
    logger.warning(...)
    return False
except ConfigError as exc:
    logger.error(...)
    raise  # Fail fast
```

**1B. Validate Benchmark Output Structure**
```python
# Current (broken):
output = case.fn()
accuracy=output.get("accuracy", 0.0)

# Required:
output = case.fn()
assert isinstance(output, dict), f"Benchmark {case.name} returned {type(output)}, expected dict"
assert "accuracy" in output, f"Benchmark {case.name} missing required 'accuracy' field"
```

**1C. Capture Exception Type Information**
```python
# Current (broken):
error=str(exc)

# Required:
error=f"{type(exc).__name__}: {str(exc)}"
```

### Priority 2 - IMPORTANT (Fix Before Next Release)

- Add unit tests for `_check_services_available()` exception paths
- Add tests for malformed benchmark output (None, string, incomplete dict)
- Add tests for error type capture in results
- Upgrade DEBUG logs to WARNING in service checks

### Priority 3 - NICE-TO-HAVE

- Add retry logic for transient failures (ConnectionError)
- Add metrics tracking for failure types
- Add runbook for ops: "benchmark skipped" vs "benchmark failed"

---

## SUMMARY

**Phase 5 benchmark code has CRITICAL silent failure patterns:**

1. Service checks mask root causes (network vs config) - BLOCKING
2. Generic error messages prevent debugging - BLOCKING
3. No output validation allows buggy benchmarks to pass - BLOCKING

**All 3 issues violate Router Contracts required for production deployment.**

---

## CONCLUSION

```
DEPLOYMENT_DECISION: DO_NOT_DEPLOY
BLOCKING_ISSUES: 3 critical findings
REMEDIATION_EFFORT: 2-3 hours for Priority 1 fixes
RISK_IF_DEPLOYED: HIGH - Silent failures in production benchmarking

NEXT_STEPS:
1. Builder team addresses Priority 1 fixes
2. Quality team adds test coverage
3. Security team reviews updated error handling
4. Re-run audit after fixes (Task #6 redux)
5. Then proceed with deployment approval
```

---

**Audit Report:** `/Users/rom.iluz/Dev/agentic-search-mongo/PHASE5_SILENT_FAILURE_AUDIT.md`
**Router Contract:** This file
**Status:** COMPLETE - Awaiting remediation team assignment
