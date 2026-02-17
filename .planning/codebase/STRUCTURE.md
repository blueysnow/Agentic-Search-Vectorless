# Codebase Structure

**Analysis Date:** 2026-02-17

## Directory Layout

```
Agentic-Search-Vectorless/
├── src/                          # Python backend
│   ├── api/                      # FastAPI application (Phase 4)
│   │   ├── routes/               # HTTP route handlers
│   │   │   ├── ingest.py         # POST /ingest
│   │   │   ├── query.py          # POST /query
│   │   │   ├── stream.py         # POST /query/stream
│   │   │   ├── documents.py      # GET /documents
│   │   │   ├── sessions.py       # GET /sessions, POST /sessions
│   │   │   └── __init__.py
│   │   ├── main.py               # Entry point for uvicorn
│   │   ├── server.py             # FastAPI app factory, lifespan, middleware
│   │   ├── models.py             # Pydantic request/response models
│   │   ├── middleware.py         # Error handling middleware
│   │   └── __init__.py
│   │
│   ├── ingestion/                # Document ingestion pipeline
│   │   ├── pipeline.py           # Orchestrator: page_index_main(), save_* functions
│   │   ├── parsers/              # Format-specific parsers
│   │   │   ├── pdf_parser.py     # PDF extraction (pypdf, PyMuPDF)
│   │   │   ├── markdown_parser.py# Markdown parsing
│   │   │   └── __init__.py
│   │   ├── tree_builder/         # Hierarchical structure generation
│   │   │   ├── tree_generator.py # 3-mode tree generation (ToC, no-ToC fallback)
│   │   │   ├── toc_detector.py   # ToC detection via LLM
│   │   │   ├── toc_transformer.py# Transform ToC to tree structure
│   │   │   ├── tree_utils.py     # Flatten, assign node IDs, compute paths
│   │   │   ├── splitter.py       # Handle large nodes recursively
│   │   │   ├── verifier.py       # Verify tree accuracy
│   │   │   └── __init__.py
│   │   ├── enrichment/           # Content enrichment (optional)
│   │   │   ├── summarizer.py     # Generate node summaries (LLM)
│   │   │   ├── keyword_extractor.py# Extract keywords (LLM)
│   │   │   ├── content_classifier.py# Classify content type (section, table, etc)
│   │   │   ├── cross_ref_detector.py# Detect cross-references
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── retrieval/                # Query answering pipeline
│   │   ├── pipeline.py           # Orchestrator: retrieve() main function
│   │   ├── atlas_search.py       # Atlas Search aggregation builder, fallback $text
│   │   ├── tree_navigator.py     # LLM-driven hierarchical tree walk
│   │   ├── reasoner.py           # LLM sufficiency check, answer generation
│   │   ├── merger.py             # Merge Atlas Search + tree navigation results
│   │   ├── content_loader.py     # Fetch page content for candidates
│   │   ├── query_analyzer.py     # Analyze query: type, keywords, intent
│   │   ├── session_manager.py    # Multi-turn conversation history
│   │   └── __init__.py
│   │
│   ├── models/                   # Pydantic data models
│   │   ├── document.py           # Document, Ingestion, DocumentMetadata
│   │   ├── node.py               # Node, CrossReference (tree structure)
│   │   ├── page.py               # Page (raw content)
│   │   ├── session.py            # RetrievalSession, RetrievalTurn
│   │   ├── retrieval.py          # RetrievalCandidate, ReasonerResponse, NextAction
│   │   └── __init__.py
│   │
│   ├── db/                       # Database layer
│   │   ├── client.py             # PyMongo singleton, get_client(), get_database()
│   │   ├── collections.py        # Typed collection accessors (documents_col, nodes_col, etc)
│   │   ├── indexes.py            # Index creation (compound, text, search indexes)
│   │   └── __init__.py
│   │
│   ├── llm/                      # LLM provider abstraction
│   │   ├── provider.py           # LLMProvider interface, Anthropic/OpenAI implementations
│   │   ├── prompts/              # Prompt templates
│   │   │   ├── tree_building.py  # Tree generation prompts (init, continue)
│   │   │   ├── toc_detection.py  # ToC detection prompt
│   │   │   ├── tree_navigation.py# Tree navigation prompts
│   │   │   ├── sufficiency_check.py# Sufficiency check prompts (single/multi-turn)
│   │   │   ├── summarization.py  # Summarization prompts
│   │   │   ├── query_analysis.py # Query analysis prompt
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── utils/                    # Shared utilities
│   │   ├── logger.py             # Structured logging setup (structlog)
│   │   ├── tokens.py             # Token counting (tiktoken)
│   │   ├── json_utils.py         # JSON extraction from LLM output
│   │   └── __init__.py
│   │
│   ├── config.py                 # Application settings (pydantic-settings)
│   ├── benchmarks/               # Performance benchmarking (optional)
│   └── __init__.py
│
├── frontend/                     # React/Next.js UI (App Router)
│   ├── app/                      # Next.js app directory
│   │   ├── layout.tsx            # Root layout
│   │   ├── page.tsx              # Home page (redirect to /documents)
│   │   ├── error.tsx             # Global error boundary
│   │   ├── globals.css           # Global styles
│   │   ├── providers.tsx         # Context providers
│   │   ├── api/                  # API routes (auth, chat proxying, sessions)
│   │   │   ├── chat/             # Chat/query proxying
│   │   │   │   └── stream/
│   │   │   │       └── route.ts  # POST /api/chat/stream (SSE proxy)
│   │   │   └── sessions/         # Session management
│   │   │       ├── route.ts      # POST/GET sessions
│   │   │       └── [sessionId]/
│   │   │           └── route.ts  # GET/DELETE single session
│   │   ├── documents/            # Document management
│   │   │   ├── page.tsx          # List documents page
│   │   │   ├── DocumentsClient.tsx# Client component
│   │   │   └── [id]/             # Document detail
│   │   │       ├── page.tsx
│   │   │       └── DocumentDetailClient.tsx
│   │   ├── chat/                 # Query/chat interface
│   │   │   └── page.tsx
│   │   ├── query/                # Query page (alt to /chat)
│   │   │   └── page.tsx
│   │   ├── sessions/             # Session history
│   │   │   ├── page.tsx          # List sessions
│   │   │   └── [id]/
│   │   │       └── page.tsx      # View session
│   │   └── dashboard/            # Dashboard
│   │       └── page.tsx
│   │
│   ├── components/               # Reusable React components
│   │   ├── ui/                   # Shadcn/UI components
│   │   │   ├── skeleton.tsx      # Loading skeleton
│   │   │   ├── toast.tsx         # Toast notifications
│   │   │   └── toaster.tsx       # Toast container
│   │   ├── chat/                 # Chat-related components
│   │   │   ├── ChatClient.tsx    # Main chat component
│   │   │   ├── ChatInput.tsx     # Input field
│   │   │   ├── MessageList.tsx   # Message display
│   │   │   ├── MessageItem.tsx   # Single message
│   │   │   ├── RetrievalTrace.tsx# Trace visualization
│   │   │   ├── ThinkingProcess.tsx# Thinking/reasoning display
│   │   │   ├── PageCitation.tsx  # Page source citations
│   │   │   └── DocumentSelector.tsx# Document picker
│   │   ├── documents/            # Document management
│   │   │   ├── UploadForm.tsx    # Server form wrapper
│   │   │   ├── UploadFormClient.tsx# Client form implementation
│   │   │   ├── UploadFormWrapper.tsx# Form container
│   │   │   ├── DocumentCard.tsx  # Document preview
│   │   │   ├── DocumentFilters.tsx# Filter UI
│   │   │   └── TreeVisualization.tsx# Tree visualization
│   │   ├── skeletons/            # Loading skeletons
│   │   │   ├── ChatSkeleton.tsx
│   │   │   ├── DocumentsSkeleton.tsx
│   │   │   └── SessionsSkeleton.tsx
│   │   └── layout/               # Layout components
│   │       └── AppShell.tsx      # Main app shell
│   │
│   ├── public/                   # Static assets
│   ├── package.json              # Frontend dependencies
│   ├── tsconfig.json             # TypeScript config
│   ├── next.config.ts            # Next.js config
│   └── tailwind.config.ts        # Tailwind CSS config
│
├── tests/                        # Pytest suite
│   ├── test_api.py               # API endpoint tests
│   ├── test_ingestion.py         # Ingestion pipeline tests
│   ├── test_retrieval.py         # Retrieval pipeline tests (naming varies)
│   ├── test_integration.py       # Full integration tests (real MongoDB, LLM)
│   ├── test_markdown_parser.py
│   ├── test_pdf_parser.py
│   ├── test_toc_detector.py
│   ├── test_tree_generator.py
│   ├── test_pipeline.py
│   ├── test_llm_provider.py
│   ├── test_models.py
│   └── conftest.py               # Pytest fixtures
│
├── docker/                       # Docker configurations
│   ├── compose/                  # Docker Compose files
│   └── scripts/                  # Docker setup scripts
│
├── .planning/                    # GSD planning outputs
│   ├── codebase/                 # Codebase analysis documents
│   └── phases/                   # Phase planning documents
│
├── pyproject.toml                # Python project config, dependencies
├── Dockerfile                    # Backend Docker image
├── docker-compose.yml            # Full stack composition
├── conftest.py                   # Pytest root config
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
└── README.md                     # Project documentation
```

