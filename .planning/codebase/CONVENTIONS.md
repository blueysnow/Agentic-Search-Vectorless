# Coding Conventions

**Analysis Date:** 2026-02-17

## Naming Patterns

**Files:**
- TypeScript/JavaScript: camelCase with kebab-case directories
  - Example: `lib/api/client.ts`, `lib/hooks/use-chat-stream.ts`
  - Test files: `.test.ts` or `.spec.ts` suffix
  - Pages: filename is route (e.g., `app/chat/page.tsx`)
- Python: snake_case with underscores
  - Example: `src/ingestion/tree_builder.py`, `src/llm/prompts/tree_building.py`
  - Test files: `test_*.py` prefix

**Functions/Methods:**
- TypeScript: camelCase for regular functions, lowercase for async functions without verb
  - Examples: `apiClient.getDocuments()`, `uploadDocumentWithProgress()`, `fetch<T>()`
  - Arrow functions common for callbacks
- Python: snake_case for all functions
  - Examples: `verify_toc()`, `process_toc_with_page_numbers()`, `_validate_and_truncate()`
  - Private/internal functions prefixed with underscore: `_get_document_info()`, `_mock_llm_provider()`

**Variables:**
- TypeScript: camelCase for standard variables, UPPER_SNAKE_CASE for constants
  - Example: `const DEFAULT_TIMEOUT = 10000`, `const baseUrl = API_CONFIG.baseUrl`
  - State and computed values: camelCase (e.g., `queryClient`, `mockDocs`)
- Python: snake_case for variables and constants
  - Module-level constants in UPPER_CASE: `logger = get_logger(__name__)`

**Types/Classes:**
- TypeScript: PascalCase for interfaces and types
  - Examples: `Document`, `QueryRequest`, `APIClient`, `IngestResponse`
- Python: PascalCase for Pydantic models and classes
  - Examples: `class Document(BaseModel)`, `class Ingestion(BaseModel)`, `class Settings(BaseSettings)`

## Code Style

**Formatting:**
- TypeScript: Prettier (implicit via ESLint Next.js config)
  - No explicit prettier.json found
  - Uses TypeScript strict mode via `tsconfig.json`
  - Configured for ES2020 target with bundler module resolution
- Python: Ruff formatter (configured in `pyproject.toml`)
  - Target version: py312
  - Line length: 120 characters
  - Default settings applied

**Linting:**
- TypeScript: ESLint with Next.js config
  - Config: `frontend/.eslintrc.json` extends `["next/core-web-vitals", "next/typescript"]`
  - Enforces Next.js best practices and TypeScript strict rules
- Python: Ruff linter configured in `pyproject.toml`
  - Target version: py312
  - Follows PEP 8 with enforced line length of 120 chars

## Import Organization

**TypeScript:**

Order by category (imports grouped):
1. External library imports (React, Next.js, third-party packages)
2. Type imports (`import type { ... }`)
3. Relative imports (local modules and utilities)

Example from `frontend/lib/api/client.ts`:
```typescript
import { API_CONFIG } from '../config'
import type {
  Document,
  DocumentFilters,
  IngestResponse,
  Session,
  QueryRequest,
  QueryResponse,
} from './types'
```

Path aliases:
- `@/*` maps to project root in `frontend/` for TypeScript modules
- Configured in `tsconfig.json`: `"paths": { "@/*": ["./*"] }`
- Used extensively: `import { apiClient } from '@/lib/api/client'`

**Python:**

Order by category:
1. `from __future__ import annotations` (always first)
2. Standard library imports
3. Third-party imports (pydantic, fastapi, motor, pymongo, etc.)
4. Local imports (src.* modules)

Example from `src/retrieval/pipeline.py`:
```python
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from src.config import get_settings
from src.db.collections import documents_col
from src.llm.provider import LLMProvider
# ... more imports
```

## Error Handling

**TypeScript:**

- Use try/catch for async operations and promise chains
- Error objects should include context (status codes, endpoint info)
- Log errors to console before rethrowing:
  ```typescript
  try {
    const errorBody = await res.json()
    errorDetail = errorBody.detail || errorDetail
  } catch (parseError) {
    console.error('Failed to parse error response:', parseError)
  }
  ```
- Check error type with `instanceof Error` and `error.name === 'AbortError'`
- Preserve HTTP status codes in error messages: `throw new Error(${errorDetail} (${res.status}))`

**Python:**

- Use `except Exception:` for broad error handling with `logger.exception()` for context
- Wrap separate concerns in individual try/except blocks for independence:
  ```python
  try:
    ensure_indexes()
  except Exception:
    logger.warning("ensure_indexes_failed", exc_info=True)
  ```
