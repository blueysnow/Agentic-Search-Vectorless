"""Phase 5: Mocked integration tests (fast, no real services required).

Uses mocked LLM + mocked MongoDB for fast CI.
For real-service integration tests, see test_real_integration.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.server import create_app


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def app():
    """Create a test FastAPI app with MongoDB lifespan mocked."""
    with patch("src.api.server.get_client") as mock_client:
        mock_client.return_value = MagicMock()
        mock_client.return_value.admin.command.return_value = {"ok": 1}
        application = create_app()
        yield application


@pytest.fixture()
def client(app):
    """TestClient for the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


def _mock_pipeline_result(total_nodes: int = 2):
    """Standard mock result from page_index_main."""
    return {
        "doc_name": "Test Document",
        "doc_description": "A test document for integration testing",
        "structure": [
            {
                "title": "Introduction",
                "node_id": "0001",
                "start_index": 1,
                "end_index": 1,
                "token_count": 50,
                "text": "This is the introduction section.",
                "summary": "Introduction to the document",
                "keywords": ["introduction"],
                "nodes": [
                    {
                        "title": "Background",
                        "node_id": "0002",
                        "start_index": 1,
                        "end_index": 1,
                        "token_count": 30,
                        "text": "Background information here.",
                        "summary": "Background details",
                        "keywords": ["background"],
                        "nodes": [],
                    }
                ],
            },
        ],
    }


class TestIngestFlow:

    def test_full_ingest_flow(self, client):
        """content -> _parse_content -> page_index_main -> save_document -> save_nodes -> save_pages -> update_status."""
        mock_result = _mock_pipeline_result()
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch("src.api.routes.ingest.save_document") as mock_save_doc,
            patch(
                "src.api.routes.ingest.save_nodes", return_value=2
            ) as mock_save_nodes,
            patch("src.api.routes.ingest.save_pages") as mock_save_pages,
            patch("src.api.routes.ingest.update_document_status") as mock_update,
        ):
            mock_prov.return_value = MagicMock()

            resp = client.post(
                "/ingest",
                json={
                    "name": "integration_test.txt",
                    "content": "Hello world. This is a test document.",
                    "docType": "text",
                },
            )

            assert resp.status_code == 201
            body = resp.json()
            assert body["status"] == "completed"
            assert body["name"] == "integration_test.txt"
            assert body["totalPages"] == 1
            assert body["totalNodes"] == 2
            assert "documentId" in body

            mock_save_doc.assert_called_once()
            mock_save_nodes.assert_called_once()
            mock_save_pages.assert_called_once()
            mock_update.assert_called_once()

    def test_ingest_with_form_feeds(self, client):
        """Multi-page content split on form-feeds."""
        mock_result = _mock_pipeline_result()
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_pipeline,
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.save_nodes", return_value=2),
            patch("src.api.routes.ingest.save_pages"),
            patch("src.api.routes.ingest.update_document_status"),
        ):
            mock_prov.return_value = MagicMock()

            content = "Page 1 content\fPage 2 content\fPage 3 content"
            resp = client.post(
                "/ingest",
                json={
                    "name": "multipage.txt",
                    "content": content,
                    "docType": "text",
                },
            )

            assert resp.status_code == 201
            body = resp.json()
            assert body["totalPages"] == 3

            call_args = mock_pipeline.call_args
            page_list = call_args[0][0]
            assert len(page_list) == 3
            assert page_list[0][0] == "Page 1 content"
            assert page_list[1][0] == "Page 2 content"
            assert page_list[2][0] == "Page 3 content"

    def test_ingest_empty_content(self, client):
        """Empty content after parsing -> 400 error."""
        resp = client.post(
            "/ingest",
            json={
                "name": "empty.txt",
                "content": "  ",
            },
        )
        assert resp.status_code in (400, 422)

    def test_ingest_pipeline_failure(self, client):
        """LLM failure -> document status 'failed'."""
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM crashed"),
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.update_document_status") as mock_update,
        ):
            mock_prov.return_value = MagicMock()

            resp = client.post(
                "/ingest",
                json={
                    "name": "failing.txt",
                    "content": "Some content",
                },
            )

            assert resp.status_code == 500
            assert resp.json()["detail"] == "Ingestion failed"

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][1] == "failed"
            assert isinstance(call_args[0][2], list)


