"""PDF text extraction -- adapted from reference utils.py get_page_tokens().

Supports two backends (same as reference): pypdf and PyMuPDF.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import tiktoken


logger = logging.getLogger(__name__)


class PDFParseError(Exception):
    """Raised when a PDF cannot be parsed (corrupt, encrypted, unsupported)."""


@dataclass
class ParsedPage:
    """One physical page extracted from a PDF."""

    page_number: int  # 1-indexed
    text: str
    token_count: int
    content_hash: str


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def parse_pdf(
    pdf_path: str | Path | BytesIO,
    *,
    model: str = "gpt-4o",
    backend: str = "pypdf",
) -> list[ParsedPage]:
    """Parse a PDF into a list of ParsedPage objects.

    Adapted from reference get_page_tokens() which returns (text, token_count)
    tuples per page. We add page_number and content_hash.

    Args:
        pdf_path: File path or BytesIO stream.
        model: Model name for tiktoken encoding.
        backend: "pypdf" or "PyMuPDF".

    Raises:
        PDFParseError: If the PDF is corrupt, encrypted, or otherwise unreadable.
        ValueError: If the backend is unsupported.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception as exc:
        raise PDFParseError(f"Invalid tiktoken model '{model}': {exc}") from exc

    pages: list[ParsedPage] = []

    if backend == "pypdf":
        import pypdf

        try:
            reader = pypdf.PdfReader(pdf_path)
            if reader.is_encrypted:
                raise PDFParseError(
                    "PDF is encrypted and cannot be read without a password"
                )
        except PDFParseError:
            raise
        except Exception as exc:
            raise PDFParseError(f"Failed to open PDF with pypdf: {exc}") from exc

        for page_num in range(len(reader.pages)):
            try:
                text = reader.pages[page_num].extract_text() or ""
            except Exception as exc:
                logger.warning(
                    "pypdf: failed to extract text from page %d: %s", page_num + 1, exc
                )
                text = ""
            token_count = len(enc.encode(text))
            pages.append(
                ParsedPage(
                    page_number=page_num + 1,
                    text=text,
                    token_count=token_count,
                    content_hash=_sha256(text),
                )
            )
    elif backend == "PyMuPDF":
        import pymupdf

        try:
            if isinstance(pdf_path, BytesIO):
                doc = pymupdf.open(stream=pdf_path, filetype="pdf")
            else:
                doc = pymupdf.open(str(pdf_path))
        except Exception as exc:
            raise PDFParseError(f"Failed to open PDF with PyMuPDF: {exc}") from exc

        try:
            for page_num, page in enumerate(doc):
                try:
                    text = page.get_text()
                except Exception as exc:
                    logger.warning(
                        "PyMuPDF: failed to extract text from page %d: %s",
                        page_num + 1,
                        exc,
                    )
                    text = ""
                token_count = len(enc.encode(text))
                pages.append(
                    ParsedPage(
                        page_number=page_num + 1,
                        text=text,
                        token_count=token_count,
                        content_hash=_sha256(text),
                    )
                )
        finally:
            doc.close()
    else:
        raise ValueError(f"Unsupported PDF backend: {backend}")

    return pages


def get_text_of_pages(
    pages: list[ParsedPage], start_page: int, end_page: int, *, tag: bool = True
) -> str:
    """Get concatenated text for a page range (1-indexed, inclusive).

    Adapted from reference get_text_of_pages().
    """
    parts: list[str] = []
    for p in pages:
        if start_page <= p.page_number <= end_page:
            if tag:
                parts.append(
                    f"<start_index_{p.page_number}>\n{p.text}\n<end_index_{p.page_number}>"
                )
            else:
                parts.append(p.text)
    return "\n".join(parts)


def get_pdf_title(pdf_path: str | Path) -> str:
    """Extract the PDF title from metadata. Falls back to 'Untitled'."""
    import pypdf

    try:
        reader = pypdf.PdfReader(str(pdf_path))
        meta = reader.metadata
        return meta.title if meta and meta.title else "Untitled"
    except Exception:
        return "Untitled"