- Validate data before raising errors: `raise RuntimeError("Tree building failed: no valid toc items")`
- Use structured logging with key=value pairs for error context (see logging section below)
- For JSON parsing failures, log and continue with fallback behavior

## Logging

**Framework:**
- TypeScript: `console.error()` for client-side errors (no dedicated logger framework)
- Python: `structlog` with `logging` module
  - Logger created with `get_logger(__name__)` from `src/utils/logger.py`
  - Setup via `setup_logging()` on application startup

**Patterns:**

TypeScript (browser-based):
- `console.error(message, error)` for exceptions
- Used minimally, mainly for parse failures and network errors
- Example: `console.error('Failed to parse error response:', parseError)`

Python (structured logging):
- Use `logger.info()`, `logger.warning()`, `logger.exception()` with structured key=value context
- Event names are snake_case descriptive strings:
  ```python
  logger.info("starting_application")
  logger.info("mongodb_connection_verified")
  logger.warning("meta_processor_empty_after_filter", mode=mode)
  logger.warning("ensure_indexes_failed", exc_info=True)
  ```
- Include relevant metadata: `logger.info("indexes_ensured", count=len(idx_names))`
- Use `exc_info=True` to capture exception details in warnings/errors

## Comments

**When to Comment:**
- Document non-obvious algorithm behavior (tree building, verification steps)
- Reference issue tracking: `# SF-011 Fix: Add timeout with AbortController`
- Reference external docs or design specs: `# ref: page_index.py:950-1100`
- Clarify complex conditional logic or multi-step processes

**JSDoc/TSDoc:**
- Not extensively used in this codebase
- Function signatures rely on TypeScript type annotations
- Docstrings in Python used for modules and complex functions:
  ```python
  """Ingestion pipeline orchestrator (ref: page_index.py:950-1100).

  Three-mode orchestrator with fallback, full tree parsing, and MongoDB persistence.
  """
  ```

## Function Design

**Size:**
- Keep functions focused on single responsibility
- Python functions range from 10-50 lines for core logic
- TypeScript methods in APIClient class average 30-40 lines
- Longer functions decomposed with helper functions (e.g., `_validate_and_truncate`, `_get_document_info`)

**Parameters:**
- Use named parameters with defaults
- Python uses `*` for keyword-only args: `async def retrieve(query: str, document_id: str, *, session_id: str | None = None)`
- TypeScript uses options objects for multiple optional params
- Avoid parameter shadowing (e.g., private variables in class)

**Return Values:**
- Type annotations mandatory in TypeScript (e.g., `Promise<T>`, `Promise<Document[]>`)
- Python uses type hints: `-> RetrievalResult:`, `-> tuple[str, str]:`
- Generic functions use generics: `async fetch<T>(endpoint: string): Promise<T>`
- Container classes like `RetrievalResult` use `__slots__` for memory efficiency

## Module Design

**Exports:**
- TypeScript: Single default export for singletons (e.g., `export const apiClient = new APIClient()`)
- Named exports for types and utilities
- Python: Import by full path, no wildcard imports
  - Example: `from src.retrieval.pipeline import RetrievalResult`

**Barrel Files:**
- Used in Python: `src/models/__init__.py`, `src/ingestion/__init__.py`
- TypeScript: Minimal barrel files, mostly direct imports

**File Organization Patterns:**
- Separate concerns by domain: `src/ingestion/`, `src/retrieval/`, `src/llm/`, `src/api/`
- Utilities grouped: `src/utils/logger.py`, `src/utils/tokens.py`, `src/utils/json_utils.py`
- Configuration at root: `src/config.py`
- Models in dedicated directory: `src/models/`
- Parsers in sub-package: `src/ingestion/parsers/`
- Enrichment in sub-package: `src/ingestion/enrichment/`
- Frontend mirrors: `frontend/lib/api/`, `frontend/lib/hooks/`, `frontend/lib/utils/`, `frontend/lib/validation/`

## Class and Type Patterns

**Python Pydantic Models:**
- Use Field() with defaults and aliases for camelCase serialization
- Example from `src/models/document.py`:
  ```python
  document_id: str = Field(..., alias="documentId")
  created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="createdAt")
  model_config = {"populate_by_name": True}
  ```
- Include `to_mongo()` method for database serialization
- Always set `model_config = SettingsConfigDict(...)` for Settings classes

**TypeScript Classes:**
- Use private fields with `private readonly` for constants
- Example from `frontend/lib/api/client.ts`:
  ```typescript
  class APIClient {
    private baseUrl: string
    private readonly DEFAULT_TIMEOUT = 10000
  }
  ```
- Singleton pattern: create once and export as `export const apiClient = new APIClient()`

---

*Convention analysis: 2026-02-17*
