"""Phase 5: REAL integration tests -- no mocks.

Uses real MongoDB Atlas and real Gemini LLM (via OpenAI-compatible endpoint).
All tests are marked @pytest.mark.integration so they can be excluded from CI.

Run:
    python -m pytest tests/test_real_integration.py -v -m integration

Skip (CI without services):
    python -m pytest tests/ -m "not integration"
"""

from __future__ import annotations

import os
import uuid
import warnings
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from src.api.server import create_app
from src.config import get_settings

# ---------------------------------------------------------------------------
# Real service configuration -- read from .env file (falls back to os env)
# ---------------------------------------------------------------------------
_env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

_REAL_MONGODB_URI = _env.get("MONGODB_URI") or os.environ.get("MONGODB_URI", "")
_REAL_DATABASE = _env.get("MONGODB_DATABASE") or os.environ.get(
    "MONGODB_DATABASE", "agentic_search_test"
)
_REAL_LLM_PROVIDER = "openai"
_REAL_LLM_MODEL = _env.get("LLM_INGESTION_MODEL") or os.environ.get(
    "LLM_INGESTION_MODEL", "gemini-2.0-flash"
)
_REAL_OPENAI_KEY = _env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
_REAL_OPENAI_BASE_URL = _env.get("OPENAI_BASE_URL") or os.environ.get(
    "OPENAI_BASE_URL", ""
)


def _services_available() -> bool:
    """Check if real MongoDB and LLM are reachable."""
    if not _REAL_MONGODB_URI or not _REAL_OPENAI_KEY:
        return False
    try:
        from pymongo import MongoClient

        c = MongoClient(_REAL_MONGODB_URI, serverSelectionTimeoutMS=5000)
        c.admin.command("ping")
        c.close()
    except Exception as exc:
        warnings.warn(f"Integration service check failed (MongoDB): {exc}")
        return False
    try:
        import openai

        client = openai.OpenAI(
            api_key=_REAL_OPENAI_KEY, base_url=_REAL_OPENAI_BASE_URL or None
        )
        client.chat.completions.create(
            model=_REAL_LLM_MODEL,
            messages=[{"role": "user", "content": "Say ok"}],
            max_tokens=5,
        )
    except Exception as exc:
        warnings.warn(f"Integration service check failed (LLM): {exc}")
        return False
    return True


# ---------------------------------------------------------------------------
# Lazy service check -- only runs when integration tests are collected
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def services_available():
    """Session-scoped check: are real MongoDB and LLM reachable?"""
    return _services_available()


@pytest.fixture(autouse=True)
def skip_without_services(request, services_available):
    """Auto-skip integration tests when real services are not available."""
    if request.node.get_closest_marker("integration") and not services_available:
        pytest.skip("Real MongoDB Atlas or Gemini LLM not reachable")


# ---------------------------------------------------------------------------
# Fixtures -- override conftest autouse env vars with real service config
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_env(monkeypatch, _set_test_env):
    """Point env vars at real services and reset singletons.

    Depends on ``_set_test_env`` (conftest autouse) so that this fixture runs
    AFTER the conftest defaults and can override them with real service values.
    """
    monkeypatch.setenv("MONGODB_URI", _REAL_MONGODB_URI)
    monkeypatch.setenv("MONGODB_DATABASE", _REAL_DATABASE)
    monkeypatch.setenv("LLM_PROVIDER", _REAL_LLM_PROVIDER)
    monkeypatch.setenv("LLM_INGESTION_MODEL", _REAL_LLM_MODEL)
    monkeypatch.setenv("LLM_RETRIEVAL_MODEL", _REAL_LLM_MODEL)
    monkeypatch.setenv("OPENAI_API_KEY", _REAL_OPENAI_KEY)
    monkeypatch.setenv("OPENAI_BASE_URL", _REAL_OPENAI_BASE_URL)

    get_settings.cache_clear()

    # Reset MongoDB client singleton so it picks up the new URI
    from src.db import client as db_client_mod

    old_client = db_client_mod._client
    db_client_mod._client = None

    yield

    # Teardown: close real client, restore previous singleton, clear settings cache
    if db_client_mod._client is not None:
        db_client_mod._client.close()
    db_client_mod._client = old_client
    get_settings.cache_clear()


