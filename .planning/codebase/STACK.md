# Technology Stack

**Analysis Date:** 2026-02-17

## Languages

**Primary:**
- Python 3.12+ - Backend API, document ingestion, LLM integration, retrieval logic
- TypeScript 5.6+ - Frontend React components and Next.js application

**Secondary:**
- JavaScript (Node.js) - Frontend build tooling and runtime

## Runtime

**Environment:**
- Python 3.12+ (backend)
- Node.js 20 (frontend)

**Package Manager:**
- Backend: pip (with hatchling build system)
- Frontend: npm (using package-lock.json)
- Dependency lock: `uv.lock` (backend) and `package-lock.json` (frontend)

## Frameworks

**Core Backend:**
- FastAPI 0.115+ - REST API framework, async request handling
- Uvicorn 0.30+ - ASGI server for FastAPI deployment
- Pydantic 2.10+ - Data validation and settings management
- Pydantic-Settings 2.6+ - Environment configuration loading

**Core Frontend:**
- Next.js 15.1.0 - React framework, server-side rendering, API routes
- React 19.0.0 - UI component library

**Data Layer:**
- PyMongo 4.9+ with SRV support - Synchronous MongoDB driver
- Motor 3.6+ - Async MongoDB driver for async operations

**LLM Integration:**
- Anthropic SDK 0.40+ - Claude AI integration (primary)
- OpenAI SDK 1.55+ - GPT integration (secondary, optional)

**Frontend UI/Form Handling:**
- TanStack React Query 5.62.0 - Server state management and data fetching
- TanStack React Query DevTools 5.62.0 - Query debugging
- React Hook Form 7.54.0 - Form state management
- Zod 3.24.0 - Schema validation for forms
- Radix UI 1.x - Accessible component primitives:
  - @radix-ui/react-accordion (1.2.2)
  - @radix-ui/react-dialog (1.1.4)
  - @radix-ui/react-dropdown-menu (2.1.4)
  - @radix-ui/react-toast (1.2.15)
  - @radix-ui/react-tooltip (1.1.6)
- Lucide React 0.460.0 - Icon library

**Styling:**
- Tailwind CSS 3.4.0 - Utility-first CSS framework
- Tailwind Merge 2.6.0 - Merge Tailwind classes without conflicts
- Tailwind Animate 1.0.7 - Animation utilities
- PostCSS 8.4.49 - CSS processing
- Autoprefixer 10.4.20 - Vendor prefix automation
- Class Variance Authority 0.7.1 - Component variant management

## Key Dependencies

**Critical Backend:**
- pymongo[srv] 4.9+ - MongoDB connectivity with SRV support
- motor 3.6+ - Async MongoDB operations
- anthropic 0.40+ - Claude API client (primary LLM provider)
- fastapi 0.115+ - REST API framework
- uvicorn 0.30+ - ASGI application server

**Document Processing:**
- PyPDF 4.0+ - PDF text extraction and parsing
- PyMuPDF 1.24+ - Advanced PDF manipulation and rendering (requires libmupdf system library)
- tiktoken 0.8+ - OpenAI tokenizer for token counting

**Utility & Infrastructure:**
- structlog 24.4+ - Structured logging with JSON output
- python-dotenv 1.0+ - Load environment variables from .env files
- slowapi 0.1.9+ - Rate limiting middleware for FastAPI
- python-multipart 0.0.9+ - Multipart form data parsing

**Testing:**
- pytest 8.3+ - Test framework
- pytest-asyncio 0.24+ - Async test support
- pytest-cov 6.0+ - Code coverage reporting
- httpx 0.27+ - HTTP client for testing

**Code Quality:**
- ruff 0.8+ - Python linter and formatter

**Frontend Testing:**
- Vitest 2.1.0 - Unit/component testing framework
- @testing-library/react 16.1.0 - React component testing utilities
- @testing-library/jest-dom 6.9.1 - DOM matchers
- @testing-library/user-event 14.5.0 - User interaction simulation
- @playwright/test 1.49.0 - E2E testing framework
- jsdom 28.0.0 - DOM implementation for testing

**Linting & Formatting:**
- ESLint 9.17.0 - JavaScript linting
- eslint-config-next 15.1.0 - Next.js ESLint rules
- Prettier 3.4.0 - Code formatter

## Configuration

**Environment:**
Backend (`src/config.py`):
- Loaded from `.env` file via Pydantic Settings
- Overridable via environment variables

Key configurations:
- `MONGODB_URI` - MongoDB connection string (default: mongodb://localhost:27017)
- `MONGODB_DATABASE` - Database name (default: agentic_search)
- `LLM_PROVIDER` - "anthropic" or "openai" (default: anthropic)
- `LLM_INGESTION_MODEL` - Model for document processing (default: claude-haiku-4-5-20251001)
- `LLM_RETRIEVAL_MODEL` - Model for query answering (default: claude-haiku-4-5-20251001)
- `ANTHROPIC_API_KEY` - Claude API key (required if LLM_PROVIDER=anthropic)
- `OPENAI_API_KEY` - OpenAI API key (required if LLM_PROVIDER=openai)
- `OPENAI_BASE_URL` - Optional custom OpenAI endpoint
- `MAX_PAGES_PER_NODE` - Document chunking parameter (default: 10)
- `MAX_TOKENS_PER_NODE` - Token limit per node (default: 20000)
- `PORT` - API port (default: 8000, overridden to 8002 in docker-compose)
- `CORS_ORIGINS` - Comma-separated CORS origins (empty = disabled)
- `LOG_LEVEL` - Logging level (default: info)

Frontend (`frontend/.env.local` or docker-compose):
- `NEXT_PUBLIC_API_URL` - Backend API base URL (baked into client at build time)

**Build:**
- Backend: `pyproject.toml` with hatchling build system
- Frontend: `frontend/next.config.ts` for Next.js configuration
- Frontend: `frontend/tsconfig.json` for TypeScript compilation
- Frontend: `frontend/tailwind.config.ts` for Tailwind CSS
- Frontend: `frontend/vitest.config.ts` for test runner configuration

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 20+
- MongoDB 7.0+ with replica set support (for transactions)
- libmupdf development headers (for PyMuPDF)
- Docker and Docker Compose (for containerized deployment)

**Production:**
- Deployment: Docker containers (see Dockerfile files)
- Backend container: Python 3.12-slim base image, exposes port 8002
- Frontend container: Node.js 20-alpine, next.js standalone output, exposes port 3000
- Database: MongoDB 7.0+ (can be local or Atlas)
- Optional: mongot (MongoDB search engine) for Atlas Search support
- Optional: mongot container for on-premise full-text search index support

---

*Stack analysis: 2026-02-17*