## Directory Purposes

**`src/api/`**
- Purpose: HTTP API serving the frontend and external clients
- Contains: FastAPI app factory, route handlers, Pydantic request/response models, middleware
- Key files: `server.py` (app setup), `routes/` (handlers)
- Entry point: `main.py` (exports `app` for uvicorn)

**`src/ingestion/`**
- Purpose: Parse documents and build hierarchical PageIndex trees
- Contains: Document parsers (PDF, Markdown), ToC detection, tree generation, enrichment
- Key files: `pipeline.py` (orchestrator), `parsers/`, `tree_builder/`, `enrichment/`
- Invoked by: `/ingest` endpoint

**`src/retrieval/`**
- Purpose: Answer queries using dual retrieval and LLM reasoning
- Contains: Query analysis, Atlas Search, tree navigation, sufficiency checking, session tracking
- Key files: `pipeline.py` (orchestrator), `atlas_search.py`, `tree_navigator.py`, `reasoner.py`
- Invoked by: `/query` and `/query/stream` endpoints

**`src/models/`**
- Purpose: Define data schemas for MongoDB documents and API contracts
- Contains: Pydantic models for documents, nodes, pages, sessions, retrieval results
- Pattern: Camel case aliases (`nodeId` in MongoDB, `node_id` in Python)
- Used by: All layers for validation and serialization

