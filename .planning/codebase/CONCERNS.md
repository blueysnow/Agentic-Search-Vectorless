# Codebase Concerns

**Analysis Date:** 2026-02-17

## Tech Debt

**Benchmark Output Validation (High Priority):**
- Issue: Multiple TODO comments in `tests/test_benchmarks.py` indicate incomplete error validation. Benchmark error handling was partially implemented but specific error type verification is missing.
- Files: `src/benchmarks/benchmark_runner.py` (lines 171-227), `tests/test_benchmarks.py` (lines 1100-1222)
- Impact: Error messages may not include exception types, tracebacks, or line numbers, making it hard to debug benchmark failures. Tests verify errors exist but don't validate content (e.g., "ValueError" vs generic message).
- Fix approach: Complete the error validation test assertions by checking that exception types, function names, and traceback frames are included in error messages. Update `BenchmarkResult.error` to always include type and traceback info.

**Incomplete Benchmark Output Type Validation (Medium Priority):**
- Issue: When benchmarks return None or non-dict outputs, silent defaults (0.0) are used instead of failing clearly.
- Files: `src/benchmarks/benchmark_runner.py` (lines 169-189)
- Impact: Broken benchmarks may report success with 0.0 accuracy silently, hiding the actual failure.
- Fix approach: Check if output is None before validation (line 169). Add explicit error if output is None or empty dict.

**Broad Exception Catching (Medium Priority):**
- Issue: Multiple locations catch bare `Exception` without re-raising non-recoverable errors.
- Files: `src/db/client.py` (line 44), `src/retrieval/pipeline.py` (line 320), `src/db/indexes.py` (line 187), `src/retrieval/tree_navigator.py` (line 140)
- Impact: Critical failures may be silently logged instead of propagated, making errors harder to track.
- Fix approach: Use specific exception types. For example, in `db/client.py`, catch ConnectionFailure separately from other exceptions. Re-raise non-recoverable errors or log at ERROR level, not WARNING.

**Silent Fallbacks Returning Empty Results (Medium Priority):**
- Issue: Multiple retrieval functions return empty lists `[]` on error instead of raising exceptions or returning meaningful error states.
- Files: `src/retrieval/atlas_search.py` (lines 284, 344), `src/retrieval/tree_navigator.py` (lines 142, 147, 151, 182)
- Impact: When Atlas Search or tree navigation fails silently, the retrieval pipeline gets no candidates and may return "answer not found" instead of reporting the actual failure.
- Fix approach: Distinguish between "no results found" (return []) and "search failed" (raise exception). Return error objects with failure reason instead of empty arrays.

## Known Bugs

**SSE Stream Citation Data Incomplete:**
- Symptoms: Page citation data in stream response uses placeholder values.
- Files: `src/api/routes/stream.py` (lines 176-185)
- Trigger: Any query that produces results will emit citations with `page: 0` and generic text.
- Workaround: Frontend could load actual page info separately, but this data should come from retrieval results.
- Impact: User cannot easily navigate to the exact page in the cited section.
- Fix: Extract page ranges from node metadata in `RetrievalResult.trace` and pass actual page numbers to citation events.

**Timeout Event in Content Loader Not Fully Handled:**
- Symptoms: When content loader timeout occurs (10s), incomplete data is returned to reasoning loop.
- Files: `src/retrieval/content_loader.py` (lines 181-194)
- Trigger: Large documents with slow MongoDB queries when loading 5+ candidates in parallel.
- Workaround: None - reasoning loop receives partial results.
- Impact: The reasoning loop may make decisions based on incomplete content, leading to incorrect answers.
- Fix: Add timeout handling that either retries with fewer workers or raises an exception to trigger deeper navigation instead.

## Security Considerations

**Configuration Secrets in Environment (Standard Practice):**
- Risk: `.env` file contains API keys (Anthropic, OpenAI, MongoDB URI).
- Files: `.env` (not committed, only `.env.example` in repo)
- Current mitigation: `.env` is in `.gitignore`. `.env.example` has placeholder values.
- Recommendations: Verify `.env` is never accidentally committed. Use read-only file permissions in production. Consider vault-based secret management for cloud deployments.

**API Key Validation in LLM Provider:**
- Risk: Invalid API keys are only caught at runtime during first call, not at startup.
- Files: `src/llm/provider.py` (lines 105-131)
- Current mitigation: `_check_services_available()` in benchmark runner validates keys before running tests.
- Recommendations: Add explicit API key format validation in config module at startup. Log a clear error if keys are missing or malformed.

**MongoDB Query Injection Risk (Low Risk):**
- Risk: Document IDs and node IDs are passed directly to MongoDB queries.
- Files: `src/retrieval/pipeline.py` (line 73), `src/retrieval/content_loader.py` (various)
- Current mitigation: MongoDB driver escapes strings; IDs are stored in typed fields.
- Recommendations: Continue using parameterized queries only. Never construct MongoDB query strings manually.

## Performance Bottlenecks