@pytest.fixture()
def real_db(real_env):
    """Provide a DIRECT database handle (independent of the app singleton).

    Uses its own pymongo client to avoid conflicts with the TestClient lifespan
    which calls close_client() on shutdown.  Reads from primary to avoid
    replica-set lag on Atlas.  Cleans up all test collections after test.
    """
    from pymongo import MongoClient, ReadPreference

    client = MongoClient(
        _REAL_MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=30000,
    )
    db = client.get_database(_REAL_DATABASE, read_preference=ReadPreference.PRIMARY)
    yield db
    for col_name in ["documents", "nodes", "pages", "retrieval_sessions"]:
        db[col_name].delete_many({})
    client.close()


@pytest.fixture()
def real_llm(real_env):
    """Provide a real LLM provider (Gemini via OpenAI-compatible endpoint)."""
    from src.llm.provider import get_provider

    return get_provider("openai", model=_REAL_LLM_MODEL)


@pytest.fixture()
def real_client(real_env):
    """TestClient backed by real MongoDB + real LLM.

    Uses context manager to ensure the app lifespan (MongoDB connect/disconnect)
    runs with the real service env vars already in place.
    """
    from src.db import client as db_client_mod

    get_settings.cache_clear()
    # Ensure singleton is clean so lifespan creates a fresh connection
    db_client_mod._client = None
    application = create_app()
    with TestClient(application, raise_server_exceptions=False) as tc:
        yield tc


# ---------------------------------------------------------------------------
# 1. Real MongoDB connection
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealMongoDBConnection:
    """Verify live connectivity to MongoDB Atlas."""

    def test_real_mongodb_connection(self, real_db):
        """Ping the real MongoDB cluster and verify it responds."""
        from src.db.client import get_client

        result = get_client().admin.command("ping")
        assert result.get("ok") == 1

    def test_mongodb_write_read_delete(self, real_db):
        """Full CRUD cycle on a scratch collection in real MongoDB."""
        col = real_db["_integration_scratch"]
        doc_id = str(uuid.uuid4())

        col.insert_one({"_id": doc_id, "msg": "integration-test"})
        found = col.find_one({"_id": doc_id})
        assert found is not None
        assert found["msg"] == "integration-test"

        col.delete_one({"_id": doc_id})
        assert col.find_one({"_id": doc_id}) is None


# ---------------------------------------------------------------------------
# 2. Real LLM connection
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealLLMConnection:
    """Verify Gemini responds through the OpenAI-compatible endpoint."""

    def test_real_llm_connection(self, real_llm):
        """Sync chat call to Gemini -- simple arithmetic prompt."""
        from src.llm.provider import Message

        resp = real_llm.chat(
            [
                Message(
                    role="user", content="What is 2 + 2? Reply with just the number."
                )
            ],
        )
        assert resp.content.strip()
        assert "4" in resp.content

    @pytest.mark.asyncio
    async def test_real_llm_async(self, real_llm):
        """Async chat call to Gemini."""
        from src.llm.provider import Message

        resp = await real_llm.chat_async(
            [
                Message(
                    role="user", content="What is 3 + 3? Reply with just the number."
                )
            ],
        )
        assert resp.content.strip()
        assert "6" in resp.content


# ---------------------------------------------------------------------------
# 3. Real ingest: small document through the FULL pipeline
# ---------------------------------------------------------------------------

_SMALL_DOC_CONTENT = (
    "Acme Corporation Annual Report 2024\n\n"
    "Executive Summary\n\n"
    "Acme Corporation reported total revenue of $4.2 billion for fiscal year 2024, "
    "representing a 12% year-over-year increase. Net income was $680 million. "
    "The company launched three new product lines and expanded into Southeast Asia.\n"
    "\f"
    "Financial Highlights\n\n"
    "Revenue: $4.2 billion (up 12% YoY)\n"
    "Net Income: $680 million (up 21%)\n"
    "Operating Margin: 22.4%\n"
    "Free Cash Flow: $890 million\n"
    "Earnings Per Share: $3.42\n"
    "\f"
    "Risk Factors\n\n"
    "The company faces risks from macroeconomic uncertainty, cybersecurity threats, "
    "and intense competition in the technology sector. Regulatory changes in data "
    "privacy could increase compliance costs."
)


