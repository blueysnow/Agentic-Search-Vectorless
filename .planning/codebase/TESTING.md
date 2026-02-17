# Testing Patterns

**Analysis Date:** 2026-02-17

## Test Framework

**TypeScript/Frontend:**
- Runner: Vitest 2.1.0
- Config: `frontend/vitest.config.ts`
- Environment: jsdom (browser simulation)
- Assertion Library: Native Vitest assertions (via `expect()`)
- Testing utilities: `@testing-library/react` v16.1.0, `@testing-library/jest-dom` v6.9.1

**Python/Backend:**
- Runner: pytest 8.3+
- Config: `pyproject.toml` (test section)
- Assertion Library: pytest built-in assertions
- Async support: pytest-asyncio 0.24+ with `asyncio_mode = "auto"`
- Coverage: pytest-cov 6.0+

**Run Commands:**
```bash
# Frontend
npm test              # Run all tests
npm run test:watch   # Watch mode
npm run test:ui      # UI mode

# Backend
pytest               # Run all tests
pytest -v           # Verbose
pytest --cov        # Coverage report
pytest -k <pattern> # Filter tests
pytest -m integration  # Run only integration tests
```

## Test File Organization

**Frontend Location:**
- Directory: `frontend/tests/`
- Mirrors source structure under `tests/`:
  - `tests/api/` — API client tests
  - `tests/lib/` — Utility and hook tests
  - `tests/integration/` — End-to-end integration tests
- Naming: `*.test.ts` suffix
- Example paths:
  - `frontend/tests/lib/api/client.test.ts` (tests `frontend/lib/api/client.ts`)
  - `frontend/tests/lib/hooks/useDocuments.test.ts` (tests hooks)
  - `frontend/tests/integration/rem-fix-3.test.ts` (integration)

**Backend Location:**
- Directory: `tests/` at root level
- Naming: `test_*.py` prefix
- Example paths:
  - `tests/test_pipeline.py` (tests ingestion pipeline)
  - `tests/test_retrieval.py` (tests retrieval pipeline)
  - `tests/test_api.py` (tests API routes)
- Markers: Tests marked with `@pytest.mark.integration` for integration tests vs unit

**Test Structure:**

Frontend (Vitest):
```
frontend/tests/
├── setup.ts                          # Global setup (cleanup, jest-dom)
├── api/
│   ├── chat-stream.test.ts
│   └── chat-stream-timeout.test.ts
├── lib/
│   ├── api/
│   │   ├── client.test.ts
│   │   └── server.test.ts
│   ├── validation/
│   │   └── document.test.ts
│   ├── utils.test.ts
│   └── ...
└── integration/
    ├── rem-fix-2.test.ts
    └── rem-fix-3.test.ts
```

Backend (pytest):
```
tests/
├── test_api.py
├── test_pipeline.py
├── test_retrieval.py
├── test_enrichment.py
└── ... (25 test files)
```

## Test Structure

**Vitest Pattern (TypeScript):**
```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { apiClient } from '@/lib/api/client'

describe('Client API error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('fetch', () => {
    it('should preserve HTTP status code in error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Resource not found' }),
      })

      await expect(apiClient.getDocument('test')).rejects.toThrow(/404/)
    })
  })
})
```

Key structure elements:
- `describe()` for test suites (top-level and nested)
- `it()` for individual test cases
- `beforeEach()` / `afterEach()` for setup/teardown
- `vi.clearAllMocks()` to reset mocks before each test
- `vi.restoreAllMocks()` for cleanup after each test
- Async test cases use `async` and `await`
- Error testing: `await expect(...).rejects.toThrow(/pattern/)`

**pytest Pattern (Python):**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm.provider import LLMResponse

class TestPromptTemplates:
    """Verify all retrieval prompt templates exist and contain expected content."""

    def test_tree_navigation_prompt_importable(self):
        from src.llm.prompts.tree_navigation import TREE_NAVIGATION_PROMPT
        assert "tree" in TREE_NAVIGATION_PROMPT.lower()

