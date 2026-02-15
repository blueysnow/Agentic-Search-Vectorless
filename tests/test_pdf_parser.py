"""Tests for src/ingestion/parsers/pdf_parser.py.

These tests use a tiny in-memory PDF generated with pypdf so no external
fixture files are needed.
"""

from io import BytesIO

import pypdf
import pytest

from src.ingestion.parsers.pdf_parser import PDFParseError, get_text_of_pages, parse_pdf


def _make_simple_pdf() -> BytesIO:
    """Create a 2-page blank in-memory PDF (no external deps beyond pypdf)."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output


def test_parse_pdf_pypdf2():
    pdf = _make_simple_pdf()
    pages = parse_pdf(pdf, backend="pypdf")
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert isinstance(pages[0].token_count, int)
    assert pages[0].content_hash.startswith("sha256:")


def test_parse_pdf_pymupdf():
    pdf = _make_simple_pdf()
    pages = parse_pdf(pdf, backend="PyMuPDF")
    assert len(pages) == 2
    assert pages[0].page_number == 1


def test_parse_pdf_invalid_backend():
    pdf = _make_simple_pdf()
    with pytest.raises(ValueError, match="Unsupported"):
        parse_pdf(pdf, backend="invalid")


def test_parse_pdf_corrupt_pypdf2():
    corrupt = BytesIO(b"this is not a pdf")
    with pytest.raises(PDFParseError, match="Failed to open PDF"):
        parse_pdf(corrupt, backend="pypdf")


def test_parse_pdf_corrupt_pymupdf():
    corrupt = BytesIO(b"this is not a pdf")
    with pytest.raises(PDFParseError, match="Failed to open PDF"):
        parse_pdf(corrupt, backend="PyMuPDF")


def test_get_text_of_pages_with_tags():
    pdf = _make_simple_pdf()
    pages = parse_pdf(pdf, backend="pypdf")
    text = get_text_of_pages(pages, 1, 2, tag=True)
    assert "<start_index_1>" in text
    assert "<end_index_2>" in text


def test_get_text_of_pages_without_tags():
    pdf = _make_simple_pdf()
    pages = parse_pdf(pdf, backend="pypdf")
    text = get_text_of_pages(pages, 1, 2, tag=False)
    assert "<start_index" not in text