@pytest.mark.integration
class TestRealIngestSmallDoc:
    """Ingest a 3-page document through the REAL pipeline (real LLM + real MongoDB)."""

    @pytest.mark.timeout(120)
    def test_real_ingest_small_doc(self, real_client, real_db):
        """POST /ingest with real content -> real LLM tree building -> real MongoDB persistence.

        Verifies:
        - 201 status, completed status
        - Document record saved in MongoDB
        - Nodes saved in MongoDB
        - Pages saved in MongoDB
        """
        resp = real_client.post(
            "/ingest",
            json={
                "name": "acme_annual_report_2024.txt",
                "content": _SMALL_DOC_CONTENT,
                "docType": "text",
            },
        )

        assert resp.status_code == 201, f"Ingest failed: {resp.text}"
        body = resp.json()
        assert body["status"] == "completed"
        assert body["totalPages"] == 3
        assert body["totalNodes"] >= 1
        assert body["totalTokens"] > 0
        doc_id = body["documentId"]

        # Verify document persisted in real MongoDB (retry for Atlas replica lag)
        import time as _time

        doc = None
        for _ in range(5):
            doc = real_db["documents"].find_one({"documentId": doc_id})
            if doc is not None:
                break
            _time.sleep(1)
        assert doc is not None
        assert doc["name"] == "acme_annual_report_2024.txt"
        assert doc["ingestion"]["status"] == "completed"

        # Verify nodes were saved
        node_count = real_db["nodes"].count_documents({"documentId": doc_id})
        assert node_count >= 1, "Expected at least 1 node in MongoDB"

        # Verify pages were saved
        page_count = real_db["pages"].count_documents({"documentId": doc_id})
        assert page_count == 3, f"Expected 3 pages, got {page_count}"

        # Verify page content is correct
        page_1 = real_db["pages"].find_one({"documentId": doc_id, "pageNumber": 1})
        assert page_1 is not None
        assert "Acme Corporation" in page_1["content"]


# ---------------------------------------------------------------------------
# 4. Real query after ingest
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealQueryAfterIngest:
    """Ingest a document, then query it -- full end-to-end with real LLM + real MongoDB."""

    @pytest.mark.timeout(180)
    def test_real_query_after_ingest(self, real_client, real_db):
        """POST /ingest -> POST /query: verify the system returns a meaningful answer.

        Steps:
        1. Ingest the small document through the real pipeline
        2. Query "What was the total revenue?" against the ingested document
        3. Verify we get a non-empty answer back
        """
        # Step 1: Ingest
        ingest_resp = real_client.post(
            "/ingest",
            json={
                "name": "acme_report_query_test.txt",
                "content": _SMALL_DOC_CONTENT,
                "docType": "text",
            },
        )
        assert ingest_resp.status_code == 201, f"Ingest failed: {ingest_resp.text}"
        doc_id = ingest_resp.json()["documentId"]

        # Step 2: Query
        query_resp = real_client.post(
            "/query",
            json={
                "query": "What was the total revenue in fiscal year 2024?",
                "documentId": doc_id,
            },
        )
        assert query_resp.status_code == 200, f"Query failed: {query_resp.text}"
        body = query_resp.json()

        # Step 3: Verify answer
        assert body["answer"] is not None
        assert len(body["answer"]) > 0
        # The answer should mention the revenue figure from the document
        answer_lower = body["answer"].lower()
        assert (
            "4.2" in answer_lower
            or "4,200" in answer_lower
            or "4.2b" in answer_lower
            or "billion" in answer_lower
        ), f"Expected answer to mention $4.2 billion revenue, got: {body['answer']}"
        assert body["confidence"] > 0
        assert "trace" in body