**`src/db/`**
- Purpose: MongoDB client and collection accessors
- Contains: PyMongo singleton, typed collection functions, index creation
- Key files: `client.py` (singleton), `collections.py` (accessors), `indexes.py` (schema)
- Used by: Persistence operations in all layers

**`src/llm/`**
- Purpose: Abstract LLM backend with retry logic and provider switching
- Contains: Provider interface, implementations (Anthropic, OpenAI), retry logic, prompts
- Key files: `provider.py` (interface), `prompts/` (templates)
- Used by: Ingestion (tree generation, enrichment), retrieval (tree navigation, reasoning)

**`src/utils/`**
- Purpose: Shared utilities and helpers
- Contains: Structured logging, token counting, JSON extraction
- Key files: `logger.py`, `tokens.py`, `json_utils.py`
- Used by: All layers

**`frontend/`**
- Purpose: React/Next.js user interface
- Contains: App Router pages, components, API routes, styles
- Key paths: `/app` (pages), `/components` (reusable), `/app/api` (proxies)
- Server entry: `app/layout.tsx`

**`tests/`**
- Purpose: Unit, integration, and end-to-end test suite
- Contains: Pytest tests for all modules
- Pattern: `test_<module>.py` (one test file per source module)
- Config: `conftest.py` (fixtures, MongoDB testcontainers)

## Key File Locations

**Entry Points:**
- **Backend**: `src/api/main.py` (exports `app` for uvicorn)
- **Frontend Root**: `frontend/app/layout.tsx` (Next.js root layout)
- **Config**: `src/config.py` (Settings singleton via environment)

**Configuration:**
- `src/config.py`: Application settings (pydantic-settings, reads .env)
- `pyproject.toml`: Python dependencies, project metadata
- `frontend/next.config.ts`: Next.js configuration
- `Dockerfile`: Backend Docker image
- `docker-compose.yml`: Full stack (backend + MongoDB + optional search)