**Content Loader Thread Pool Timeout (10s total for 5 workers):**
- Problem: ThreadPoolExecutor waits up to 10 seconds for all content loads to complete. With 5 workers and network delays, some large nodes may timeout.
- Files: `src/retrieval/content_loader.py` (lines 17-18, 176-194)
- Cause: Fixed 10s timeout doesn't scale with document size or network latency. Per-node timeout might be more appropriate.
- Current settings: 5 workers, 10s total timeout (avg 2s per node).
- Improvement path: (1) Increase timeout to 20s with configurable setting, (2) use per-task timeout instead of pool timeout, (3) implement adaptive timeout based on node size, (4) add partial result handling.

**Exponential Backoff Max Delay Hardcoded (60s):**
- Problem: LLM provider retries with max 60s delay between attempts. With 10 retries, worst case is ~10 minutes of backoff.
- Files: `src/llm/provider.py` (lines 17-19)
- Cause: Conservative retry strategy needed for rate limits, but no differentiation between rate limit (should retry) and transient network failure (could retry faster).
- Impact: Rate-limited queries block the request thread for extended periods.
- Improvement path: Implement exponential backoff with jitter tuning. Add configuration option. Consider circuit breaker pattern for repeated failures.

**Database Connection Pool Limited (50 connections):**
- Problem: Fixed pool size of 50 connections may be insufficient for high-concurrency retrieval scenarios or bottlenecking for parallel benchmark runs.
- Files: `src/db/client.py` (line 21)
- Cause: Default chosen without load testing.
- Impact: Connection queueing delays under 50+ concurrent requests.
- Improvement path: Load test with expected concurrency. Make configurable via environment variable. Monitor connection pool saturation in production.

**Synchronous PDF Parsing in Async Pipeline:**
- Problem: PDF parsing with PyMuPDF/pypdf is synchronous, blocking the async ingestion pipeline.
- Files: `src/ingestion/parsers/pdf_parser.py` (not examined, but likely blocking)
- Impact: Large PDF parsing can block event loop, delaying concurrent ingestion tasks.
- Improvement path: Use `asyncio.to_thread()` for PDF parsing operations, or implement streaming parser for very large files.

## Fragile Areas

**Tree Navigation Reasoning Loop (5 iterations max):**
- Files: `src/retrieval/tree_navigator.py` (lines 110-195), `src/retrieval/pipeline.py` (lines 180-290)
- Why fragile: LLM reasoning loop is brittle if LLM doesn't follow the expected output format. JSON parsing failures return empty results silently.
- Safe modification: (1) Add stricter format validation with helpful error messages, (2) implement fallback if LLM output is malformed, (3) add logging for format violations to track reasoning issues.
- Test coverage: `tests/test_benchmarks.py` has some coverage but E2E tree navigation tests are needed. Query behavior with large trees isn't tested.
- Risk: Poorly formatted LLM responses cause silent navigation failures.

**Session Persistence Swallows Errors:**
- Files: `src/retrieval/pipeline.py` (lines 320-323)
- Why fragile: MongoDB write failures during session persistence are caught and logged but not raised. User won't know session wasn't saved.
- Safe modification: (1) Separate session tracking from retrieval response, (2) return session_id even if persistence fails, (3) add explicit error to response if session persistence fails.
- Test coverage: No tests for session persistence failure scenarios.

**Search Backend Detection at Startup:**
- Files: `src/retrieval/atlas_search.py` (lines 32-34)
- Why fragile: `_search_backend` is a module-level variable set once at startup. If Atlas Search becomes unavailable after startup, fallback won't be triggered.
- Safe modification: Implement dynamic backend detection per-request or add health check endpoint that tests search index availability.
- Test coverage: Detection logic is tested but runtime fallback isn't.

**JSON Extraction Utility (Silent Failures):**
- Files: `src/utils/json_utils.py` (line 52)
- Why fragile: `json.JSONDecodeError` is caught with `pass`, then Python literal cleanup is attempted. If both fail, `None` is returned silently.
- Safe modification: (1) Log when JSON parsing fails with the raw content (for debugging), (2) raise exception instead of returning None if all parsing fails, (3) add strict mode flag.
- Impact: LLM responses with malformed JSON produce `None` with no indication of what went wrong.

## Scaling Limits

**MongoDB Tree Query Performance (Materialized Path Lookups):**
- Current capacity: Efficient for documents up to ~10,000 nodes (typical 200-page PDF = 100-500 nodes).
- Limit: Materialized path string grows with depth. Very deep trees (50+ levels) may slow substring queries.
- Scaling path: (1) Add compound index on (documentId, materializedPath) for faster ancestor lookups, (2) consider hierarchical path encoding (e.g., array of IDs), (3) benchmark with 50k+ node documents.