def _mock_llm_provider(responses: list[str]):
    """Create a mock LLM provider that returns responses in order."""
    provider = MagicMock()
    call_count = {"i": 0}

    async def async_side_effect(messages, **kwargs):
        idx = min(call_count["i"], len(responses) - 1)
        call_count["i"] += 1
        return LLMResponse(content=responses[idx], finish_reason="finished")

    provider.chat_async = AsyncMock(side_effect=async_side_effect)
    return provider
```

Key structure elements:
- Class-based test organization with `Test*` prefix
- Helper functions with `_` prefix (e.g., `_mock_llm_provider()`)
- `@pytest.fixture` for reusable test data
- Direct imports from source modules
- Simple assertions using `assert`

## Mocking

**Vitest (TypeScript):**
Framework: `vi` from vitest
```typescript
const mockFetch = vi.fn()
global.fetch = mockFetch

// Setup mock responses
mockFetch.mockResolvedValueOnce({
  ok: true,
  json: async () => ({ documents: mockDocs, total: 1 }),
})

// Spy on existing methods
const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

// Clear/restore
vi.clearAllMocks()
vi.restoreAllMocks()
consoleSpy.mockRestore()
```

What to Mock:
- Global APIs: `fetch`, `XMLHttpRequest`, `global.fetch`
- External services: LLM providers, database clients (in unit tests)
- Side effects: `console.error`, `console.log`
- Browser APIs when needed

What NOT to Mock:
- Utility functions within test scope
- Configuration (unless testing config handling)
- Core business logic of unit being tested

**pytest (Python):**
Framework: `unittest.mock` (MagicMock, AsyncMock, patch)
```python
from unittest.mock import AsyncMock, MagicMock, patch

# Create mock
provider = MagicMock()
provider.chat_async = AsyncMock(side_effect=async_side_effect)

# Patch external dependencies
@patch('src.db.collections.documents_col')
def test_something(mock_col):
    mock_col.return_value = MagicMock()

