# Architecture

**Analysis Date:** 2026-02-17

## Pattern Overview

**Overall:** Vectorless RAG (Retrieval-Augmented Generation) System with Hybrid Tree Navigation

**Key Characteristics:**
- Document-structured RAG: Documents are hierarchically organized into PageIndex trees, not vectorized
- Dual retrieval: Atlas Search (semantic text search) + Tree Navigation (top-down hierarchical browsing)
- LLM-driven reasoning: LLM evaluates sufficiency and recommends next actions (deeper navigation, reference following)
- Async FastAPI backend with MongoDB persistence
- Streaming query support with multi-turn conversation history

## Layers

**API Layer (Presentation):**
- Purpose: HTTP endpoints for document ingestion, querying, session management, and streaming
- Location: `src/api/` (routes, models, middleware, server)
- Contains: FastAPI routers, Pydantic request/response models, error handling middleware
- Depends on: Config, DB, Ingestion, Retrieval, LLM Provider modules
- Used by: Frontend (React/Next.js), external API clients

**Ingestion Layer:**
- Purpose: Parse documents, detect table of contents, build hierarchical PageIndex trees, enrich content
- Location: `src/ingestion/` (pipeline, parsers, tree_builder, enrichment)
- Contains: PDF/Markdown parsers, ToC detection, tree generation, summarization, keyword extraction
- Depends on: LLM Provider, DB, Models, Utils
- Used by: API layer (/ingest endpoint)
- Key workflow:
  1. Parse uploaded file to page tuples (text, token_count)
  2. Detect ToC if present
  3. Generate hierarchical structure via LLM (3 modes: with page numbers, without page numbers, no ToC)
  4. Enrich nodes with summaries, keywords, cross-references
  5. Persist to MongoDB (documents, nodes, pages collections)

**Retrieval Layer:**
- Purpose: Answer queries by combining dual search methods, merging results, and iteratively reasoning about sufficiency
- Location: `src/retrieval/` (pipeline, atlas_search, tree_navigator, reasoner, session_manager, merger, content_loader)
- Contains: Query analysis, Atlas Search builder, tree navigation, LLM reasoning, session tracking, content fetching
- Depends on: DB, LLM Provider, Models, Utils
- Used by: API layer (/query endpoint, /stream endpoint)
- Key workflow:
  1. Parse and analyze query (extract keywords, classify intent)
  2. Parallel retrieval: Atlas Search + tree navigation
  3. Merge and deduplicate candidates
  4. Load candidate node content
  5. LLM reasoning loop: check sufficiency, generate answer, recommend next action
  6. If not sufficient: navigate deeper, follow cross-references, or search new section
  7. Log turn to session history

**Data Layer:**
- Purpose: MongoDB client, collection accessors, schema, indexes
- Location: `src/db/` (client.py, collections.py, indexes.py)
- Contains: PyMongo singleton client, typed collection accessors, index creation
- Depends on: Config, Models
- Used by: All layers that need persistence
- Collections:
  - `documents`: Document metadata, ingestion status
  - `nodes`: Hierarchical tree nodes with parent/child relationships, summaries, keywords
  - `pages`: Raw page content with token counts
  - `retrieval_sessions`: Multi-turn conversation history
  - `analytics`: Event logging (optional)

**LLM Provider Layer:**
- Purpose: Abstract LLM calls with retry logic, provider switching (Anthropic/OpenAI)
- Location: `src/llm/` (provider.py, prompts/)
- Contains: LLM interface, retry/backoff logic, prompt templates
- Depends on: Config, Utils
- Used by: Ingestion, Retrieval, other reasoning tasks
- Supports: Anthropic (claude-*), OpenAI (gpt-*)

**Utility Layer:**
- Purpose: Shared helpers for logging, tokenization, JSON parsing, configuration
- Location: `src/utils/` (logger.py, tokens.py, json_utils.py)
- Location: `src/config.py` (Settings singleton)
- Contains: Structured logging (structlog), token counting (tiktoken), JSON extraction, settings management
- Depends on: External libraries only
- Used by: All layers

