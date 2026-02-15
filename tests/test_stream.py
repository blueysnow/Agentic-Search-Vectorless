"""Tests for SSE streaming endpoint (POST /query/stream).

Covers:
- Successful streaming response with all SSE event types
- Error handling (missing document, failed retrieval)
- SSE event format validation (thinking, metadata, content, citations, done, error)
- Session creation/continuation
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
    return application


@pytest.fixture()
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse SSE text/event-stream response into list of event dicts."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data_str = line[len("data: ") :]
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pass
    return events


def _mock_retrieval_result():
    """Return a mock RetrievalResult with typical fields."""
    from src.retrieval.pipeline import RetrievalResult

    return RetrievalResult(
        answer="The revenue was $10M in 2024.",
        confidence=0.85,
        session_id="sess-123",
        trace={
            "atlas_hits": 3,
            "tree_hits": 2,
            "merged_candidates": 4,
            "iterations": 2,
            "navigation_path": ["0001", "0003", "0006"],
            "nodes_read": ["0003", "0006"],
        },
        candidates=[],
        query_analysis=None,
        iterations=2,
    )


# ---------------------------------------------------------------------------
# 1. Route exists and returns SSE content type
# ---------------------------------------------------------------------------


class TestStreamEndpointExists:
    """Verify the /query/stream route is registered and returns correct content type."""

    def test_stream_route_exists(self, client):
        """POST /query/stream should be a valid route (not 404/405)."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            # Should not be 404 or 405
            assert response.status_code != 404
            assert response.status_code != 405

    def test_stream_returns_event_stream_content_type(self, client):
        """Response should have text/event-stream content type."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            assert "text/event-stream" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 2. SSE event format validation
# ---------------------------------------------------------------------------


class TestSSEEventFormat:
    """Validate all SSE event types are emitted correctly."""

    def test_stream_emits_thinking_event(self, client):
        """Stream should include a thinking event with the query analysis step."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            thinking_events = [e for e in events if e.get("type") == "thinking"]
            assert len(thinking_events) >= 1

    def test_stream_emits_metadata_event(self, client):
        """Stream should include a metadata event with retrieval trace."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            metadata_events = [e for e in events if e.get("type") == "metadata"]
            assert len(metadata_events) == 1
            data = metadata_events[0].get("data", {})
            assert "atlas_hits" in data or "atlasHits" in data

    def test_stream_emits_content_event(self, client):
        """Stream should include a content event with the answer text."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            content_events = [e for e in events if e.get("type") == "content"]
            assert len(content_events) >= 1
            # Reconstruct answer from content events
            full_content = "".join(e.get("content", "") for e in content_events)
            assert "revenue" in full_content.lower() or "$10M" in full_content

    def test_stream_emits_done_event(self, client):
        """Stream should always end with a done event."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            done_events = [e for e in events if e.get("type") == "done"]
            assert len(done_events) == 1

    def test_stream_event_order(self, client):
        """Events should be in order: thinking -> metadata -> content -> citations -> done."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            types = [e.get("type") for e in events]

            # done must be last
            assert types[-1] == "done"
            # thinking must come before content
            if "thinking" in types and "content" in types:
                assert types.index("thinking") < types.index("content")


# ---------------------------------------------------------------------------
# 3. Error handling
# ---------------------------------------------------------------------------


class TestStreamErrorHandling:
    """Error conditions should emit error SSE events, not crash."""

    def test_missing_document_returns_error_event(self, client):
        """When document_id doesn't exist, stream should emit an error event."""
        with patch("src.api.routes.stream._find_document_status") as mock_find:
            mock_find.return_value = None

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "nonexistent"},
            )
            events = _parse_sse_events(response.text)
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) >= 1
            assert "not found" in error_events[0].get("content", "").lower()

    def test_document_not_ready_returns_error_event(self, client):
        """When document ingestion is not completed, emit error."""
        with patch("src.api.routes.stream._find_document_status") as mock_find:
            mock_find.return_value = {"ingestion": {"status": "processing"}}

            response = client.post(
                "/query/stream",
                json={"query": "test query", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) >= 1
            assert "not ready" in error_events[0].get("content", "").lower()

    def test_retrieval_failure_returns_error_event(self, client):
        """When retrieve() raises, stream should emit error + done."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.side_effect = RuntimeError("LLM timeout")
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            events = _parse_sse_events(response.text)
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) >= 1

    def test_empty_body_returns_error_event(self, client):
        """Missing required fields should emit an error SSE event (not 422)."""
        response = client.post("/query/stream", json={})
        # Streaming endpoint always returns 200 with SSE
        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1


# ---------------------------------------------------------------------------
# 4. Session handling
# ---------------------------------------------------------------------------


class TestStreamSessionHandling:
    """Verify session_id is passed through correctly."""

    def test_session_id_passed_to_retrieve(self, client):
        """When session_id is provided, it should be forwarded to retrieve()."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            client.post(
                "/query/stream",
                json={
                    "query": "What is the revenue?",
                    "documentId": "doc-1",
                    "sessionId": "sess-abc",
                },
            )
            # Verify retrieve was called with correct session_id
            call_kwargs = mock_retrieve.call_args
            assert call_kwargs is not None
            # session_id could be positional or keyword
            if call_kwargs.kwargs.get("session_id"):
                assert call_kwargs.kwargs["session_id"] == "sess-abc"
            else:
                # Check it was passed as keyword arg
                assert "sess-abc" in str(call_kwargs)

    def test_no_session_id_passes_none(self, client):
        """When session_id is omitted, retrieve gets None."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            client.post(
                "/query/stream",
                json={"query": "What is the revenue?", "documentId": "doc-1"},
            )
            call_kwargs = mock_retrieve.call_args
            assert call_kwargs is not None
            session_val = call_kwargs.kwargs.get("session_id")
            assert session_val is None


# ---------------------------------------------------------------------------
# 5. Frontend contract: request body matches what Next.js proxy sends
# ---------------------------------------------------------------------------


class TestFrontendContract:
    """The request body format must match what the Next.js proxy route sends."""

    def test_accepts_message_field(self, client):
        """Frontend sends 'message' not 'query'. Both should work."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={
                    "message": "What is the revenue?",
                    "document_ids": ["doc-1"],
                },
            )
            # Should work, not 422
            assert response.status_code != 422

    def test_accepts_document_ids_array(self, client):
        """Frontend sends document_ids as array. Use first one for retrieval."""
        with (
            patch("src.api.routes.stream._find_document_status") as mock_find,
            patch(
                "src.api.routes.stream.retrieve", new_callable=AsyncMock
            ) as mock_retrieve,
            patch("src.api.routes.stream.get_provider") as mock_provider,
        ):
            mock_find.return_value = {"ingestion": {"status": "completed"}}
            mock_retrieve.return_value = _mock_retrieval_result()
            mock_provider.return_value = MagicMock()

            response = client.post(
                "/query/stream",
                json={
                    "message": "What is the revenue?",
                    "document_ids": ["doc-1", "doc-2"],
                },
            )
            events = _parse_sse_events(response.text)
            done_events = [e for e in events if e.get("type") == "done"]
            assert len(done_events) == 1
