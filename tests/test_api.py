"""Tests for Phase 4: API & Integration (src/api/).

Tests cover:
- Pydantic request/response models (validation, serialization)
- FastAPI server setup (create_app, health check, CORS, route prefixes)
- Ingest route (POST /ingest)
- Query route (POST /query)
- Documents route (GET /documents, GET /documents/{id})
- Sessions route (GET /sessions/{id})
- Error handling middleware (structlog, safe validation detail)
- Rate limiting
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.models import (
    DocumentResponse,
    ErrorResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SessionResponse,
    TraceResponse,
    TurnResponse,
    MAX_QUERY_LENGTH,
)
from src.api.server import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Create a test FastAPI app with MongoDB mocked out."""
    with patch("src.api.server.get_client") as mock_client:
        mock_client.return_value = MagicMock()
        mock_client.return_value.admin.command.return_value = {"ok": 1}
        application = create_app()
        yield application


@pytest.fixture()
def client(app):
    """Create a TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# MODEL TESTS
# ===========================================================================


class TestIngestRequest:
    def test_valid_request(self):
        req = IngestRequest(name="test.pdf", content="Hello world", doc_type="pdf")
        assert req.name == "test.pdf"
        assert req.content == "Hello world"
        assert req.doc_type == "pdf"

    def test_default_doc_type(self):
        req = IngestRequest(name="doc", content="data")
        assert req.doc_type == "text"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            IngestRequest(name="", content="data")

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            IngestRequest(name="doc", content="")

    def test_invalid_doc_type_rejected(self):
        with pytest.raises(ValidationError):
            IngestRequest(name="doc", content="data", doc_type="docx")

    def test_camel_case_alias(self):
        req = IngestRequest(name="doc", content="data", docType="markdown")
        assert req.doc_type == "markdown"


class TestQueryRequest:
    def test_valid_request(self):
        req = QueryRequest(query="What is the revenue?", document_id="doc-1")
        assert req.query == "What is the revenue?"
        assert req.document_id == "doc-1"

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="", document_id="doc-1")

    def test_blank_query_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="   ", document_id="doc-1")

    def test_query_stripped(self):
        req = QueryRequest(query="  question?  ", document_id="doc-1")
        assert req.query == "question?"

    def test_long_query_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * (MAX_QUERY_LENGTH + 1), document_id="doc-1")

    def test_empty_document_id_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="question", document_id="")

    def test_session_id_optional(self):
        req = QueryRequest(query="question", document_id="doc-1")
        assert req.session_id is None

    def test_camel_case_aliases(self):
        req = QueryRequest(query="q", documentId="d1", sessionId="s1")
        assert req.document_id == "d1"
        assert req.session_id == "s1"


class TestIngestResponse:
    def test_serialization(self):
        resp = IngestResponse(
            document_id="abc",
            name="test",
            status="completed",
            total_pages=10,
            total_nodes=5,
            total_tokens=1000,
        )
        data = resp.model_dump(by_alias=True)
        assert data["documentId"] == "abc"
        assert data["totalPages"] == 10


class TestQueryResponse:
    def test_serialization(self):
        resp = QueryResponse(
            answer="42",
            confidence=0.95,
            session_id="s1",
            trace=TraceResponse(atlas_hits=3, tree_hits=2),
        )
        data = resp.model_dump(by_alias=True)
        assert data["sessionId"] == "s1"
        assert data["trace"]["atlasHits"] == 3


class TestDocumentResponse:
    def test_serialization(self):
        resp = DocumentResponse(
            document_id="d1",
            name="report.pdf",
            type="pdf",
            total_pages=50,
            total_nodes=20,
        )
        data = resp.model_dump(by_alias=True)
        assert data["documentId"] == "d1"
        assert data["totalNodes"] == 20


class TestSessionResponse:
    def test_serialization(self):
        now = datetime.now(UTC)
        resp = SessionResponse(
            session_id="s1",
            document_id="d1",
            turns=[TurnResponse(turn_number=1, query="q", answer="a", latency_ms=100)],
            total_turns=1,
            created_at=now,
        )
        data = resp.model_dump(by_alias=True)
        assert data["sessionId"] == "s1"
        assert len(data["turns"]) == 1
        assert data["turns"][0]["turnNumber"] == 1


class TestHealthResponse:
    def test_defaults(self):
        resp = HealthResponse()
        assert resp.status == "ok"
        assert resp.version == "0.1.0"


class TestErrorResponse:
    def test_serialization(self):
        resp = ErrorResponse(
            error="Not Found", detail="Document not found", status_code=404
        )
        data = resp.model_dump(by_alias=True)
        assert data["statusCode"] == 404


# ===========================================================================
# SERVER TESTS
# ===========================================================================


class TestCreateApp:
    def test_app_has_routes(self, app):
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_app_title(self, app):
        assert app.title == "Agentic Search API"

    def test_app_version(self, app):
        assert app.version == "0.1.0"

    def test_no_route_prefix_overlap(self, app):
        """Ingest uses /ingest, documents uses /documents -- no overlap."""
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        # POST /ingest should exist, not POST /documents
        assert "/ingest" in routes
        # GET /documents/{document_id} should exist
        assert "/documents/{document_id}" in routes

    def test_cors_disabled_by_default(self, app):
        """CORS middleware is not added when cors_origins is empty (default)."""
        from starlette.middleware.cors import CORSMiddleware

        middleware_classes = [
            type(m.cls) if hasattr(m, "cls") else type(m) for m in app.user_middleware
        ]
        # With empty cors_origins, CORSMiddleware should NOT be present
        assert CORSMiddleware not in middleware_classes


class TestHealthEndpoint:
    def test_health_check_connected(self, client):
        with patch("src.api.server.get_client") as mock_client:
            mock_client.return_value.admin.command.return_value = {"ok": 1}
            resp = client.get("/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["mongodb"] == "connected"

    def test_health_check_disconnected(self, client):
        with patch("src.api.server.get_client") as mock_client:
            mock_client.return_value.admin.command.side_effect = Exception("down")
            resp = client.get("/health")
            assert resp.status_code == 503
            body = resp.json()
            assert body["mongodb"] == "disconnected"
            assert body["status"] == "degraded"


# ===========================================================================
# INGEST ROUTE TESTS (now at /ingest)
# ===========================================================================


class TestIngestRoute:
    def test_ingest_success(self, client):
        mock_result = {
            "doc_name": "test",
            "doc_description": "A test doc",
            "structure": [
                {
                    "title": "Intro",
                    "node_id": "0001",
                    "start_index": 1,
                    "end_index": 1,
                    "token_count": 10,
                    "text": "Hello",
                    "nodes": [],
                },
            ],
        }
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.save_nodes", return_value=1),
            patch("src.api.routes.ingest.save_pages"),
            patch("src.api.routes.ingest.update_document_status"),
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/ingest",
                json={"name": "test.pdf", "content": "Hello world", "docType": "text"},
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["status"] == "completed"
            assert body["name"] == "test.pdf"
            assert "documentId" in body

    def test_ingest_empty_content(self, client):
        resp = client.post(
            "/ingest",
            json={"name": "test.pdf", "content": "", "docType": "text"},
        )
        assert resp.status_code == 422

    def test_ingest_missing_name(self, client):
        resp = client.post(
            "/ingest",
            json={"content": "data", "docType": "text"},
        )
        assert resp.status_code == 422

    def test_ingest_pipeline_failure(self, client):
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM failed"),
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.update_document_status"),
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/ingest",
                json={"name": "test", "content": "data"},
            )
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert detail == "Ingestion failed"
            # Must NOT leak internal exception info
            assert "LLM failed" not in detail

    def test_ingest_failure_status_update_protected(self, client):
        """If update_document_status throws in except block, it must not swallow the real error."""
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch("src.api.routes.ingest.save_document"),
            patch(
                "src.api.routes.ingest.update_document_status",
                side_effect=RuntimeError("DB down"),
            ),
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/ingest",
                json={"name": "test", "content": "data"},
            )
            # Should still return 500 with the generic message, not crash
            assert resp.status_code == 500
            assert resp.json()["detail"] == "Ingestion failed"


# ===========================================================================
# QUERY ROUTE TESTS
# ===========================================================================


class TestQueryRoute:
    def _make_mock_result(self):
        result = MagicMock()
        result.answer = "The answer is 42"
        result.confidence = 0.95
        result.session_id = "sess-1"
        result.trace = {
            "atlas_hits": 3,
            "tree_hits": 2,
            "merged_candidates": 4,
            "iterations": 1,
            "navigation_path": ["0001", "0003"],
            "nodes_read": ["0003"],
        }
        return result

    def test_query_success(self, client):
        mock_result = self._make_mock_result()
        with (
            patch(
                "src.api.routes.query._find_document_status",
                return_value={"ingestion": {"status": "completed"}},
            ),
            patch("src.api.routes.query.get_provider") as mock_prov,
            patch(
                "src.api.routes.query.retrieve",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            mock_prov.return_value = MagicMock()

            resp = client.post(
                "/query",
                json={"query": "What is revenue?", "documentId": "doc-1"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["answer"] == "The answer is 42"
            assert body["confidence"] == 0.95
            assert body["trace"]["atlasHits"] == 3

    def test_query_document_not_found(self, client):
        with patch("src.api.routes.query._find_document_status", return_value=None):
            resp = client.post(
                "/query",
                json={"query": "question", "documentId": "missing-id"},
            )
            assert resp.status_code == 404
            detail = resp.json()["detail"]
            assert detail == "Document not found"
            # Must NOT leak the document_id
            assert "missing-id" not in detail

    def test_query_document_not_ready(self, client):
        with patch(
            "src.api.routes.query._find_document_status",
            return_value={"ingestion": {"status": "processing"}},
        ):
            resp = client.post(
                "/query",
                json={"query": "question", "documentId": "doc-1"},
            )
            assert resp.status_code == 409
            assert "not ready" in resp.json()["detail"]

    def test_query_validation_error(self, client):
        resp = client.post("/query", json={"query": "", "documentId": "doc-1"})
        assert resp.status_code == 422

    def test_query_pipeline_failure(self, client):
        with (
            patch(
                "src.api.routes.query._find_document_status",
                return_value={"ingestion": {"status": "completed"}},
            ),
            patch("src.api.routes.query.get_provider") as mock_prov,
            patch(
                "src.api.routes.query.retrieve",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM boom"),
            ),
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/query",
                json={"query": "question", "documentId": "doc-1"},
            )
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert detail == "Query failed"
            # Must NOT leak internal exception info
            assert "LLM boom" not in detail


# ===========================================================================
# DOCUMENTS ROUTE TESTS
# ===========================================================================


class TestDocumentsRoute:
    def _make_doc(self, doc_id: str = "d1") -> dict:
        return {
            "documentId": doc_id,
            "name": "report.pdf",
            "type": "pdf",
            "domain": "finance",
            "description": "Quarterly report",
            "totalPages": 50,
            "totalNodes": 20,
            "totalTokens": 5000,
            "ingestion": {
                "status": "completed",
                "model": "gpt-4o-mini",
                "startedAt": datetime.now(UTC),
                "completedAt": datetime.now(UTC),
                "errors": [],
            },
            "createdAt": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
        }

    def test_list_documents(self, client):
        mock_docs = [self._make_doc("d1"), self._make_doc("d2")]
        with patch("src.api.routes.documents.documents_col") as mock_col:
            cursor_mock = MagicMock()
            cursor_mock.sort.return_value = cursor_mock
            cursor_mock.skip.return_value = cursor_mock
            cursor_mock.limit.return_value = cursor_mock
            cursor_mock.__iter__ = lambda self: iter(mock_docs)
            mock_col.return_value.find.return_value = cursor_mock
            mock_col.return_value.count_documents.return_value = 2

            resp = client.get("/documents")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 2
            assert len(body["documents"]) == 2

    def test_list_documents_with_filters(self, client):
        with patch("src.api.routes.documents.documents_col") as mock_col:
            cursor_mock = MagicMock()
            cursor_mock.sort.return_value = cursor_mock
            cursor_mock.skip.return_value = cursor_mock
            cursor_mock.limit.return_value = cursor_mock
            cursor_mock.__iter__ = lambda self: iter([])
            mock_col.return_value.find.return_value = cursor_mock
            mock_col.return_value.count_documents.return_value = 0

            resp = client.get("/documents?domain=finance&status=completed")
            assert resp.status_code == 200

            # Verify the query filter was passed
            call_args = mock_col.return_value.find.call_args
            query_filter = call_args[0][0]
            assert query_filter["domain"] == "finance"
            assert query_filter["ingestion.status"] == "completed"

    def test_get_document_success(self, client):
        doc = self._make_doc("d1")
        with patch("src.api.routes.documents.documents_col") as mock_col:
            mock_col.return_value.find_one.return_value = doc
            resp = client.get("/documents/d1")
            assert resp.status_code == 200
            body = resp.json()
            assert body["documentId"] == "d1"
            assert body["name"] == "report.pdf"
            assert body["ingestion"]["status"] == "completed"

    def test_get_document_not_found(self, client):
        with patch("src.api.routes.documents.documents_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            resp = client.get("/documents/missing-id")
            assert resp.status_code == 404

    def test_list_documents_limit_over_200_rejected(self, client):
        """Verify that limit > 200 is rejected by Query validation."""
        resp = client.get("/documents?limit=201")
        assert resp.status_code == 422

    def test_list_documents_limit_zero_rejected(self, client):
        """Verify that limit=0 is rejected (ge=1)."""
        resp = client.get("/documents?limit=0")
        assert resp.status_code == 422

    def test_list_documents_negative_skip_rejected(self, client):
        """Verify that negative skip is rejected (ge=0)."""
        resp = client.get("/documents?skip=-1")
        assert resp.status_code == 422

    def test_get_document_invalid_id_rejected(self, client):
        """Verify that document_id with invalid chars is rejected by Path validation."""
        resp = client.get("/documents/bad%20id%21%40%23")
        assert resp.status_code == 422

    def test_get_document_generic_404(self, client):
        """Verify that 404 does NOT leak the document_id."""
        with patch("src.api.routes.documents.documents_col") as mock_col:
            mock_col.return_value.find_one.return_value = None
            resp = client.get("/documents/some-missing-id")
            assert resp.status_code == 404
            detail = resp.json()["detail"]
            assert detail == "Document not found"
            assert "some-missing-id" not in detail


# ===========================================================================
# SESSIONS ROUTE TESTS
# ===========================================================================


class TestSessionsRoute:
    def test_get_session_success(self, client):
        from src.models.session import (
            RetrievalSession,
            Turn,
            RetrievalTrace,
            SessionSummary,
        )

        mock_session = RetrievalSession(
            session_id="s1",
            document_id="d1",
            turns=[
                Turn(
                    turn_number=1,
                    query="What is revenue?",
                    answer="42",
                    latency_ms=150,
                    retrieval_trace=RetrievalTrace(),
                ),
            ],
            summary=SessionSummary(total_turns=1),
        )

        with patch("src.api.routes.sessions.get_session", return_value=mock_session):
            resp = client.get("/sessions/s1")
            assert resp.status_code == 200
            body = resp.json()
            assert body["sessionId"] == "s1"
            assert body["documentId"] == "d1"
            assert len(body["turns"]) == 1
            assert body["turns"][0]["query"] == "What is revenue?"
            assert body["turns"][0]["answer"] == "42"

    def test_get_session_not_found(self, client):
        with patch("src.api.routes.sessions.get_session", return_value=None):
            resp = client.get("/sessions/missing")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"]

    def test_get_session_invalid_id_rejected(self, client):
        """Session ID with invalid chars is rejected by Path validation."""
        resp = client.get("/sessions/bad%20id%21%40")
        assert resp.status_code == 422


# ===========================================================================
# MIDDLEWARE TESTS
# ===========================================================================


class TestErrorHandlingMiddleware:
    def test_unhandled_exception_returns_500(self, client):
        """Verify that an unhandled exception in a route returns structured 500."""
        with patch("src.api.routes.documents.documents_col") as mock_col:
            mock_col.return_value.find_one.side_effect = RuntimeError("Unexpected!")
            resp = client.get("/documents/test-id")
            assert resp.status_code == 500
            body = resp.json()
            assert body["error"] == "Internal Server Error"

    def test_mongodb_connection_failure_returns_503(self, client):
        from pymongo.errors import ConnectionFailure

        with patch("src.api.routes.documents.documents_col") as mock_col:
            mock_col.return_value.find_one.side_effect = ConnectionFailure(
                "Connection refused"
            )
            resp = client.get("/documents/test-id")
            assert resp.status_code == 503
            body = resp.json()
            assert body["error"] == "Service Unavailable"


class TestSafeValidationDetail:
    def test_only_loc_and_msg_returned(self):
        from src.api.middleware import _safe_validation_detail

        try:
            QueryRequest(query="", document_id="doc-1")
        except ValidationError as exc:
            result = _safe_validation_detail(exc)
            for entry in result:
                assert set(entry.keys()) == {"loc", "msg"}
                # Must not contain ctx, url, or input
                assert "ctx" not in entry
                assert "url" not in entry
                assert "input" not in entry

    def test_loc_is_list(self):
        from src.api.middleware import _safe_validation_detail

        try:
            QueryRequest(query="", document_id="doc-1")
        except ValidationError as exc:
            result = _safe_validation_detail(exc)
            for entry in result:
                assert isinstance(entry["loc"], list)


# ===========================================================================
# INGEST PARSE CONTENT TESTS
# ===========================================================================


class TestParseContent:
    def test_single_page(self):
        from src.api.routes.ingest import _parse_content

        result = _parse_content("Hello world")
        assert len(result) == 1
        assert result[0][0] == "Hello world"
        assert result[0][1] > 0

    def test_multi_page_form_feed(self):
        from src.api.routes.ingest import _parse_content

        result = _parse_content("Page 1\fPage 2\fPage 3")
        assert len(result) == 3

    def test_empty_pages_filtered(self):
        from src.api.routes.ingest import _parse_content

        result = _parse_content("Content\f\f\fMore content")
        assert len(result) == 2

    def test_empty_string(self):
        from src.api.routes.ingest import _parse_content

        result = _parse_content("")
        assert len(result) == 0


# ===========================================================================
# REVIEWER FIX TESTS
# ===========================================================================


class TestContentMaxLength:
    def test_content_over_max_rejected(self):
        from src.api.models import MAX_CONTENT_LENGTH

        with pytest.raises(ValidationError):
            IngestRequest(name="doc", content="x" * (MAX_CONTENT_LENGTH + 1))

    def test_content_within_limit_accepted(self):
        req = IngestRequest(name="doc", content="x" * 1000)
        assert len(req.content) == 1000


class TestSanitizeErrors:
    def test_file_paths_stripped(self):
        from src.api.routes.documents import _sanitize_errors

        errors = [
            "Failed to parse /Users/rom.iluz/Dev/project/src/file.py: syntax error",
            "No such file: /home/user/data/input.pdf",
        ]
        sanitized = _sanitize_errors(errors)
        assert "/Users/" not in sanitized[0]
        assert "/home/" not in sanitized[1]
        assert "[path]" in sanitized[0]
        assert "[path]" in sanitized[1]

    def test_no_paths_unchanged(self):
        from src.api.routes.documents import _sanitize_errors

        errors = ["LLM timeout after 30s", "Connection refused"]
        sanitized = _sanitize_errors(errors)
        assert sanitized == errors

    def test_empty_errors(self):
        from src.api.routes.documents import _sanitize_errors

        assert _sanitize_errors([]) == []


# ===========================================================================
# HUNTER FIX REGRESSION TESTS
# ===========================================================================


class TestHunterFixes:
    def test_startup_fails_on_mongo_unreachable(self):
        """HUNT-001: App must fail to start if MongoDB is unreachable at startup."""
        with patch("src.api.server.get_client") as mock_client:
            mock_client.return_value.admin.command.side_effect = ConnectionError(
                "refused"
            )
            application = create_app()
            with pytest.raises(ConnectionError):
                with TestClient(application, raise_server_exceptions=True):
                    pass  # lifespan re-raises → startup failure

    def test_rate_limit_generic_message(self, client):
        """HUNT-007: Rate limit response must not expose configuration details."""
        from src.api.server import _rate_limit_handler

        mock_request = MagicMock()
        mock_exc = MagicMock()
        mock_exc.detail = "60 per 1 minute"
        resp = _rate_limit_handler(mock_request, mock_exc)
        import json

        body = json.loads(resp.body)
        assert resp.status_code == 429
        assert body["detail"] == "Rate limit exceeded"
        # Must NOT leak rate limit config string
        assert "60 per 1 minute" not in body["detail"]

    def test_session_not_found_generic_message(self, client):
        """HUNT-006: Session 404 must not include session_id."""
        with patch("src.api.routes.sessions.get_session", return_value=None):
            resp = client.get("/sessions/secret-session-id")
            assert resp.status_code == 404
            detail = resp.json()["detail"]
            assert detail == "Session not found"
            assert "secret-session-id" not in detail