class TestQueryFlow:

    def _mock_retrieval_result(
        self, answer="The answer is 42", confidence=0.95, session_id="sess-1"
    ):
        result = MagicMock()
        result.answer = answer
        result.confidence = confidence
        result.session_id = session_id
        result.trace = {
            "atlas_hits": 3,
            "tree_hits": 2,
            "merged_candidates": 4,
            "iterations": 2,
            "navigation_path": ["0001", "0002"],
            "nodes_read": ["0002"],
        }
        return result

    def test_full_query_flow(self, client):
        """POST /query -> analyze_query -> dual retrieval -> merge -> reason -> answer."""
        mock_result = self._mock_retrieval_result()
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
                json={
                    "query": "What is the total revenue?",
                    "documentId": "doc-123",
                },
            )

            assert resp.status_code == 200
            body = resp.json()
            assert body["answer"] == "The answer is 42"
            assert body["confidence"] == 0.95
            assert body["sessionId"] == "sess-1"
            assert body["trace"]["atlasHits"] == 3
            assert body["trace"]["treeHits"] == 2

    def test_query_document_not_found(self, client):
        """404 when document doesn't exist."""
        with patch("src.api.routes.query._find_document_status", return_value=None):
            resp = client.post(
                "/query",
                json={
                    "query": "What is revenue?",
                    "documentId": "nonexistent",
                },
            )
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Document not found"

    def test_query_document_not_ready(self, client):
        """409 when document is still processing."""
        with patch(
            "src.api.routes.query._find_document_status",
            return_value={"ingestion": {"status": "processing"}},
        ):
            resp = client.post(
                "/query",
                json={
                    "query": "What is revenue?",
                    "documentId": "doc-1",
                },
            )
            assert resp.status_code == 409
            assert "not ready" in resp.json()["detail"]


class TestMultiTurn:

    def test_multi_turn_conversation(self, client):
        """query -> follow-up query -> verify session has 2 turns."""
        result_1 = MagicMock()
        result_1.answer = "Revenue is $4.2B"
        result_1.confidence = 0.9
        result_1.session_id = "sess-multi"
        result_1.trace = {
            "atlas_hits": 2,
            "tree_hits": 1,
            "merged_candidates": 2,
            "iterations": 1,
            "navigation_path": [],
            "nodes_read": ["0001"],
        }

        result_2 = MagicMock()
        result_2.answer = "Revenue grew by 12% YoY"
        result_2.confidence = 0.85
        result_2.session_id = "sess-multi"
        result_2.trace = {
            "atlas_hits": 1,
            "tree_hits": 2,
            "merged_candidates": 3,
            "iterations": 2,
            "navigation_path": ["0001"],
            "nodes_read": ["0002"],
        }

        retrieve_mock = AsyncMock(side_effect=[result_1, result_2])

        with (
            patch(
                "src.api.routes.query._find_document_status",
                return_value={"ingestion": {"status": "completed"}},
            ),
            patch("src.api.routes.query.get_provider") as mock_prov,
            patch("src.api.routes.query.retrieve", retrieve_mock),
        ):
            mock_prov.return_value = MagicMock()

            resp1 = client.post(
                "/query",
                json={
                    "query": "What is the revenue?",
                    "documentId": "doc-1",
                    "sessionId": "sess-multi",
                },
            )
            assert resp1.status_code == 200
            assert resp1.json()["answer"] == "Revenue is $4.2B"

            resp2 = client.post(
                "/query",
                json={
                    "query": "How did it grow year over year?",
                    "documentId": "doc-1",
                    "sessionId": "sess-multi",
                },
            )
            assert resp2.status_code == 200
            assert resp2.json()["answer"] == "Revenue grew by 12% YoY"

            assert retrieve_mock.call_count == 2

    def test_session_retrieval(self, client):
        """query -> GET /sessions/{id} -> verify history."""
        from src.models.session import (
            RetrievalSession,
            RetrievalTrace,
            SessionSummary,
            Turn,
        )

        mock_session = RetrievalSession(
            session_id="sess-abc",
            document_id="doc-1",
            turns=[
                Turn(
                    turn_number=1,
                    query="What is revenue?",
                    answer="Revenue is $4.2B",
                    latency_ms=200,
                    retrieval_trace=RetrievalTrace(),
                ),
                Turn(
                    turn_number=2,
                    query="How did it grow?",
                    answer="It grew 12%",
                    latency_ms=300,
                    retrieval_trace=RetrievalTrace(),
                ),
            ],
            summary=SessionSummary(total_turns=2),
        )

        with patch("src.api.routes.sessions.get_session", return_value=mock_session):
            resp = client.get("/sessions/sess-abc")
            assert resp.status_code == 200
            body = resp.json()
            assert body["sessionId"] == "sess-abc"
            assert body["totalTurns"] == 2
            assert len(body["turns"]) == 2