**Concurrent Ingestion (Limited by LLM API Rate Limits):**
- Current capacity: ~5-10 concurrent document ingestions (limited by Anthropic/OpenAI rate limits).
- Limit: Each document requires multiple LLM calls (tree generation, summarization, verification). Rate limit queuing blocks all ingestions.
- Scaling path: (1) Implement queue-based ingestion with configurable concurrency, (2) add batch request support if API provides it, (3) use cheaper model for summarization/classification steps.

**Memory Usage for Large Documents:**
- Current capacity: Single 500-page document can require ~100-200MB for tree in memory during ingestion (token counting, tree building).
- Limit: Very large documents (2000+ pages) may exceed container memory limits.
- Scaling path: (1) Stream-process pages instead of loading all at once, (2) implement pagination for tree building, (3) move token counting to async background task.

**Frontend Real-time Message Rendering:**
- Current capacity: Streaming response with 100+ citations per response.
- Limit: SSE events are sent individually; high-frequency events may cause frontend rendering lag.
- Scaling path: Batch citation events, throttle thinking updates, or use WebSocket for better bidirectional control.

## Dependencies at Risk

**PyMuPDF (fitz) -- Windows/macOS Licensing Uncertainty:**
- Risk: PyMuPDF uses AGPL-licensed code (Tesseract). Commercial use may require licensing.
- Impact: If license terms change, PDF parsing may become unavailable without license purchase.
- Current mitigation: pypdf is available as fallback, but PyMuPDF is preferred for performance.
- Migration plan: Ensure pypdf can fully replace PyMuPDF. Test text extraction accuracy with pypdf as backup. Review license terms before production deployment.

**Anthropic/OpenAI API Dependency (No Local Fallback):**
- Risk: No fallback LLM provider if Anthropic/OpenAI APIs become unavailable.
- Impact: Retrieval pipeline completely blocked if both APIs fail.
- Current mitigation: Configurable provider selection between Anthropic and OpenAI.
- Migration plan: Add support for local LLM (Ollama or similar) or another provider (Together.ai, Replicate). Test fallback switching.

**MongoDB Atlas Search (Depends on Mongot Service):**
- Risk: Atlas Search requires mongot service to be running. Community Edition has limited search support.
- Impact: Search quality degrades significantly without proper indexes.
- Current mitigation: Fallback to $text indexes if Atlas Search unavailable.
- Migration plan: Ensure $text fallback works correctly (already implemented in `atlas_search.py`). Consider self-managed MongoDB with Mongot for non-Atlas deployments.

## Missing Critical Features

**Batch Ingestion Queue:**
- Problem: No way to queue multiple documents for parallel ingestion. Single-document API blocks on LLM operations.
- Blocks: Multi-document upload workflow, bulk ingestion from data sources.
- Solution: Add async job queue (Celery/Temporal) for ingestion tasks with progress tracking.

**Result Pagination for Large Retrieval Results:**
- Problem: Tree navigation may collect 50+ candidate nodes, but all are loaded into memory.
- Blocks: Handling queries that match many sections.
- Solution: Implement candidate pagination in reasoning loop. Load candidates lazily as reasoning progresses.

**Cost Tracking per Document/Query:**
- Problem: Cost estimates in benchmarks, but actual per-request costs not tracked in production.
- Blocks: Billing, usage monitoring, cost optimization.
- Solution: Log actual token counts per LLM call. Aggregate costs per session/document.

## Test Coverage Gaps

**Retrieval Pipeline Error Handling:**
- What's not tested: Query timeouts, partial content load failures, LLM response parsing failures.
- Files: `src/retrieval/pipeline.py`, `src/retrieval/tree_navigator.py`
- Risk: Error paths may not work as intended, causing unexpected failures in production.
- Priority: **High** - core functionality.

**MongoDB Bulk Operations:**
- What's not tested: Batch inserts of 1000+ nodes during ingestion, bulk updates, transaction handling.
- Files: `src/ingestion/pipeline.py` (lines 200-220)
- Risk: Performance degradation or data consistency issues with large documents.
- Priority: **Medium** - only affects large documents.

**Session Persistence Failures:**
- What's not tested: MongoDB write failures, concurrent session updates, session corruption recovery.
- Files: `src/retrieval/session_manager.py`, `src/retrieval/pipeline.py` (line 320)
- Risk: Sessions may be partially saved or lost, affecting conversation continuity.
- Priority: **Medium** - affects user experience in multi-turn conversations.

**Frontend Component Error Boundaries:**
- What's not tested: Component crash handling during upload, streaming errors, network timeouts.
- Files: `frontend/components/ErrorBoundary.tsx`, `frontend/components/chat/ChatClient.tsx`
- Risk: UI crashes instead of showing error messages to user.
- Priority: **Medium** - affects user experience.

**Atlas Search Index Creation:**
- What's not tested: Index creation under load, concurrent index creates, mongot unavailability handling.
- Files: `src/db/indexes.py` (lines 160-210)
- Risk: Index creation may fail silently or hang if mongot is unhealthy.
- Priority: **Low** - mostly handled in startup, not critical during operation.

---

*Concerns audit: 2026-02-17*
