"""POST /ingest -- ingest a document (Phase 4).

Accepts both:
  - multipart/form-data file upload (from frontend UI)
  - JSON body with text content (from API clients)

Runs the ingestion pipeline, persists to MongoDB, and returns the document summary.
"""

from __future__ import annotations

import asyncio
import uuid
from io import BytesIO

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from src.api.models import IngestRequest, IngestResponse
from src.config import get_settings
from src.ingestion.parsers.pdf_parser import parse_pdf
from src.ingestion.pipeline import (
    page_index_main,
    save_document,
    save_nodes,
    save_pages,
    update_document_status,
)
from src.llm.provider import get_provider
from src.utils.logger import get_logger
from src.utils.tokens import count_tokens

logger = get_logger(__name__)

router = APIRouter()


def _parse_content(content: str) -> list[tuple[str, int]]:
    """Split raw text content into a page_list of (text, token_count) tuples.

    For plain text / markdown, we treat the entire content as a single page.
    For multi-page content separated by form-feeds, we split on them.
    """
    pages: list[str] = content.split("\f") if "\f" in content else [content]
    return [(page, count_tokens(page)) for page in pages if page.strip()]


async def _extract_text_from_upload(
    file: UploadFile,
) -> tuple[list[tuple[str, int]], str]:
    """Read an uploaded file and extract text pages.

    Returns:
        (page_list, doc_type) where page_list is [(text, token_count), ...]
    """
    file_bytes = await file.read()
    filename = file.filename or "untitled"
    lower = filename.lower()

    if lower.endswith(".pdf"):
        # Parse PDF using existing parser (supports BytesIO)
        parsed_pages = await asyncio.to_thread(
            parse_pdf, BytesIO(file_bytes), backend="pypdf"
        )
        page_list = [(p.text, p.token_count) for p in parsed_pages if p.text.strip()]
        return page_list, "pdf"

    elif lower.endswith((".md", ".markdown")):
        text = file_bytes.decode("utf-8", errors="replace")
        return _parse_content(text), "markdown"

    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="replace")
        return _parse_content(text), "text"

    else:
        # Try as text
        try:
            text = file_bytes.decode("utf-8")
            return _parse_content(text), "text"
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}. Accepted: .pdf, .md, .txt",
            )


async def _run_ingestion(
    document_id: str,
    name: str,
    doc_type: str,
    page_list: list[tuple[str, int]],
) -> IngestResponse:
    """Shared ingestion logic for both upload and JSON endpoints."""
    settings = get_settings()
    total_pages = len(page_list)
    total_tokens = sum(t for _, t in page_list)

    # Create document record (status: processing)
    await asyncio.to_thread(
        save_document,
        document_id=document_id,
        name=name,
        doc_type=doc_type,
        total_pages=total_pages,
        total_nodes=0,
        total_tokens=total_tokens,
        model=settings.llm_ingestion_model,
    )

    try:
        llm = get_provider(settings.llm_provider, model=settings.llm_ingestion_model)

        result = await page_index_main(page_list, llm, doc_name=name)

        structure = result.get("structure", [])
        total_nodes = await asyncio.to_thread(save_nodes, document_id, structure)
        await asyncio.to_thread(save_pages, document_id, page_list, structure)

        await asyncio.to_thread(update_document_status, document_id, "completed")
        logger.info(
            "ingest_complete",
            document_id=document_id,
            total_pages=total_pages,
            total_nodes=total_nodes,
        )

        return IngestResponse(
            document_id=document_id,
            name=name,
            status="completed",
            total_pages=total_pages,
            total_nodes=total_nodes,
            total_tokens=total_tokens,
        )

    except Exception as exc:
        try:
            await asyncio.to_thread(
                update_document_status, document_id, "failed", [str(exc)]
            )
        except Exception:
            logger.exception(
                "failed_to_update_document_status", document_id=document_id
            )
        logger.exception("ingest_failed", document_id=document_id)
        raise HTTPException(status_code=500, detail="Ingestion failed") from exc


@router.post("/upload", response_model=IngestResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    domain: str = Form(""),
    description: str = Form(""),
) -> IngestResponse:
    """Upload and ingest a document file (PDF, Markdown, or text)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    page_list, doc_type = await _extract_text_from_upload(file)
    if not page_list:
        raise HTTPException(
            status_code=400, detail="Document content is empty after parsing"
        )

    document_id = str(uuid.uuid4())
    name = file.filename.rsplit(".", 1)[0] if file.filename else "Untitled"

    return await _run_ingestion(document_id, name, doc_type, page_list)


@router.post("", response_model=IngestResponse, status_code=201)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Ingest a document from JSON body (API clients)."""
    page_list = _parse_content(request.content)
    if not page_list:
        raise HTTPException(
            status_code=400, detail="Document content is empty after parsing"
        )

    document_id = str(uuid.uuid4())
    return await _run_ingestion(document_id, request.name, request.doc_type, page_list)
