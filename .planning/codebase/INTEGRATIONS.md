# External Integrations

**Analysis Date:** 2026-02-17

## APIs & External Services

**LLM Providers (Pluggable):**
- **Anthropic Claude** (primary)
  - SDK: `anthropic>=0.40`
  - Auth: Environment variable `ANTHROPIC_API_KEY`
  - Models: Claude Haiku (ingestion), Claude Sonnet (retrieval)
  - Implementation: `src/llm/provider.py:AnthropicProvider`
  - Features: Async support, retry with exponential backoff, message formatting

- **OpenAI GPT** (secondary, optional)
  - SDK: `openai>=1.55`
  - Auth: Environment variables `OPENAI_API_KEY` and optional `OPENAI_BASE_URL`
  - Implementation: `src/llm/provider.py:OpenAIProvider`
  - Features: Async support, custom endpoint support, retry mechanism

**Provider Selection:**
- Configuration: `LLM_PROVIDER` environment variable ("anthropic" or "openai")
- Factory: `src/llm/provider.py:get_provider()` instantiates correct provider
- Error Handling: Custom exceptions for auth errors, bad requests, retryable errors
- Retry Strategy: Exponential backoff with full jitter (max 10 attempts)

## Data Storage

**Primary Database:**
- **MongoDB**
  - Type: Document database
  - Connection: Environment variable `MONGODB_URI`
  - Default: mongodb://localhost:27017 (local) or mongodb+srv:// (Atlas)
  - Database: Configurable via `MONGODB_DATABASE` (default: agentic_search)
  - Client Library: `pymongo[srv]>=4.9` (synchronous)
  - Async Driver: `motor>=3.6` (async compatibility, though not currently used)
  - Collections:
    - `documents` - Ingested PDF documents with metadata
    - `nodes` - Document tree nodes with content, summaries, keywords
    - `sessions` - Query sessions for conversation history
  - Connection Pool: Max 50 connections, 5s server selection timeout, 30s socket timeout
  - Configuration: `src/db/client.py:get_client()` creates MongoClient singleton

**Indexes:**
- Text indexes on `nodes` collection for full-text search fallback
- Atlas Search indexes for enhanced search (optional, requires MongoDB Atlas or mongot)
- Document indexes for efficient filtering and lookups
- Index creation: `src/db/indexes.py:ensure_indexes()`, `ensure_text_index()`, `ensure_search_index()`

**Search Backend (Dual-Mode):**
- **Atlas Search** (primary when available)
  - Technology: MongoDB Atlas Search or on-premise mongot
  - Implementation: `src/retrieval/atlas_search.py`
  - Features: Compound queries with boosting, fuzzy matching, phrase search
  - Pipeline: Aggregation pipeline with $search stage
  - Fallback: Automatically falls back to $text if indexes unavailable
  - Detection: `detect_search_backend()` checks if search indexes exist at startup

- **Text Search** (fallback)
  - Technology: MongoDB $text operator
  - Implementation: `src/retrieval/atlas_search.py:text_search()`
  - Automatic: Used when Atlas Search indexes not configured
  - No external dependencies required

## File Storage

- **Local filesystem only** - PDFs stored on application server or shared volume
- Document upload: `src/api/routes/ingest.py` receives multipart form data
- Frontend upload: `frontend/lib/api/client.ts:uploadDocumentWithProgress()` with XHR progress tracking
- Maximum upload: 5 minute timeout configured in frontend and backend

## Caching

- **None** - Application is stateless, relies on MongoDB for persistence
- No Redis, Memcached, or other caching layers
- Browser caching: Frontend uses React Query with stale-while-revalidate patterns

## Authentication & Identity

**Backend:**
- **No built-in authentication** - API endpoints are public
- Future: Can add via middleware (not currently implemented)
- CORS only restricts cross-origin requests

**Frontend:**
- No user authentication
- No OAuth/social login
- Sessions keyed by session ID (anonymous, persisted to MongoDB)

## Rate Limiting

**Implementation:** slowapi middleware on FastAPI
- Configuration: `src/api/server.py:limiter` set to 60 requests/minute per remote address
- Applies globally to all endpoints
- Rate limit errors return HTTP 429 with structured error response

## Monitoring & Observability

**Error Tracking:**
- None detected - No Sentry, DataDog, or similar integration

**Logging:**
- Framework: `structlog>=24.4` for structured logging
- Setup: `src/utils/logger.py:setup_logging()`
- Format: JSON output for easy parsing
- Levels: Configurable via `LOG_LEVEL` environment variable (default: info)
- Lifecycle Events: Startup/shutdown, MongoDB connection, index creation, search backend detection

