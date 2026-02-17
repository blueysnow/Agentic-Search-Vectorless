# CLAUDE.md

## Project Overview

Agentic Search -- Vectorless RAG on MongoDB. A document retrieval system that does NOT use vector embeddings. Instead it builds a hierarchical PageIndex tree (like a table of contents) from uploaded documents, then uses an LLM to reason and navigate that structure to answer queries.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI 0.115+, PyMongo 4.9+, Anthropic SDK, structlog
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript 5.6+, TanStack Query, Tailwind CSS 3.4, Radix UI
- **Database:** MongoDB 7.0+ with replica set (required for change streams)
- **Build:** uv (Python), npm (frontend), Docker Compose

## Architecture

Five layers: API (`src/api/`) → Ingestion (`src/ingestion/`) → Retrieval (`src/retrieval/`) → Data (`src/db/`) → LLM (`src/llm/`). Frontend is a separate Next.js app in `frontend/`.

**Ingestion:** 3-mode tree building with fallback (A: ToC with pages → B: ToC without pages → C: LLM-generated hierarchy). Nodes get summaries, keywords, content classification, and cross-references.

**Retrieval:** Dual scoring -- Atlas Search (BM25, weight 0.3) + LLM tree navigation (weight 0.7), up to 5 reasoning iterations.

**Data model:** Three collections (`documents`, `nodes`, `pages`) + `retrieval_sessions`. Nodes use `materializedPath` (e.g. `/0001/0003/0006`) with `parentNodeId`/`childNodeIds[]`.

## Key Commands

```bash
# Backend
uv run pytest                                    # run backend tests (471 tests)
uv run pytest -v --tb=short                      # verbose with short tracebacks
uv run pytest -k <pattern>                       # filter tests
uv run pytest -m integration                     # integration tests (need MongoDB + LLM)
uvicorn src.api.server:create_app --factory --reload --port 8002  # dev server

# Frontend (from frontend/)
npm test                                         # run vitest (300 tests, 40 suites)
npm run dev                                      # dev server on port 3000
npm run build                                    # production build
npm run lint                                     # ESLint

# Docker
docker compose up                                # default: mongodb + backend + frontend
docker compose --profile search up               # adds Atlas Search (mongodb-search + mongot)

# Linting
uv run ruff check src/                           # Python lint
uv run ruff format src/                          # Python format
```

## Environment

Copy `.env.example` to `.env`. Required vars:
- `MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0`
- `ANTHROPIC_API_KEY=sk-ant-...`

Key optional vars: `LLM_PROVIDER` (anthropic|openai), `LLM_INGESTION_MODEL`, `LLM_RETRIEVAL_MODEL`, `PORT` (default 8002), `CORS_ORIGINS`.

All settings defined in `src/config.py:Settings` (pydantic-settings with `lru_cache`).

## API Endpoints

```
POST /ingest/upload              Upload document (PDF/Markdown/text)
POST /query/                     Query (JSON response)
POST /query/stream               Query (SSE streaming)
GET  /documents                  List documents
GET  /documents/{id}             Get document detail
DELETE /documents/{id}           Delete document + nodes + pages
GET  /sessions                   List sessions
POST /sessions                   Create session
GET  /sessions/{id}              Get session with history
DELETE /sessions/{id}            Delete session
GET  /health                     Health check
```

Rate limit: 60 req/min per IP (slowapi, HTTP 429).

## Code Conventions

**Python:**
- ruff: `target-version = "py312"`, `line-length = 120`
- `from __future__ import annotations` at top of every module
- `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants
- Private helpers prefixed with `_`
- Pydantic models use `Field(..., alias="camelCase")` with `populate_by_name=True`
- Logging: `get_logger(__name__)`, events as snake_case strings

**TypeScript:**
- ESLint with `next/core-web-vitals` + `next/typescript`
- Strict mode enabled
- Path alias: `@/*` → `frontend/` root
- `camelCase` functions/vars, `PascalCase` types/components

## Testing

**Backend (pytest):** Config in `pyproject.toml`. Root `conftest.py` has autouse fixture setting safe env vars and clearing settings cache. Integration tests need `@pytest.mark.integration`.

**Frontend (Vitest):** Config in `frontend/vitest.config.ts`. Environment: jsdom (v28, requires Node.js 20+). Setup file: `frontend/tests/setup.ts` imports `@testing-library/jest-dom`.

## Docker Networking

Frontend server-side API routes (Next.js `app/api/`) use `BACKEND_URL=http://backend:8002` for container-to-container communication. `NEXT_PUBLIC_API_URL` is baked at build time for client-side browser requests only.

## Key Files

| Purpose | Path |
|---------|------|
| Backend entry | `src/api/main.py` |
| App factory | `src/api/server.py:create_app()` |
| Config (all env vars) | `src/config.py:Settings` |
| Ingestion pipeline | `src/ingestion/pipeline.py:page_index_main()` |
| Retrieval pipeline | `src/retrieval/pipeline.py:retrieve()` |
| Atlas Search | `src/retrieval/atlas_search.py` |
| LLM provider | `src/llm/provider.py` |
| MongoDB client | `src/db/client.py:get_client()` |
| Index creation | `src/db/indexes.py:ensure_indexes()` |
| Frontend API client | `frontend/lib/api/client.ts` |
| Docker orchestration | `docker-compose.yml` |

## Git Workflow

- `main` branch: stable/production
- `dev` branch: active development
- Commit messages: conventional style, concise description of "why"
