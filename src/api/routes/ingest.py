"""POST /ingest -- ingest a document (Phase 4).

Receives document content, runs the ingestion pipeline, persists to MongoDB,
and returns the document summary.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from src.api.models import IngestRequest, IngestResponse
from src.config import get_settings
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


@router.post("", response_model=IngestResponse, status_code=201)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Ingest a document: parse, build tree, persist to MongoDB."""
    settings = get_settings()
    document_id = str(uuid.uuid4())

    page_list = _parse_content(request.content)
    if not page_list:
        raise HTTPException(
            status_code=400, detail="Document content is empty after parsing"
        )

    total_pages = len(page_list)
    total_tokens = sum(t for _, t in page_list)

    # Create document record (status: processing) -- sync PyMongo, offload to thread
    await asyncio.to_thread(
        save_document,
        document_id=document_id,
        name=request.name,
        doc_type=request.doc_type,
        total_pages=total_pages,
        total_nodes=0,
        total_tokens=total_tokens,
        model=settings.llm_ingestion_model,
    )

    try:
        llm = get_provider(settings.llm_provider, model=settings.llm_ingestion_model)

        result = await page_index_main(page_list, llm, doc_name=request.name)

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
            name=request.name,
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
