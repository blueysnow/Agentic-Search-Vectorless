"""PDF math extraction validation script.

Empirically tests how PyMuPDF and pymupdf4llm extract math symbols from PDF files.
Produces per-page character classification reports showing whether math symbols
extract as usable Unicode, private-use-area characters, or replacement characters.

Usage:
    uv run python scripts/validate_pdf_math.py path/to/file.pdf
    uv run python scripts/validate_pdf_math.py path/to/file.pdf --pages 1-10
    uv run python scripts/validate_pdf_math.py path/to/file.pdf --output-dir /tmp/reports
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import unicodedata

import fitz  # PyMuPDF
import pymupdf4llm

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Character classification
# ---------------------------------------------------------------------------

_RANGES = (
    # (low, high, label)
    (0x2200, 0x22FF, "math_operator"),
    (0xE000, 0xF8FF, "private_use"),
    (0xFFFF, 0xFFFF, "replacement"),  # U+FFFD handled separately
    (0xAC00, 0xD7AF, "hangul"),
    (0x0020, 0x007E, "ascii"),
    (0x2070, 0x209F, "superscript_subscript"),
    (0x2190, 0x21FF, "arrow"),
)


def classify_char(ch: str) -> str:
    """Classify a single character into a named category.

    Returns one of: 'math_operator', 'private_use', 'replacement', 'hangul',
    'ascii', 'superscript_subscript', 'arrow', 'other'.

    Uses unicodedata.category() to refine classification for letter-like math symbols.
    """
    if not ch:
        return "other"
    cp = ord(ch)
    if cp == 0xFFFD:
        return "replacement"
    for low, high, label in _RANGES:
        if low <= cp <= high:
            return label
    # Additional check: Unicode letter categories in math-adjacent blocks
    # (e.g. Mathematical Alphanumeric Symbols U+1D400-U+1D7FF)
    if 0x1D400 <= cp <= 0x1D7FF:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):
            return "math_operator"
    return "other"


# ---------------------------------------------------------------------------
# Backend 1 — PyMuPDF raw analysis
# ---------------------------------------------------------------------------


def _empty_page_stats() -> dict[str, Any]:
    return {
        "total_chars": 0,
        "by_category": {
            "math_operator": 0,
            "private_use": 0,
            "replacement": 0,
            "hangul": 0,
            "ascii": 0,
            "superscript_subscript": 0,
            "arrow": 0,
            "other": 0,
        },
        "fonts": [],
        "flagged": False,
        "verdict": "CLEAN",
    }


def _verdict(stats: dict[str, Any]) -> str:
    cats = stats["by_category"]
    if cats["private_use"] > 0 or cats["replacement"] > 0:
        return "DEGRADED"
    if cats["math_operator"] > 0:
        return "HAS_MATH_UNICODE"
    return "CLEAN"


def analyze_with_pymupdf(pdf_path: str, page_numbers: list[int]) -> list[dict[str, Any]]:
    """Analyze PDF pages using PyMuPDF rawdict extraction.

    Returns a list of per-page statistics dicts (1-indexed by page_number key).
    """
    doc = fitz.open(pdf_path)
    results: list[dict[str, Any]] = []

    for page_idx in page_numbers:
        if page_idx >= len(doc):
            continue

        page = doc[page_idx]
        stats = _empty_page_stats()
        stats["page_number"] = page_idx + 1

        fonts_seen: set[str] = set()
        try:
            raw = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in raw.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_name = span.get("font", "unknown")
                        fonts_seen.add(font_name)
                        for char_info in span.get("chars", []):
                            ch = char_info.get("c", "")
                            if not ch:
                                continue
                            cat = classify_char(ch)
                            stats["total_chars"] += 1
                            stats["by_category"][cat] += 1
        except Exception as exc:  # noqa: BLE001
            stats["error"] = str(exc)

        stats["fonts"] = sorted(fonts_seen)
        stats["flagged"] = (
            stats["by_category"]["private_use"] > 0 or stats["by_category"]["replacement"] > 0
        )
        stats["verdict"] = _verdict(stats)
        results.append(stats)

    doc.close()
    return results


# ---------------------------------------------------------------------------
# Backend 2 — pymupdf4llm markdown analysis
# ---------------------------------------------------------------------------


def analyze_with_pymupdf4llm(pdf_path: str, page_numbers: list[int]) -> list[dict[str, Any]]:
    """Analyze PDF pages using pymupdf4llm markdown extraction.

    Returns a list of per-page statistics dicts.
    """
    results: list[dict[str, Any]] = []

    try:
        # page_chunks=True yields a list of dicts, one per page
        chunks = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    except Exception as exc:  # noqa: BLE001
        # Fatal failure — return degraded entries for requested pages
        for page_idx in page_numbers:
            entry: dict[str, Any] = _empty_page_stats()
            entry["page_number"] = page_idx + 1
            entry["error"] = f"pymupdf4llm.to_markdown failed: {exc}"
            results.append(entry)
        return results

    # Build index: chunk index -> page number (1-based)
    # pymupdf4llm chunk dict has key "metadata" -> "page" (1-based)
    chunk_by_page: dict[int, dict] = {}
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        pg = meta.get("page", None)
        if pg is not None:
            chunk_by_page[pg] = chunk

    for page_idx in page_numbers:
        page_num = page_idx + 1
        stats = _empty_page_stats()
        stats["page_number"] = page_num

        chunk = chunk_by_page.get(page_num)
        if chunk is None:
            stats["error"] = f"No chunk found for page {page_num}"
            results.append(stats)
            continue

        try:
            text = chunk.get("text", "")
            # Classify every character in the markdown text
            for ch in text:
                cat = classify_char(ch)
                stats["total_chars"] += 1
                stats["by_category"][cat] += 1

            # Record first 500 chars for manual inspection
            stats["markdown_preview"] = text[:500]
        except Exception as exc:  # noqa: BLE001
            stats["error"] = str(exc)

        stats["flagged"] = (
            stats["by_category"]["private_use"] > 0 or stats["by_category"]["replacement"] > 0
        )
        stats["verdict"] = _verdict(stats)
        results.append(stats)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_table_row(
    page_num: int,
    total: int,
    math_op: int,
    priv: int,
    repl: int,
    verdict: str,
    backend: str,
) -> None:
    verdict_color = {"DEGRADED": "\033[91m", "HAS_MATH_UNICODE": "\033[92m", "CLEAN": ""}
    reset = "\033[0m" if verdict_color.get(verdict) else ""
    color = verdict_color.get(verdict, "")
    print(
        f"  {backend:<14} | pg {page_num:>4} | "
        f"total={total:>6} | math={math_op:>5} | priv={priv:>5} | repl={repl:>4} | "
        f"{color}{verdict}{reset}"
    )


def print_console_report(
    pymupdf_pages: list[dict[str, Any]],
    llm_pages: list[dict[str, Any]],
) -> None:
    """Print a human-readable side-by-side comparison table to stdout."""
    print()
    print("=" * 90)
    print("PDF Math Extraction Validation Report")
    print("=" * 90)
    print(f"  {'Backend':<14} | {'Page':>7} | {'Total':>8} | {'Math':>7} | {'Priv':>7} | {'Repl':>5} | Verdict")
    print("-" * 90)

    # Zip both lists (they should have same page coverage)
    by_page: dict[int, dict[str, dict]] = {}
    for p in pymupdf_pages:
        by_page.setdefault(p["page_number"], {})["pymupdf"] = p
    for p in llm_pages:
        by_page.setdefault(p["page_number"], {})["llm"] = p

    for page_num in sorted(by_page):
        pair = by_page[page_num]
        for backend_key, label in (("pymupdf", "PyMuPDF"), ("llm", "pymupdf4llm")):
            entry = pair.get(backend_key)
            if entry is None:
                continue
            cats = entry["by_category"]
            _print_table_row(
                page_num,
                entry["total_chars"],
                cats["math_operator"],
                cats["private_use"],
                cats["replacement"],
                entry.get("verdict", "CLEAN"),
                label,
            )
        print("-" * 90)


def _build_summary(
    pymupdf_pages: list[dict[str, Any]],
    llm_pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an overall summary comparing both backends."""

    def _agg(pages: list[dict[str, Any]]) -> dict[str, Any]:
        degraded = sum(1 for p in pages if p.get("verdict") == "DEGRADED")
        has_math = sum(1 for p in pages if p.get("verdict") == "HAS_MATH_UNICODE")
        clean = sum(1 for p in pages if p.get("verdict") == "CLEAN")
        total_priv = sum(p["by_category"]["private_use"] for p in pages)
        total_repl = sum(p["by_category"]["replacement"] for p in pages)
        total_math = sum(p["by_category"]["math_operator"] for p in pages)
        return {
            "pages_degraded": degraded,
            "pages_has_math_unicode": has_math,
            "pages_clean": clean,
            "total_private_use_chars": total_priv,
            "total_replacement_chars": total_repl,
            "total_math_operator_chars": total_math,
        }

    pymupdf_agg = _agg(pymupdf_pages)
    llm_agg = _agg(llm_pages)

    total_pages = len(pymupdf_pages)
    recommendation = "UNKNOWN"
    if total_pages > 0:
        degraded_frac = pymupdf_agg["pages_degraded"] / total_pages
        if degraded_frac == 0 and pymupdf_agg["total_math_operator_chars"] > 0:
            recommendation = "REGEX_VIABLE — math Unicode is usable; regex detection may work"
        elif degraded_frac > 0.5:
            recommendation = "LLM_RECONSTRUCTION_MANDATORY — majority of pages have degraded text"
        else:
            recommendation = "MIXED — inspect per-page data; LLM reconstruction likely needed for math pages"

    return {
        "pymupdf": pymupdf_agg,
        "pymupdf4llm": llm_agg,
        "recommendation": recommendation,
    }


