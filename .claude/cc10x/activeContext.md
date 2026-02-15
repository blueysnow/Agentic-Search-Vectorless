<!-- CC10x Memory File - DO NOT manually edit section headers -->

## Current Focus
- Make agentic-search-mongo work perfectly end-to-end (ingest → query → stream → display)
- Fix all broken pieces identified in comprehensive audit
- Inherited from cc100x: Backend 428 tests pass, Frontend 290 tests pass
- Architecture: PageIndex Trees + MongoDB + Atlas Search (Lucene) + LLM Reasoning + FastAPI + Next.js 15

## Recent Changes
- [UX-BUILD] Full UX refactor: 3-phase plan → component-builder → review/hunt → 2x REM-FIX → integration-verifier
- [Task-24] Session detail proxy: added data transform (sessionId→id, turns→messages, documentId→documentIds[])
- [Task-24] Backend DELETE /sessions/{id} endpoint + delete_session() in session_manager.py
- [Task-24] CORS updated: allow_methods now includes DELETE
- [Task-24] Sessions proxy: forward limit/offset params, typed BackendSession interface (no any)
- [Task-24] Removed dead date filter UI from sessions page (backend doesn't support date filtering)
- [Task-24] useSessions hook cleaned: removed startDate/endDate, kept documentId + limit/offset
- [Task-24] Test updated: date range test → pagination test
- [Task-21] Fixed session detail proxy: /api/sessions/ → /sessions/ (backend has no /api prefix)
- [Task-21] Added backend GET /sessions list endpoint + list_sessions() in session_manager.py
- [Task-21] Added SessionListItemResponse + SessionListResponse to models.py
- [Task-21] Frontend sessions proxy transforms backend response to SessionSummary format
- [Task-21] Fixed 3 failing tests: .txt is now valid, changed test files to .exe, updated error messages
- [Task-21] ChatClient: added isError handling for document fetch + error banner
- [Task-21] ChatClient: validate documentId URL param with isValidDocumentId
- [Task-21] Sidebar: close mobile sidebar on route change via useEffect on pathname
- [Task-21] DocumentSelector: removed unused useCallback import
- [E2E-FIX] Added python-multipart to pyproject.toml (required by FastAPI UploadFile/Form)
- [E2E-FIX] Fixed LLM model defaults: gpt-4o-mini → claude-3-5-haiku-20241022 (was sending OpenAI model to Anthropic API)
- [E2E-FIX] Fixed retrieval model default: claude-opus-4-6 → claude-sonnet-4-20250514
- [E2E-FIX] Rewrote ingest.py: added POST /ingest/upload for multipart file uploads (PDF, markdown, text)
- [E2E-FIX] Updated frontend client.ts: upload URL → /ingest/upload (was sending FormData to JSON endpoint)
- [E2E-FIX] Fixed frontend healthcheck: wget http://0.0.0.0:3000 (localhost fails on Alpine when HOSTNAME=0.0.0.0)
- [E2E-FIX] Full upload pipeline verified: upload txt → parse → LLM ingestion → MongoDB → completed
- [E2E-FIX] Fixed /query page: was placeholder stub, now has full ChatClient interface (was at /chat only)
- [E2E-FIX] Added .txt to frontend accepted file types (backend already supported it)
- [AUDIT] Reference comparison: 13/16 features full parity, 2 partial, 1 missing
- [REM-FIX-14] Backend Dockerfile: stub src/__init__.py + --no-deps reinstall (hatchling layer caching)
- [REM-FIX-14] Frontend Dockerfile: mkdir -p public in builder (COPY fails on missing source)
- [REM-FIX-14] Health check returns 503 when MongoDB disconnected (Docker health monitoring)
- [REM-FIX-14] use_fuzzy logged when dropped on Community backend
- [REM-FIX-14] env_file: required: false (fresh clone support)
- [REM-FIX-14] CORS includes localhost:3000 + 127.0.0.1:3000
- [REM-FIX-14] Switched next/font/google → next/font/local with bundled Inter font (Docker offline builds)
- [Docker-E2E] docker compose up: 3 containers (mongodb, backend, frontend) all healthy
- [Docker-E2E] Search backend: community detected, text index created, 16 regular indexes ensured
- [Docker-E2E] 12/12 verification scenarios PASS
- [Task-9] Docker E2E: Dockerfiles for backend (Python 3.12-slim) + frontend (Node 20 Alpine multi-stage)
- [Task-9] MongoDB Community fallback: text_search() using $text + text index, detect_search_backend()
- [BUILD] Full Docker E2E workflow: component-builder → [code-reviewer ∥ silent-failure-hunter] → REM-FIX → integration-verifier
- [Task-2] Created SSE streaming endpoint POST /query/stream (src/api/routes/stream.py)
- [Task-2] Fixed N+1 tree navigator with _get_children_batch using $in query
- [Task-2] Replaced PyPDF2 with pypdf in pyproject.toml + pdf_parser.py + tests
- [Task-2] Added docker-compose.yml (MongoDB 7.0 replSet + backend + frontend)
- [Task-2] Moved 23+ audit markdown files from root to docs/audits/
- [Task-2] Fixed frontend proxy URL: /api/chat/stream -> /query/stream
- [REM-FIX] Fixed SSE format mismatch: frontend proxy now strips "data: " prefix before JSON.parse
- [REM-FIX] Fixed silent catch in proxy: parse errors forwarded as SSE error events
- [REM-FIX] Fixed exception leakage in stream.py: generic "Retrieval failed" message
- [REM-FIX] Added 60s timeout on retrieve() via asyncio.wait_for
- [REM-FIX] Fixed broken test mock: _get_children → _get_children_batch
- [REM-FIX] Removed dead _get_children function, added .limit(200) to batch query
- [REM-FIX] Docker Compose: bound MongoDB to 127.0.0.1, removed deprecated version field
- Backend 443 tests pass, Frontend 290 tests pass, TypeScript clean, build clean

## Next Steps
- Commit all UX refactor changes
- Make ingestion async (return 202 + poll status) for large PDF support
- Add leaf vs parent summary distinction (prefix_summary for parents)
- Add preference-integrated retrieval (domain rules, expert knowledge)
- Add DELETE /documents/{id} endpoint
- Fix benchmark silent failures in benchmark_runner.py

## Decisions
- MongoDB Community fallback: detect_search_backend() at startup, transparent switch in atlas_search()
- Atlas Search (Lucene) - built-in, free, full-text search
- No Vector Search - vectorless philosophy
- MongoDB primary storage - JSON document model for hierarchical trees
- PageIndex as base architecture
- Python 3.12+, FastAPI, Pydantic, pytest
- Next.js 15 + React 19, TanStack Query, SSE streaming
- 5 MongoDB collections: documents, nodes, pages, retrieval_sessions, analytics

## Learnings
- [UX-BUILD] next/typescript ESLint config promotes no-explicit-any to ERROR — tsc passes but next build fails. Always run next build as final gate, not just tsc
- [UX-BUILD] Detail proxy transforms easily missed when list proxy gets the transform — verify BOTH list and detail endpoints
- [UX-BUILD] CORS allowed_methods must include DELETE if frontend uses it — default ["GET", "POST"] blocks DELETE silently
- [UX-BUILD] UI filter controls without backend support = dead UI — remove UI or add backend support, never leave connected but non-functional
- [UX-BUILD] Proxy layer must forward ALL query params (limit, offset) or pagination silently breaks with defaults
- [UX-BUILD] SessionListItemResponse uses populate_by_name with aliases — frontend proxy accesses camelCase alias names, frontend types use different field names, proxy must transform
- [Task-9] MongoDB Community Edition lacks $search (Atlas Search) -- need $text fallback with text index
- [Task-9] NEXT_PUBLIC_API_URL must be build ARG in Docker (Next.js bakes it in at build), browser connects to localhost:8000 not Docker network name
- [Task-9] Next.js standalone output copies only needed files -- must also copy .next/static and public/ separately
- [Task-9] detect_search_backend() at startup avoids per-query overhead -- set module-level flag once
- [Task-9] Text index weights {title:10, summary:5, keywords:3} mirror Atlas Search boost values
- [inherited] See cc100x memory for 160+ learnings from Phases 1-5 and UI Weeks 1-5
- [cc10x-init] Frontend endpoints had /api prefix but backend routes are /documents, /ingest, /query, /sessions
- [cc10x-init] PyPDF2 deprecated, pypdf is the successor
- [Task-2] SSE endpoints should handle errors as SSE events (not HTTP errors) since EventSource expects 200
- [Task-2] StreamRequest needs flexible field names to bridge frontend (message, document_ids) and backend (query, document_id)
- [Task-2] MongoDB $in batch queries eliminate N+1 with zero API change -- just swap _get_children loop with _get_children_batch
- [Task-2] pypdf is API-compatible with PyPDF2 (PdfReader, PdfWriter same interface)
- [REM-FIX] SSE proxy must strip "data: " prefix when re-parsing backend SSE → JSON.parse fails on "data: {...}"
- [REM-FIX] Test mocks must match actual SSE wire format, not idealized raw JSON
- [REM-FIX] When replacing a function with batch variant, ALL test mock patches must be updated
- [REM-FIX] SSE error events must use generic messages (never raw exception strings)
- [REM-FIX] asyncio.wait_for wraps retrieve() with 60s timeout + TimeoutError catch
- [REM-FIX] MongoDB $in batch query needs .limit() to prevent unbounded result sets
- [Verifier] docker compose config --quiet is fastest Docker validation (exit code only)
- [Verifier] 11 backend tests always skip without live MongoDB (integration tests)
- [REM-FIX-14] Hatchling requires source package dir at pip install time -- cannot cache deps with pyproject.toml alone
- [REM-FIX-14] Docker COPY fails hard on missing source dirs -- always verify target dirs exist
- [REM-FIX-14] next/font/google fails in Docker builds (no internet) -- use next/font/local with bundled font
- [REM-FIX-14] Health checks must return non-200 on degraded state or Docker orchestration is blind
- [REM-FIX-14] Docker Compose env_file: use required: false for optional .env files (v2.24+)
- [Docker-E2E] Port conflicts from local dev servers block Docker containers -- check lsof -i :PORT before compose up
- [Docker-E2E] MongoDB replica set auto-initializes via healthcheck script (rs.initiate on first run)
- [E2E-FIX] FastAPI UploadFile/Form requires python-multipart — missing dep crashes on import, not at runtime
- [E2E-FIX] Default LLM model must match default provider — gpt-4o-mini + anthropic = 404 error
- [E2E-FIX] Frontend sends FormData for file uploads, backend must accept UploadFile not JSON IngestRequest
- [E2E-FIX] Alpine wget healthcheck fails on localhost when server binds to 0.0.0.0 — use 0.0.0.0 in check

## References
- Plan: docs/plans/VECTORLESS_RAG_SYSTEM_PLAN.md
- UI Plan: docs/plans/NEXTJS_UI_PLAN.md
- Research: docs/research/ (7 files)
- Source: reference/PageIndex/
- cc100x Memory: .claude/cc100x/ (full history)

## Blockers
- None

## Last Updated
2026-02-15 - UX Refactor BUILD COMPLETE: 3 phases + 2 REM-FIX rounds. 300/300 frontend tests, tsc clean, next build 11 routes. Session CRUD fully functional. Sidebar + AppShell layout. Upload progress + success CTA.