class TestAPIIntegration:

    def test_api_ingest_then_query(self, client):
        """POST /ingest -> POST /query (with mocked pipelines)."""
        mock_ingest_result = _mock_pipeline_result()
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=mock_ingest_result,
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.save_nodes", return_value=2),
            patch("src.api.routes.ingest.save_pages"),
            patch("src.api.routes.ingest.update_document_status"),
        ):
            mock_prov.return_value = MagicMock()
            ingest_resp = client.post(
                "/ingest",
                json={"name": "report.txt", "content": "Revenue was $4.2 billion."},
            )
            assert ingest_resp.status_code == 201
            doc_id = ingest_resp.json()["documentId"]

        query_result = MagicMock()
        query_result.answer = "Revenue was $4.2 billion"
        query_result.confidence = 0.9
        query_result.session_id = ""
        query_result.trace = {
            "atlas_hits": 1,
            "tree_hits": 1,
            "merged_candidates": 1,
            "iterations": 1,
            "navigation_path": [],
            "nodes_read": ["0001"],
        }

        with (
            patch(
                "src.api.routes.query._find_document_status",
                return_value={"ingestion": {"status": "completed"}},
            ),
            patch("src.api.routes.query.get_provider") as mock_prov,
            patch(
                "src.api.routes.query.retrieve",
                new_callable=AsyncMock,
                return_value=query_result,
            ),
        ):
            mock_prov.return_value = MagicMock()
            query_resp = client.post(
                "/query", json={"query": "What was the revenue?", "documentId": doc_id}
            )
            assert query_resp.status_code == 200
            assert query_resp.json()["answer"] == "Revenue was $4.2 billion"

    def test_api_ingest_then_list(self, client):
        """POST /ingest -> GET /documents -> verify listed."""
        mock_result = _mock_pipeline_result()
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.save_nodes", return_value=2),
            patch("src.api.routes.ingest.save_pages"),
            patch("src.api.routes.ingest.update_document_status"),
        ):
            mock_prov.return_value = MagicMock()
            ingest_resp = client.post(
                "/ingest", json={"name": "test_doc.txt", "content": "Test content."}
            )
            assert ingest_resp.status_code == 201
            doc_id = ingest_resp.json()["documentId"]

        mock_doc = {
            "documentId": doc_id,
            "name": "test_doc.txt",
            "type": "text",
            "domain": "",
            "description": "",
            "totalPages": 1,
            "totalNodes": 2,
            "totalTokens": 10,
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
        with patch("src.api.routes.documents.documents_col") as mock_col:
            cursor_mock = MagicMock()
            cursor_mock.sort.return_value = cursor_mock
            cursor_mock.skip.return_value = cursor_mock
            cursor_mock.limit.return_value = cursor_mock
            cursor_mock.__iter__ = lambda self: iter([mock_doc])
            mock_col.return_value.find.return_value = cursor_mock
            mock_col.return_value.count_documents.return_value = 1

            list_resp = client.get("/documents")
            assert list_resp.status_code == 200
            assert list_resp.json()["total"] == 1

    def test_api_health(self, client):
        """GET /health -> 200 with status."""
        with patch("src.api.server.get_client") as mock_client:
            mock_client.return_value.admin.command.return_value = {"ok": 1}
            resp = client.get("/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert "mongodb" in body


class TestErrorRecovery:

    def test_ingest_llm_failure(self, client):
        """LLM error mid-pipeline -> document status 'failed' -> 500 response."""
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LLM timeout"),
            ),
            patch("src.api.routes.ingest.save_document"),
            patch("src.api.routes.ingest.update_document_status") as mock_update,
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/ingest", json={"name": "llm_fail.txt", "content": "Content"}
            )
            assert resp.status_code == 500
            assert resp.json()["detail"] == "Ingestion failed"
            assert "LLM timeout" not in resp.json()["detail"]
            mock_update.assert_called_once()
            assert mock_update.call_args[0][1] == "failed"

    def test_ingest_mongodb_save_failure(self, client):
        """MongoDB error during save -> proper error handling."""
        with (
            patch("src.api.routes.ingest.get_provider") as mock_prov,
            patch(
                "src.api.routes.ingest.page_index_main",
                new_callable=AsyncMock,
                return_value=_mock_pipeline_result(),
            ),
            patch("src.api.routes.ingest.save_document"),
            patch(
                "src.api.routes.ingest.save_nodes",
                side_effect=RuntimeError("MongoDB connection lost"),
            ),
            patch("src.api.routes.ingest.update_document_status") as mock_update,
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/ingest", json={"name": "mongo_fail.txt", "content": "Content"}
            )
            assert resp.status_code == 500
            assert resp.json()["detail"] == "Ingestion failed"
            mock_update.assert_called_once()
            assert mock_update.call_args[0][1] == "failed"

    def test_query_retrieval_failure(self, client):
        """Retrieval pipeline error -> 500 with generic message."""
        with (
            patch(
                "src.api.routes.query._find_document_status",
                return_value={"ingestion": {"status": "completed"}},
            ),
            patch("src.api.routes.query.get_provider") as mock_prov,
            patch(
                "src.api.routes.query.retrieve",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Retrieval crashed"),
            ),
        ):
            mock_prov.return_value = MagicMock()
            resp = client.post(
                "/query", json={"query": "What is revenue?", "documentId": "doc-1"}
            )
            assert resp.status_code == 500
            assert resp.json()["detail"] == "Query failed"
            assert "Retrieval crashed" not in resp.json()["detail"]