def print_summary_section(
    pymupdf_pages: list[dict[str, Any]],
    llm_pages: list[dict[str, Any]],
) -> None:
    """Print overall assessment to stdout."""
    summary = _build_summary(pymupdf_pages, llm_pages)
    print()
    print("OVERALL ASSESSMENT")
    print("=" * 90)
    for backend_key, label in (("pymupdf", "PyMuPDF raw"), ("pymupdf4llm", "pymupdf4llm")):
        agg = summary[backend_key]
        print(f"  {label}:")
        print(f"    Degraded pages:       {agg['pages_degraded']}")
        print(f"    Pages with math Unicode: {agg['pages_has_math_unicode']}")
        print(f"    Clean pages:          {agg['pages_clean']}")
        print(f"    Total private_use chars: {agg['total_private_use_chars']}")
        print(f"    Total replacement chars: {agg['total_replacement_chars']}")
        print(f"    Total math_operator chars: {agg['total_math_operator_chars']}")
        print()
    print(f"  Recommendation: {summary['recommendation']}")
    print("=" * 90)
    print()


def write_json_report(
    pdf_path: str,
    total_pages: int,
    pymupdf_pages: list[dict[str, Any]],
    llm_pages: list[dict[str, Any]],
    output_dir: Path,
) -> Path:
    """Write machine-readable JSON report to output_dir/validate_report.json."""
    report = {
        "meta": {
            "script_version": __version__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filename": Path(pdf_path).name,
            "filepath": str(Path(pdf_path).resolve()),
            "total_pages_in_pdf": total_pages,
            "pages_analyzed": len(pymupdf_pages),
        },
        "pymupdf": pymupdf_pages,
        "pymupdf4llm": llm_pages,
        "summary": _build_summary(pymupdf_pages, llm_pages),
    }
    output_path = output_dir / "validate_report.json"
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return output_path