# ---------------------------------------------------------------------------
# 5. Real session management (multi-turn)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealSessionManagement:
    """Real session creation, turn tracking, and history in MongoDB."""

    def test_real_session_create_and_turns(self, real_db):
        """Create session, add turns, verify history -- all against real MongoDB."""
        from src.retrieval.session_manager import (
            add_turn,
            create_session,
            get_conversation_history,
            get_session,
        )

        sid = f"integ-sess-{uuid.uuid4()}"

        # Create session
        session = create_session(document_id="doc-integ", session_id=sid)
        assert session.session_id == sid

        # Add turns
        add_turn(
            session_id=sid,
            query="What is revenue?",
            answer="Revenue is $4.2B",
            latency_ms=150,
        )
        add_turn(
            session_id=sid,
            query="How did it grow?",
            answer="It grew 12% year-over-year",
            latency_ms=200,
        )

        # Verify session state
        loaded = get_session(sid)
        assert loaded is not None
        assert loaded.summary.total_turns == 2
        assert len(loaded.turns) == 2
        assert loaded.turns[0].query == "What is revenue?"
        assert loaded.turns[0].answer == "Revenue is $4.2B"
        assert loaded.turns[1].query == "How did it grow?"
        assert loaded.turns[1].answer == "It grew 12% year-over-year"

        # Verify conversation history formatting
        history = get_conversation_history(sid)
        assert "What is revenue?" in history
        assert "Revenue is $4.2B" in history
        assert "How did it grow?" in history


# ---------------------------------------------------------------------------
# 6. Real query analysis with LLM
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealQueryAnalysis:
    """Real LLM-powered query analysis with Gemini."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_analyze_query_returns_structured_result(self, real_llm):
        """analyze_query should return a valid QueryAnalysis from real Gemini."""
        from src.retrieval.query_analyzer import analyze_query

        result = await analyze_query(
            "What was the total revenue in 2024?",
            "Annual Financial Report",
            "Acme Corp FY2024 annual report with financial data and risk factors",
            real_llm,
        )
        assert result.query_type in (
            "factual_lookup",
            "analytical",
            "navigational",
            "comparative",
        )
        assert len(result.keywords) > 0
        assert result.expected_content_type in (
            "section",
            "table",
            "figure",
            "appendix",
            "any",
        )


# ---------------------------------------------------------------------------
# 7. Real API health endpoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealAPIHealth:
    """Health endpoint against real MongoDB."""

    def test_health_returns_ok(self, real_client):
        resp = real_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["mongodb"] == "connected"


# ---------------------------------------------------------------------------
# 8. Real document listing
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealDocumentList:
    """Ingest a doc, then list documents -- verify it appears."""

    @pytest.mark.timeout(120)
    def test_ingest_then_list(self, real_client, real_db):
        """POST /ingest -> GET /documents -> verify the ingested doc appears."""
        ingest_resp = real_client.post(
            "/ingest",
            json={
                "name": "list_test_doc.txt",
                "content": "Simple test document for listing verification.",
                "docType": "text",
            },
        )
        assert ingest_resp.status_code == 201
        doc_id = ingest_resp.json()["documentId"]

        list_resp = real_client.get("/documents")
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["total"] >= 1

        doc_ids = [d["documentId"] for d in body["documents"]]
        assert doc_id in doc_ids


# ---------------------------------------------------------------------------
# 9. Cleanup verification
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealCleanup:
    """Verify test data cleanup works correctly."""

    def test_real_cleanup(self, real_db):
        """Insert test data, clean it up, verify collections are empty.

        This test validates that the real_db fixture's teardown
        (delete_many) works correctly on real MongoDB Atlas.
        """
        # Insert test data across all collections
        real_db["documents"].insert_one(
            {"documentId": "cleanup-test", "name": "cleanup"}
        )
        real_db["nodes"].insert_one({"documentId": "cleanup-test", "nodeId": "0001"})
        real_db["pages"].insert_one({"documentId": "cleanup-test", "pageNumber": 1})
        real_db["retrieval_sessions"].insert_one({"sessionId": "cleanup-sess"})

        # Verify data exists
        assert real_db["documents"].count_documents({"documentId": "cleanup-test"}) == 1
        assert real_db["nodes"].count_documents({"documentId": "cleanup-test"}) == 1
        assert real_db["pages"].count_documents({"documentId": "cleanup-test"}) == 1
        assert (
            real_db["retrieval_sessions"].count_documents({"sessionId": "cleanup-sess"})
            == 1
        )

        # Explicit cleanup (mimicking what the fixture teardown does)
        for col_name in ["documents", "nodes", "pages", "retrieval_sessions"]:
            real_db[col_name].delete_many({})

        # Verify cleanup
        assert real_db["documents"].count_documents({}) == 0
        assert real_db["nodes"].count_documents({}) == 0
        assert real_db["pages"].count_documents({}) == 0
        assert real_db["retrieval_sessions"].count_documents({}) == 0