# Verify calls
assert provider.chat_async.called
provider.chat_async.assert_called_with(expected_messages)
```

What to Mock:
- LLM providers (Anthropic, OpenAI) — use mock responses
- MongoDB collections and database operations (in unit tests)
- External API calls
- File I/O operations

What NOT to Mock:
- Pydantic models and data validation
- Configuration reading (use fixtures instead)
- Local utility functions

## Fixtures and Factories

**TypeScript/Vitest:**
No dedicated fixture framework used. Instead:
- Test data inlined in tests
- Mock factory functions created as helpers
- Example from `frontend/tests/lib/api/client.test.ts`:
```typescript
const mockDocs = [
  {
    documentId: 'doc-1',
    name: 'Test',
    type: 'pdf',
    totalPages: 5,
    totalNodes: 10,
    totalTokens: 100,
    ingestion: { status: 'completed', errors: [] },
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01'
  },
]
```

**pytest/Python:**
Use `conftest.py` for shared fixtures:
- Location: `conftest.py` at root
- Auto-used fixtures with `autouse=True`:
```python
@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Provide safe defaults for every test run."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "agentic_search_test")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    get_settings.cache_clear()
```

Fixture patterns:
- Environment setup: use `monkeypatch` to override settings
- Clear caches after env changes: `get_settings.cache_clear()`
- Test isolation by providing safe defaults for all external dependencies

## Coverage

**Frontend:**
- Command: `npm run test:ui` for visual coverage
- Requirements: Not enforced (no coverage threshold configured)
- Coverage tool: Vitest built-in coverage support

**Backend:**
- Command: `pytest --cov` (via pytest-cov)
- Requirements: Not enforced in CI/CD (no threshold set)
- Coverage excludes: Tests directory itself

## Test Types

**Frontend Unit Tests:**
- Scope: Individual functions, components, utilities
- Approach: Test in isolation with mocked dependencies
- Examples: `client.test.ts` (API client), `utils.test.ts` (utility functions)
- Setup: Mock fetch, console, or other side effects
- Teardown: Clear all mocks

**Frontend Integration Tests:**
- Scope: Multiple components working together, API integration
- Approach: More realistic setup, may use real async operations
- Located in: `frontend/tests/integration/`
- Examples: `rem-fix-3.test.ts`, `chat-stream.test.ts`
- Pattern: Test full request/response flow with mocked backend responses

**Backend Unit Tests:**
- Scope: Individual functions and modules
- Approach: Mock external dependencies (LLM, database)
- Naming: `test_*.py` with non-integration tests
- Setup: Use conftest.py fixture for environment

**Backend Integration Tests:**
- Scope: Full pipeline with real services (MongoDB, LLM)
- Marked with: `@pytest.mark.integration`
- Approach: Minimal mocking, test against real services
- Examples: `test_real_integration.py`, `test_integration.py`
- Requires: MongoDB running, API keys available

**E2E Tests:**
- Framework: Playwright v1.49.0 (installed but not heavily used)
- Not extensively configured in this codebase
- Coverage: Likely tested manually or in CI/CD separately

## Common Patterns

**Async Testing (Vitest):**
```typescript
it('should handle async operations', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ data: 'test' }),
  })

  await expect(apiClient.getDocument('test')).resolves.toBeDefined()
})
```

Key patterns:
- Mark test function with `async`
- Use `await` for async operations
- Use `.resolves` for resolved promises
- Use `.rejects` for rejected promises

**Async Testing (pytest):**
```python
async def test_retrieve_integration():
    """Integration test for full retrieval pipeline."""
    result = await retrieve(
        query="test query",
        document_id="doc-123",
        llm_provider=mock_provider,
    )
    assert result.answer is not None
```

Key patterns:
- Async automatically handled by pytest-asyncio with `asyncio_mode = "auto"`
- No need for special decorators
- Mark with `@pytest.mark.integration` for integration tests

**Error Testing (TypeScript):**
```typescript
it('should include request context in error', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 415,
    statusText: 'Unsupported Media Type',
    json: async () => ({ detail: 'Only PDF and Markdown supported' }),
  })

  try {
    await apiClient.uploadDocument(formData)
    expect.fail('Should have thrown')
  } catch (error) {
    expect((error as Error).message).toContain('415')
    expect((error as Error).message).toContain('PDF')
  }
})
```

Key patterns:
- Setup mock to return error state
- Use try/catch to verify exception thrown
- Use `expect.fail()` if exception not thrown
- Cast error to `Error` type for message assertions
- Verify error includes status code and context

**Error Testing (pytest):**
```python
def test_validate_truncate_empty():
    assert _validate_and_truncate([], 10) == []

def test_meta_processor_empty_after_filter():
    # When all items filtered, should fall back to process_no_toc
    # or raise RuntimeError if no mode left
    with pytest.raises(RuntimeError, match="no valid toc items"):
        result = meta_processor([], llm_provider)
```

Key patterns:
- Use `pytest.raises(ExceptionType, match="pattern")` context manager
- Simple assertions on return values
- Test edge cases (empty inputs, None values)

## Test Setup and Teardown

**Frontend Setup (`frontend/tests/setup.ts`):**
```typescript
import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})
```

- Imports jest-dom matchers globally
- Runs `cleanup()` after each test to unmount components
- Configured in vitest.config.ts: `setupFiles: ['./tests/setup.ts']`

**Backend Setup (`conftest.py`):**
```python
@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Provide safe defaults for every test run."""
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "agentic_search_test")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
```

- Automatically runs for every test via `autouse=True`
- Isolates tests by using test database (`agentic_search_test`)
- Provides dummy API keys to prevent real service calls
- Clears cached settings to force reload with new env vars

---

*Testing analysis: 2026-02-17*