# ---------------------------------------------------------------------------
# Page range parsing
# ---------------------------------------------------------------------------


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse a page range spec (e.g. '1-10', '3', '1,3,5-8') into 0-based indices."""
    indices: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            for n in range(int(lo), int(hi) + 1):
                if 1 <= n <= total_pages:
                    indices.append(n - 1)
        else:
            n = int(part)
            if 1 <= n <= total_pages:
                indices.append(n - 1)
    return sorted(set(indices))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_pdf_math",
        description=(
            "Validate PDF math extraction quality using PyMuPDF and pymupdf4llm. "
            "Produces per-page character classification reports and a JSON report file."
        ),
    )
    parser.add_argument("pdf_path", help="Path to the PDF file to analyze")
    parser.add_argument(
        "--pages",
        metavar="RANGE",
        default=None,
        help="Page range to analyze (e.g. '1-10', '3', '1,3,5-8'). Default: all pages.",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default=".",
        help="Directory where validate_report.json will be written (default: current directory).",
    )
    args = parser.parse_args(argv)

    pdf_path = args.pdf_path
    if not Path(pdf_path).exists():
        print(f"ERROR: File not found: {pdf_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine page range
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Could not open PDF: {exc}", file=sys.stderr)
        return 1

    if args.pages:
        try:
            page_indices = parse_page_range(args.pages, total_pages)
        except ValueError as exc:
            print(f"ERROR: Invalid page range '{args.pages}': {exc}", file=sys.stderr)
            return 1
    else:
        page_indices = list(range(total_pages))

    print(f"Analyzing {Path(pdf_path).name} — {len(page_indices)} pages")

    # Run both backends
    print("  Running PyMuPDF rawdict analysis...")
    pymupdf_pages = analyze_with_pymupdf(pdf_path, page_indices)

    print("  Running pymupdf4llm markdown analysis...")
    llm_pages = analyze_with_pymupdf4llm(pdf_path, page_indices)

    # Report
    print_console_report(pymupdf_pages, llm_pages)
    print_summary_section(pymupdf_pages, llm_pages)

    report_path = write_json_report(pdf_path, total_pages, pymupdf_pages, llm_pages, output_dir)
    print(f"JSON report written to: {report_path}")

    # Print character name lookups for any private_use chars found
    for entry in pymupdf_pages:
        if entry["by_category"]["private_use"] > 0:
            print(
                f"  [PyMuPDF] Page {entry['page_number']}: "
                f"{entry['by_category']['private_use']} private-use chars "
                f"(fonts: {', '.join(entry['fonts'][:5])})"
            )
    # Provide unicodedata.name() lookups for math operators found (first unique 5)
    found_math: list[str] = []
    for entry in pymupdf_pages:
        if entry["by_category"]["math_operator"] > 0 and len(found_math) < 5:
            # Re-open doc briefly to sample math chars for name lookup
            found_math.append(f"page {entry['page_number']}: {entry['by_category']['math_operator']} math chars")
    if found_math:
        print("  Math Unicode characters detected — sample unicode categories:")
        for item in found_math:
            print(f"    {item}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