**Frontend Layer:**
- Purpose: React/Next.js UI for document upload, querying, session management
- Location: `frontend/` (Next.js App Router, components)
- Contains: Pages, API routes, components (chat, documents, upload)
- Depends on: Backend API
- Routes: `/documents` (list/upload), `/chat` (query), `/sessions` (history)

## Data Flow

**Ingestion Flow:**

1. **File Upload** (User -> API)
   - POST /ingest with file or JSON content
   - `src/api/routes/ingest.py: _extract_text_from_upload()` -> page_list

2. **Tree Generation** (Ingestion Pipeline)
   - `src/ingestion/pipeline.py: page_index_main()` orchestrates:
     - `toc_detector.check_toc()` -> detects ToC pages
     - `tree_generator.py` -> 3 modes (with/without page nums, no ToC)
     - LLM generates tree structure as JSON: `[{title, start_page, end_page, children: [...]}]`
     - `tree_utils.post_processing()` -> flattens, assigns node IDs, computes materialized paths

3. **Enrichment** (Optional)
   - `summarizer.py` -> LLM summaries per node
   - `keyword_extractor.py` -> LLM keywords
   - `content_classifier.py` -> content type (section, table, appendix)
   - `cross_ref_detector.py` -> detect cross-references

4. **Persistence**
   - `save_document()` -> insert to `documents` collection (status: processing)
   - `save_nodes()` -> bulk insert `nodes` collection with full hierarchy (parent_node_id, child_node_ids, materialized_path)
   - `save_pages()` -> insert `pages` collection with raw content
   - Update `documents` (status: completed, total_nodes, total_tokens)

**Query Flow:**

1. **Query Received** (User -> API)
   - POST /query with query + document_id + optional session_id
   - `src/api/routes/query.py` -> verify document ingested, call `retrieve()`

2. **Query Analysis**
   - `query_analyzer.analyze_query()` -> LLM classifies type, extracts keywords, sets search intent

3. **Dual Retrieval** (Parallel)
   - **Atlas Search**: `atlas_search.build_search_pipeline()` -> $search aggregation
     - Boosts: title (10x), summary (5x), keywords (3x), phrases (15x)
     - Returns scored nodes, scoped to document
   - **Tree Navigation**: `tree_navigator.tree_navigate()` -> LLM-driven hierarchical walk
     - Load root nodes, LLM selects 1-3 relevant branches
     - Recursively load children, narrow selection at each depth
     - Up to 5 levels deep

4. **Merge & Deduplicate**
   - `merger.merge_results()` -> combine candidates from both sources
   - Weight formula: `final_score = atlas_score * 0.3 + tree_score * 0.7` (configurable)

5. **Content Loading**
   - `content_loader.load_candidates_content()` -> fetch full page text for top candidates

6. **LLM Reasoning Loop** (Up to 5 iterations)
   - `reasoner.check_sufficiency()` -> LLM reads query + content, evaluates if sufficient
   - If sufficient: generate final answer, return
   - If insufficient: recommend action (navigate_deeper, follow_reference, search_different_section)
   - Execute action (fetch more nodes, follow cross-refs) and loop

7. **Session Logging**
   - `session_manager.add_turn()` -> log turn to `retrieval_sessions`

8. **Return Answer**
   - `QueryResponse`: answer, confidence, trace (node hits, iterations, navigation path)

**State Management:**

- **In-Memory**: Configuration singleton (`src/config.Settings`), LLM provider cache
- **MongoDB Session State**: `retrieval_sessions` collection stores multi-turn conversation history per session
- **Transient**: Query analysis, retrieval candidates computed fresh per request (no caching)

## Key Abstractions

**PageIndex Tree:**
- Purpose: Represent document structure as hierarchical sections, not flat vectors
- Examples: `src/models/node.py` (Node model)
- Pattern: 3-pattern hierarchy - parent_node_id, child_node_ids, materialized_path
- Fields:
  - `parent_node_id`: Reference to parent (null for root)
  - `child_node_ids`: List of direct children
  - `materialized_path`: "/0001/0003/0006" for graph queries
  - `depth`, `sibling_order`, `is_leaf`: Navigation metadata
  - `title`, `summary`: Content descriptors
  - `start_page`, `end_page`: Page range
  - `keywords`, `content_type`: Enrichment metadata