**Health Checks:**
- Endpoint: `GET /health` on backend
- Checks MongoDB connectivity
- Returns JSON with status ("ok" or "degraded") and MongoDB status
- Used by Docker containers for healthchecks

## CI/CD & Deployment

**Hosting:**
- Self-hosted via Docker containers
- Docker Compose orchestration for local development and deployment

**Containerization:**
- Backend: `Dockerfile` (Python 3.12-slim)
  - Multi-layer build with pip caching
  - Non-root user execution (appuser)
  - Health check via /health endpoint
  - Entry: `uvicorn src.api.main:app --host 0.0.0.0 --port 8002`

- Frontend: `frontend/Dockerfile` (Node.js 20-alpine)
  - Multi-stage build (builder + runner)
  - Next.js standalone output mode
  - Non-root user execution (nextjs)
  - Entry: `node server.js`

- Database: Official MongoDB images
  - Default: mongo:7.0 (simple, single container)
  - Search Profile: mongodb-community-server:8.0.4 + mongot:latest

**CI Pipeline:**
- No automated CI detected (GitHub Actions, GitLab CI, etc.)
- Local only: Docker Compose

**Deployment Configurations:**
- `docker-compose.yml` - Main orchestration file
  - Services: MongoDB, FastAPI backend, Next.js frontend
  - Network: Custom bridge network (app-network)
  - Volumes: MongoDB data persistence
  - Environment: .env file loading

- `docker-compose.search.override.yml` - Optional search profile
  - Adds: mongot service + MongoDB search-enabled variant
  - Profile: [search] - activated via `docker-compose --profile search`

## Webhooks & Callbacks

**Incoming:**
- None detected - No webhook endpoints for external services

**Outgoing:**
- None detected - Application doesn't call external webhooks

## API Communication

**Frontend to Backend:**
- Protocol: HTTPS (development: HTTP)
- Base URL: `process.env.NEXT_PUBLIC_API_URL` (default: http://localhost:8002)
- Transport: Fetch API with XMLHttpRequest fallback for upload progress
- Format: JSON request/response

**Backend Routes:**
- `POST /ingest/upload` - Document upload endpoint
- `GET /documents` - List documents with filters
- `GET /documents/{id}` - Get single document
- `DELETE /documents/{id}` - Delete document
- `GET /query` - Query endpoint (with streaming support)
- `POST /query` - Query submission
- `POST /query/stream` - Streaming query responses (Server-Sent Events)
- `GET /sessions` - List sessions
- `POST /sessions` - Create session
- `GET /sessions/{id}` - Get session with query history
- `DELETE /sessions/{id}` - Delete session
- `GET /health` - Health check

**Timeouts:**
- Standard requests: 10 seconds
- Query operations: 60 seconds
- File uploads: 5 minutes (300 seconds)

## Environment Configuration

**Required Environment Variables:**

Backend (`.env` file):
- `MONGODB_URI` - MongoDB connection string
- `ANTHROPIC_API_KEY` - Claude API key (if using Anthropic)

Frontend (build-time):
- `NEXT_PUBLIC_API_URL` - Backend API URL (baked into JavaScript at build time)

**Optional Environment Variables:**

Backend:
- `LLM_PROVIDER` - LLM provider selection (default: "anthropic")
- `LLM_INGESTION_MODEL` - Ingestion model (default: claude-haiku-4-5-20251001)
- `LLM_RETRIEVAL_MODEL` - Retrieval model (default: claude-haiku-4-5-20251001)
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- `OPENAI_BASE_URL` - Custom OpenAI endpoint
- `CORS_ORIGINS` - Comma-separated allowed origins
- `LOG_LEVEL` - Logging verbosity
- `PORT` - API server port
- Document processing parameters (MAX_PAGES_PER_NODE, MAX_TOKENS_PER_NODE, etc.)
- Retrieval parameters (ATLAS_SEARCH_WEIGHT, TREE_NAVIGATION_WEIGHT, etc.)

**Secrets Location:**
- Development: `.env` file (local, not committed)
- Docker: Environment variables injected via docker-compose.yml or .env file
- Production: Environment variables set via container orchestration (Kubernetes, Docker Swarm, etc.)

## External Dependencies Summary

**Direct External APIs:**
- Anthropic Claude API - LLM inference
- OpenAI API - Alternative LLM provider (optional)
- MongoDB - Data persistence

**No Third-Party SaaS Dependencies:**
- No authentication provider (Auth0, Okta)
- No error tracking (Sentry, Rollbar)
- No analytics (Mixpanel, Amplitude)
- No CDN or storage service (AWS S3, Cloudflare)
- No email service (SendGrid, Mailgun)
- No observability platform (DataDog, New Relic)

---

*Integration audit: 2026-02-17*