**Core Logic:**
- **Ingestion**: `src/ingestion/pipeline.py: page_index_main()`
- **Retrieval**: `src/retrieval/pipeline.py: retrieve()`
- **Tree Generation**: `src/ingestion/tree_builder/tree_generator.py`
- **Tree Navigation**: `src/retrieval/tree_navigator.py: tree_navigate()`
- **Reasoning**: `src/retrieval/reasoner.py: check_sufficiency()`
- **Atlas Search**: `src/retrieval/atlas_search.py: build_search_pipeline()`

**Testing:**
- `tests/conftest.py`: Pytest fixtures (MongoDB client, LLM mocks)
- `tests/test_integration.py`: Full pipeline tests with real services
- `tests/test_api.py`: API endpoint tests

## Naming Conventions

**Files:**
- `*.py`: Standard Python modules (snake_case names)
- `*.tsx`, `*.ts`: React/TypeScript (camelCase exports)
- `route.ts`: Next.js API route handlers
- `page.tsx`: Next.js page components
- `conftest.py`: Pytest configuration and fixtures

**Directories:**
- `api/`, `ingestion/`, `retrieval/`: Feature modules (lowercase)
- `routes/`, `parsers/`, `tree_builder/`: Sub-feature groups (lowercase, plural for collections)
- `components/`: React components (grouping by feature: `chat/`, `documents/`, `ui/`)
- `app/`: Next.js App Router root (lowercase routes match URL paths)

**Python Classes:**
- `PascalCase` for classes: `Document`, `Node`, `RetrievalCandidate`, `LLMProvider`
- `snake_case` for functions: `get_client()`, `page_index_main()`, `retrieve()`
- `UPPER_CASE` for constants: `MAX_RETRIES`, `TITLE_BOOST`, `VALID_ACTION_TYPES`

**MongoDB Field Names:**
- `camelCase` in database (Pydantic `alias=` enforces this)
- Examples: `documentId`, `nodeId`, `parentNodeId`, `childNodeIds`, `materializedPath`
- Python models use `snake_case`, Pydantic `populate_by_name=True` handles both

**API Endpoints:**
- Lowercase, hyphen-separated: `/ingest`, `/query`, `/query/stream`, `/documents`, `/sessions`
- Path parameters in brackets: `/documents/{id}`, `/sessions/{id}`
- Query params: `?limit=10&offset=0`

## Where to Add New Code

**New Feature:**
- **Primary code**: `src/<layer>/<feature>/` (e.g., `src/retrieval/ranking.py`)
- **Tests**: `tests/test_<feature>.py`
- **API endpoint**: `src/api/routes/<resource>.py`
- **Models**: Add to `src/models/<domain>.py` or create new if complex

**New Component/Module:**
- **Implementation**: Follow the 4-layer pattern (API -> orchestrator -> logic modules -> DB)
- **Example for new enrichment**:
  - Create `src/ingestion/enrichment/new_feature.py`
  - Expose function in `src/ingestion/enrichment/__init__.py`
  - Call from `src/ingestion/pipeline.py`
  - Add tests in `tests/test_enrichment.py`

**Utilities:**
- **Shared helpers**: `src/utils/<helper>.py`
- **Prompts**: `src/llm/prompts/<feature>.py`
- **Database ops**: `src/db/` if it's a new collection or index type

**Frontend Components:**
- **Feature pages**: `frontend/app/<feature>/page.tsx`
- **Reusable components**: `frontend/components/<feature>/<Component>.tsx`
- **API proxies**: `frontend/app/api/<resource>/route.ts`
- **Styles**: Inline Tailwind classes (no separate CSS files unless global)

## Special Directories

**`.planning/`**
- Purpose: GSD codebase analysis and phase planning documents
- Generated: Yes (by GSD tools)
- Committed: Yes
- Contents: `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `TESTING.md`, `CONCERNS.md`, `STACK.md`, `INTEGRATIONS.md`

**`docker/`**
- Purpose: Docker setup and orchestration
- Generated: No
- Committed: Yes
- Contents: Compose files, helper scripts

**`tests/`**
- Purpose: Unit and integration tests
- Generated: No
- Committed: Yes
- Run: `pytest tests/`

**`.venv/`** (if local development)
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (in `.gitignore`)
- Created: `python -m venv .venv`

**`frontend/node_modules/`**
- Purpose: Frontend JavaScript dependencies
- Generated: Yes
- Committed: No (in `.gitignore`)
- Created: `npm install`

---

*Structure analysis: 2026-02-17*