**RetrievalCandidate:**
- Purpose: Represent a candidate node result with dual scores
- Example: `src/models/retrieval.py`
- Pattern: Merge point for Atlas Search and tree navigation scores
- Fields: node_id, atlas_score (0-100), tree_score (0-100), final_score, source (atlas|tree|both)

**LLMProvider:**
- Purpose: Abstract LLM backend with retry logic and provider switching
- Examples: `src/llm/provider.py` (Anthropic, OpenAI implementations)
- Pattern: Factory method `get_provider(provider_name, model)` + retry decorator
- Interface: `chat(messages: List[Message]) -> LLMResponse`

**ReasonerResponse:**
- Purpose: Structured output from LLM sufficiency check
- Example: `src/models/retrieval.py`
- Pattern: Union of answer (if sufficient) or next_action (if not)
- Fields: answer, confidence, sufficient, next_action (type, target_node_id, reasoning)

## Entry Points

**HTTP Entry Point:**
- Location: `src/api/main.py`
- Invokes: `src/api/server.create_app()` -> FastAPI app
- Startup: lifespan context manager initializes MongoDB, indexes, search backend

**Ingestion Entry Point:**
- Location: `src/api/routes/ingest.py: POST /ingest`
- Invokes: `src/ingestion/pipeline.page_index_main()`
- Async wrapper: runs ingestion in thread pool, returns document summary

**Query Entry Point:**
- Location: `src/api/routes/query.py: POST /query`
- Invokes: `src/retrieval/pipeline.retrieve()`
- Async: awaitable retrieval loop

**Stream Entry Point:**
- Location: `src/api/routes/stream.py: POST /query/stream`
- Invokes: `src/retrieval/pipeline.retrieve()` with streaming response
- Returns: Server-Sent Events (SSE) for real-time answer generation

**Frontend Pages:**
- `/documents`: `frontend/app/documents/page.tsx` -> list, upload
- `/chat`: `frontend/app/chat/page.tsx` -> query interface
- `/sessions`: `frontend/app/sessions/page.tsx` -> conversation history

## Error Handling

**Strategy:** Async-safe error handling with structured logging and HTTP status codes

**Patterns:**

- **API Errors**: HTTPException with status code and detail
  - 404: Document not found, session not found
  - 409: Document not ready (ingestion in progress)
  - 429: Rate limit exceeded
  - 500: Unexpected errors (logged to structlog)

- **LLM Errors** (`src/llm/provider.py`):
  - Retryable (rate limit, timeout, network): retry with exponential backoff
  - Non-retryable (auth, bad request): raise immediately as LLMAuthError or LLMBadRequestError
  - Max 10 retries, 1-60s backoff with jitter

- **Ingestion Errors**:
  - ToC detection failure: fall back from mode A -> B -> C
  - LLM tree generation failure: attempt 3 modes, log all errors to document.ingestion.errors

- **Middleware**:
  - `src/api/middleware.ErrorHandlingMiddleware`: catches unhandled exceptions, returns structured error

## Cross-Cutting Concerns

**Logging:**
- Framework: `structlog` (structured logging)
- Setup: `src/utils/logger.setup_logging()` at app startup
- Pattern: `get_logger(__name__)` per module, log as `logger.info("event_name", key=value)`
- Output: JSON to stdout/stderr (or configured handler)

**Validation:**
- Framework: Pydantic BaseModel + Field validators
- Locations: `src/api/models.py`, `src/models/`.*.py`
- Pattern: Request/response models auto-validate on parse; fields use alias for camelCase

**Authentication:**
- Not implemented (vectorless RAG assumes single-user or trusted environment)
- Future: Add API key or OAuth2 bearer token

**Rate Limiting:**
- Framework: `slowapi` (per IP address)
- Limit: 60 requests / minute (configurable)
- Applied globally in `src/api/server.create_app()`

**Database Transactions:**
- Not used (MongoDB async driver Motor + single-operation writes)
- Safe for read-heavy retrieval workloads

---

*Architecture analysis: 2026-02-17*
