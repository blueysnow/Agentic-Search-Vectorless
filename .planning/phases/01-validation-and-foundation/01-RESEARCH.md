# Phase 1: Validation and Foundation - Research

**Researched:** 2026-02-17
**Domain:** PDF math extraction (PyMuPDF / pymupdf4llm), JSON backslash escaping, Python regex math detection
**Confidence:** HIGH (codebase direct inspection + verified library docs + prior project research available)

---

## Summary

Phase 1 has two independent work streams that can be planned separately. The first (Plan 01-01) is an empirical investigation: run real 수능 PDF samples through PyMuPDF `get_text()` and pymupdf4llm `to_markdown()`, then write a documented report of what actually comes out. This is primarily a scripting + analysis task — no architectural decisions can be made until the report exists. The second (Plan 01-02) is a code change + module creation: fix the known LaTeX backslash bug in `src/utils/json_utils.py` and create a new `src/ingestion/math_extractor.py` module with unit tests.

The critical empirical unknown for this project is whether Korean 수능 PDFs store math in the text layer as recognizable Unicode or as private-use-area garbage. Prior research (`.planning/research/PITFALLS.md`) has already documented the theoretical failure modes with high confidence. Phase 1 must produce an empirical answer that settles which path Phase 2 takes. The `json_utils.py` fix and `math_extractor.py` creation are straightforward and can proceed independently of the empirical findings.

**Primary recommendation:** Build Plan 01-01 as a standalone validation script that produces machine-readable JSON output alongside a human-readable report; plan 01-02 as pure code tasks with no external dependencies.

---

## Standard Stack

### Core (already in pyproject.toml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF | `>=1.24` | PDF text extraction via `page.get_text()` | Already installed; `get_text("dict")` exposes per-character font metadata needed for symbol analysis |
| pymupdf4llm | `0.3.4` (latest as of 2026-02-14) | Markdown extraction from PDF pages | Already in project intent (VAL-02); wraps PyMuPDF into LLM-ready Markdown output |
| pypdf | `>=4.0` | Alternative PDF text extraction backend | Already installed; used as baseline comparison in validation |
| pytest | `>=8.3` | Unit test framework | Already used; 471 existing backend tests |
| re (stdlib) | stdlib | Regex-based math pattern detection | No extra dependency; sufficient for `$...$`, `$$...$$`, `\begin{equation}` detection in text that already contains LaTeX |

**Note:** `pymupdf4llm` is NOT currently in `pyproject.toml`. It must be added.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fitz` (PyMuPDF alias) | same as PyMuPDF | Low-level page inspection via `get_text("dict")` or `get_text("rawdict")` | When diagnosing character-level font encoding in validation script |
| `json` (stdlib) | stdlib | JSON parsing in json_utils.py | Already used |
| `unicodedata` (stdlib) | stdlib | Character category inspection in validation script | To classify whether extracted characters are in math Unicode ranges |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pymupdf4llm | pdfminer.six | pymupdf4llm is already referenced in requirements; pdfminer has weaker table support |
| `re` for math detection | `sympy.parsing.latex` | sympy parses valid LaTeX, but math from PDF text may not be valid LaTeX — regex detection is safer for finding patterns in existing strings |

**Installation — add to pyproject.toml:**
```
pymupdf4llm>=0.0.17
```
Or via uv:
```bash
uv add pymupdf4llm
```

---

## Architecture Patterns

### Recommended Project Structure for Phase 1

```
scripts/
└── validate_pdf_math.py          # Plan 01-01: standalone validation script

src/
└── ingestion/
    └── math_extractor.py         # Plan 01-02: math detection module

tests/
└── test_math_extractor.py        # Plan 01-02: unit tests for math_extractor

.planning/
└── phases/
    └── 01-validation-and-foundation/
        └── validation_report.md  # Plan 01-01: output report (committed as doc artifact)
```

### Pattern 1: Validation Script as Standalone Script (not a module)

**What:** The validation script lives in `scripts/` and is run directly with `uv run python scripts/validate_pdf_math.py <path-to-pdf>`. It does NOT import from `src/` modules (it calls PyMuPDF and pymupdf4llm APIs directly) because the goal is to inspect raw library behavior before any pipeline abstractions get in the way.

**When to use:** Whenever empirical investigation of library behavior is needed before pipeline decisions are made.

**Example structure:**
```python
# scripts/validate_pdf_math.py
"""Empirical validation of PDF math extraction quality.

Usage:
    uv run python scripts/validate_pdf_math.py path/to/suneung.pdf [--pages 1-10]

Outputs:
    - Console: per-page summary of symbol extraction quality
    - JSON: detailed per-page character analysis (validate_report.json)
    - MD: human-readable report (validate_report.md)
"""
import json
import unicodedata
import sys
import fitz          # PyMuPDF
import pymupdf4llm

MATH_UNICODE_RANGES = [
    (0x0041, 0x007A),   # Basic Latin (a-z, A-Z -- may appear as math substitutes)
    (0x00B0, 0x00B9),   # Degree, superscripts
    (0x2000, 0x206F),   # General punctuation
    (0x2070, 0x209F),   # Superscripts and subscripts
    (0x20A0, 0x20CF),   # Currency symbols
    (0x2100, 0x214F),   # Letterlike symbols
    (0x2190, 0x21FF),   # Arrows
    (0x2200, 0x22FF),   # Mathematical operators (∑, ∫, ∞, ≤, ≥, etc.)
    (0x2300, 0x23FF),   # Miscellaneous technical
    (0x27C0, 0x27EF),   # Misc math symbols-A
    (0x2980, 0x29FF),   # Misc math symbols-B
    (0xE000, 0xF8FF),   # Private Use Area — BAD: fonts substituting glyphs here
    (0xFFFD, 0xFFFD),   # Replacement character — BAD: undecodeable glyph
]

PRIVATE_USE_AREA = (0xE000, 0xF8FF)
REPLACEMENT_CHAR = 0xFFFD

def classify_char(ch: str) -> str:
    """Returns 'math', 'private_use', 'replacement', 'hangul', 'ascii', or 'other'."""
    cp = ord(ch)
    if cp == REPLACEMENT_CHAR:
        return 'replacement'
    if PRIVATE_USE_AREA[0] <= cp <= PRIVATE_USE_AREA[1]:
        return 'private_use'
    if 0x2200 <= cp <= 0x22FF:
        return 'math_operator'
    if 0xAC00 <= cp <= 0xD7AF:
        return 'hangul'
    if 0x20 <= cp <= 0x7E:
        return 'ascii'
    return 'other'
```

### Pattern 2: math_extractor.py as a Pure-Function Module

**What:** `math_extractor.py` contains stateless functions with no side effects. It receives text strings and returns detection results. It does NOT import `src.config` or any external service.

**When to use:** Pure-function detection modules are trivially unit-testable and can be used in pipeline steps without mocking.

**Example:**
```python
# src/ingestion/math_extractor.py
"""Math formula detection in extracted text.

Detects LaTeX delimiters that may appear in LLM-generated or LaTeX-source-derived text.
Does NOT attempt to find math in raw PDF output (where delimiters do not exist).
"""
from __future__ import annotations

import re

# Patterns for LaTeX delimiters (present only if text was LLM-generated or from LaTeX source)
_INLINE_MATH = re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', re.DOTALL)
_BLOCK_MATH = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
_BEGIN_EQUATION = re.compile(r'\\begin\{(equation|align|gather|multline)\*?\}')

def has_math(text: str) -> bool:
    """Return True if text contains any LaTeX math delimiters."""
    return bool(
        _INLINE_MATH.search(text)
        or _BLOCK_MATH.search(text)
        or _BEGIN_EQUATION.search(text)
    )

def detect_math_regions(text: str) -> dict:
    """Return counts and first match positions for each math pattern type."""
    inline = _INLINE_MATH.findall(text)
    block = _BLOCK_MATH.findall(text)
    equation_envs = _BEGIN_EQUATION.findall(text)
    return {
        "has_math": bool(inline or block or equation_envs),
        "inline_count": len(inline),
        "block_count": len(block),
        "equation_env_count": len(equation_envs),
    }
```

### Pattern 3: Page Model Extension for has_math Flag

**What:** Add `has_math: bool` to the `Page` model in `src/models/page.py`. The pipeline sets this flag based on `math_extractor.has_math(page.content)` after content is written.

**When to use:** Success criterion 4 requires the ingestion pipeline to accept a PDF and produce page content with a `has_math` flag.

**Current Page model (src/models/page.py):**
```python
class Page(BaseModel):
    # ... existing fields ...
    has_table: bool = Field(False, alias="hasTable")
    has_figure: bool = Field(False, alias="hasFigure")
    # ADD:
    has_math: bool = Field(False, alias="hasMath")
```

### Anti-Patterns to Avoid

- **Running validate_pdf_math.py inside pytest:** The validation script is a developer tool, not a test. It requires real 수능 PDF files not committed to the repo. Put it in `scripts/`, not `tests/`.
- **Making math_extractor.py import from config:** It should be a pure function module with no dependencies on settings, database, or LLM providers.
- **Treating the validation report as a test assertion:** The report is a documented artifact (Markdown + JSON). Phase 2 decisions come from reading it, not from automated pass/fail.
- **Using `\$` to escape dollar signs in the regex:** The inline math regex must use negative lookbehind `(?<!\$)` to avoid matching `$$` as two inline openers. The pattern shown above handles this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom parser | PyMuPDF `page.get_text()` | Already in pyproject.toml; handles page geometry, font metadata, CMAP |
| Markdown from PDF | Custom converter | pymupdf4llm `to_markdown()` | Version 0.3.4 handles headers, tables, bold/italic; handles page_chunks=True for per-page results |
| Unicode range inspection | Custom lookup | `unicodedata.category(ch)` + range checks | stdlib; sufficient for classifying extracted characters |
| JSON test fixtures | Real PDF files in tests | pypdf `PdfWriter` to generate in-memory PDFs | Already done in `tests/test_pdf_parser.py`; pattern to replicate for math_extractor tests |

**Key insight:** The validation script is the one place where reading the raw output matters more than abstraction. Resist adding helper classes. Let the output speak plainly.

---

## Common Pitfalls

### Pitfall 1: PDF Text Layer Has No LaTeX Delimiters

**What goes wrong:** Developer writes `math_extractor.py` expecting to find `$...$` or `\frac` in raw PyMuPDF output, then tests on a synthetic string with `$x^2$` — tests pass. Then tries on a real 수능 PDF — zero matches. All tests stay green, all production runs return `has_math=False`.

**Why it happens:** Real 수능 PDFs are typeset by Korean desktop publishing tools (HWP, InDesign), not compiled from LaTeX source. The text layer contains Unicode glyphs, not LaTeX markup. `$...$` delimiters exist only in LaTeX source files and LLM-generated text.

**How to avoid:** The validation script (Plan 01-01) must run FIRST. `math_extractor.py` (Plan 01-02) is designed for text that has ALREADY been processed by an LLM or came from LaTeX source — NOT for raw PDF output. The `has_math` flag in the Page model will be False for all raw-PDF pages until Phase 2 adds LLM-based formula reconstruction.

**Warning signs:** `detect_math_regions()` returns `{"has_math": False, "inline_count": 0, ...}` for every page of a real math PDF.

---

### Pitfall 2: Private-Use-Area Characters vs. Replacement Characters — Two Different Failure Modes

**What goes wrong:** Validation script only checks for `\uFFFD` (replacement char) and concludes "PyMuPDF extracts math fine" because it finds no replacement characters. But the actual problem is private-use-area characters (U+E000–U+F8FF) which look like letters in some fonts but are semantically meaningless.

**Why it happens:** PyMuPDF default flag `TEXT_USE_CID_FOR_UNKNOWN_UNICODE` (value 128, default ON) outputs raw CID values instead of U+FFFD for unrecognizable glyphs. These CIDs often land in the private use area and appear as boxes or font-specific symbols rather than the replacement diamond.

**How to avoid:** The validation script must check for both failure modes:
1. Characters in range U+E000–U+F8FF (private use area — indicates missing CMAP)
2. U+FFFD (replacement character — indicates explicit decode failure)

Also inspect via `get_text("rawdict")` which exposes `"origin"` and `"glyph"` fields per character, allowing font name inspection.

**Warning signs:** Validation report shows 0 replacement chars but pages 3-10 have 80%+ of characters with codepoints between 0xE000 and 0xF8FF.

---

### Pitfall 3: LLM Returns Single-Backslash LaTeX in JSON — Current json_utils.py Returns None Silently

**What goes wrong:** LLM prompt returns `{"title": "부등식 \frac{a}{b} \geq 0"}`. Python's `json.loads()` raises `JSONDecodeError` because `\f` and `\g` are not valid JSON escape sequences. The current `extract_json()` tries Python literal cleanup (`None`→`null`, etc.) but this does NOT fix backslash issues. Result: `extract_json()` returns `None`, tree builder gets no data, ingestion silently fails for math documents.

**Why it happens:** JSON requires backslashes to be doubled: `\\frac`, `\\geq`. LLMs often produce syntactically valid LaTeX (single backslash) inside JSON strings (which requires double backslash). The current cleanup pipeline in `json_utils.py` does not include a backslash-escape step.

**How to avoid:** The fix is a targeted pre-processing step. After extracting the JSON substring, before each `json.loads()` call, attempt:
```python
# In extract_json(), as a new fallback step after Python literal cleanup:
fixed = re.sub(r'(?<!\\)\\(?![\\"\/bfnrtu])', r'\\\\', json_content)
json.loads(fixed)
```
This regex replaces single backslashes that are NOT followed by a valid JSON escape character with double backslashes. It specifically avoids double-escaping already-escaped sequences.

**Warning signs:** `extract_json()` logs `"Failed to parse JSON even after cleanup"` specifically on responses that contain LaTeX commands visible in the raw LLM output.

---

### Pitfall 4: Regex Inline Math Pattern Matches Across Line Boundaries or Currency Signs

**What goes wrong:** The pattern `\$(.+?)\$` matches `$ price` in prose like "costs $50 per item and $30 more" — interpreting `50 per item and $30 more` as LaTeX.

**Why it happens:** Single `$` in prose text is common (prices, shell variables). The naive pattern cannot distinguish currency from math delimiters.

**How to avoid:** Phase 1's regex detection in `math_extractor.py` is for text that has ALREADY been processed (LLM output, LaTeX-sourced text). If used on prose, add a sanity check: inline math content should be short (< 200 chars) and not span blank lines. Use `re.compile(r'\$([^$\n]{1,200})\$')` for inline to avoid multi-paragraph false matches.

The validation script is separate from `math_extractor.py` — the script detects *Unicode math symbols* in raw text; the module detects *LaTeX delimiters* in processed text.

---

### Pitfall 5: pymupdf4llm Not Installed (Missing from pyproject.toml)

**What goes wrong:** `import pymupdf4llm` fails with `ModuleNotFoundError` when Plan 01-01 validation script runs.

**Why it happens:** `pymupdf4llm` is referenced in the requirements (VAL-02) and roadmap but is NOT in `pyproject.toml`. Only `PyMuPDF>=1.24` is listed.

**How to avoid:** Plan 01-01 must start with adding `pymupdf4llm>=0.0.17` to `pyproject.toml` and running `uv sync`. Verify: `python -c "import pymupdf4llm; print(pymupdf4llm.__version__)"`.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### PyMuPDF: Extracting Per-Character Data for Font Analysis

```python
# Source: PyMuPDF docs https://pymupdf.readthedocs.io/en/latest/textpage.html
# Use get_text("rawdict") to access per-character glyph info
import fitz

doc = fitz.open("suneung.pdf")
page = doc[0]
raw = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

for block in raw["blocks"]:
    if block["type"] != 0:  # 0 = text, 1 = image
        continue
    for line in block["lines"]:
        for span in line["spans"]:
            font_name = span["font"]
            for char in span["chars"]:
                codepoint = char["c"]
                glyph_id = char.get("glyph", -1)
                # Check if codepoint is in private use area
                if 0xE000 <= codepoint <= 0xF8FF:
                    print(f"PRIVATE USE: font={font_name} glyph={glyph_id} cp=U+{codepoint:04X}")
                elif codepoint == 0xFFFD:
                    print(f"REPLACEMENT: font={font_name} glyph={glyph_id}")
```

### pymupdf4llm: Per-Page Markdown Extraction

```python
# Source: PyPI pymupdf4llm 0.3.4 https://pypi.org/project/pymupdf4llm/
import pymupdf4llm

# page_chunks=True returns list[dict], one per page
# "text" key contains Markdown-formatted page content
pages = pymupdf4llm.to_markdown("suneung.pdf", page_chunks=True)

for page_data in pages:
    page_num = page_data["metadata"]["page"]   # 0-based in pymupdf4llm output
    markdown_text = page_data["text"]
    # Check what math (if any) was extracted
    print(f"Page {page_num + 1}: {len(markdown_text)} chars")
    print(markdown_text[:500])
```

### json_utils.py: LaTeX Backslash Fix Pattern

```python
# Source: codebase analysis + Python json stdlib docs
# Add as new fallback step inside extract_json() in src/utils/json_utils.py

import re

def _fix_latex_backslashes(json_content: str) -> str:
    """Fix single backslashes in LaTeX commands within JSON strings.

    JSON requires backslashes to be doubled. LaTeX commands like \frac, \sqrt
    use single backslashes. This regex doubles backslashes that are NOT
    already valid JSON escape sequences.

    Valid JSON escapes after \: " \ / b f n r t u
    LaTeX commands after \: letters (f, s, a, g, etc.) and { }
    """
    # Only replace \X where X is not a valid JSON escape character
    return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_content)
```

This fix must be inserted into the `extract_json()` fallback chain in `src/utils/json_utils.py` AFTER the initial `json.loads()` attempt fails, alongside the existing Python literal cleanup.

### math_extractor.py: Test Pattern

```python
# tests/test_math_extractor.py — follows project test conventions
from src.ingestion.math_extractor import has_math, detect_math_regions


def test_has_math_inline():
    assert has_math("The formula is $x^2 + y^2 = r^2$ in polar form.") is True


def test_has_math_block():
    assert has_math("$$\\frac{d}{dx}\\sin(x) = \\cos(x)$$") is True


def test_has_math_begin_equation():
    assert has_math("\\begin{equation} E = mc^2 \\end{equation}") is True


def test_has_math_false_on_plain_text():
    assert has_math("This is plain Korean text without any math.") is False


def test_has_math_false_on_raw_pdf_output():
    # Simulates garbled PDF extraction — no LaTeX delimiters present
    assert has_math("f(x) = \uFFFD\uFFFD + \uFFFD\uFFFD") is False


def test_detect_math_regions_counts():
    text = "Solve $a + b = c$ and $x^2 = 4$. Also $$\\int_0^1 f(x) dx = 1$$."
    result = detect_math_regions(text)
    assert result["has_math"] is True
    assert result["inline_count"] == 2
    assert result["block_count"] == 1
    assert result["equation_env_count"] == 0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyMuPDF `page.getText()` | `page.get_text()` (lowercase) | PyMuPDF 1.18+ | API rename; old name deprecated |
| pymupdf4llm 0.0.x | pymupdf4llm 0.3.4 (Feb 2026) | 2025-2026 | Supports `page_chunks=True`, `extract_words`, `use_glyphs` params |
| `ast.literal_eval()` fallback in json_utils | `re`-based backslash fix | Phase 1 work | Handles LaTeX escaping without eval security concerns |

**Deprecated/outdated:**
- `page.getText()`: Use `page.get_text()`. Old name may still work but is not documented in current PyMuPDF.
- `pymupdf4llm.to_markdown(doc, pages=[0,1,2])`: Pages are 0-based in pymupdf4llm despite PyMuPDF being 0-based. Verify indexing in validation script.

---

## Open Questions

1. **Do real 수능 PDFs have usable Unicode in the math text layer?**
   - What we know: PyMuPDF produces garbled output for many Korean/CJK math PDFs due to missing CMAP tables in custom fonts. Project research (PITFALLS.md) identifies this as the critical unknown.
   - What's unclear: The specific 수능 PDFs that the developer will test may vary. Some years or publishers may use fonts with complete CMaps.
   - Recommendation: The validation script (Plan 01-01) resolves this. Until it runs on real samples, Phase 2 design cannot be finalized. The script output should categorize pages into: (A) usable Unicode math symbols, (B) private-use-area characters, (C) empty/replacement-character output.

2. **Does pymupdf4llm produce better math output than raw get_text()?**
   - What we know: pymupdf4llm wraps PyMuPDF and adds Markdown formatting. It does not have native LaTeX/math support. However, it may handle character ordering and spacing better for math regions.
   - What's unclear: Whether pymupdf4llm's additional processing (table detection, layout analysis) helps or hurts math symbol extraction quality.
   - Recommendation: The validation script must test BOTH backends side-by-side on the same pages and document any difference.

3. **What is the correct regex for inline math that avoids false matches on `$$` (block math)?**
   - What we know: The naive pattern `\$([^$]+)\$` matches block math delimiters as two inline expressions.
   - Recommendation: Use negative lookahead/lookbehind: `(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)`. Test this pattern specifically on text containing both `$inline$` and `$$block$$` before finalizing `math_extractor.py`.

---

## Sources

### Primary (HIGH confidence)

- Codebase direct inspection: `src/ingestion/parsers/pdf_parser.py`, `src/utils/json_utils.py`, `src/models/page.py`, `pyproject.toml`, `tests/test_json_utils.py`, `tests/test_pdf_parser.py`
- `.planning/research/PITFALLS.md` — 12 documented pitfalls from project's own research (HIGH confidence: codebase-specific)
- `.planning/REQUIREMENTS.md` — VAL-01, VAL-02 requirements (authoritative)
- `.planning/ROADMAP.md` — Phase 1 success criteria (authoritative)
- PyMuPDF vars docs (https://pymupdf.readthedocs.io/en/latest/vars.html) — TEXT_USE_CID_FOR_UNKNOWN_UNICODE flag value 128, confirmed default ON for text extraction
- pymupdf4llm PyPI (https://pypi.org/project/pymupdf4llm/) — Version 0.3.4 released 2026-02-14, page_chunks=True output structure

### Secondary (MEDIUM confidence)

- PyMuPDF issue #423 (https://github.com/pymupdf/PyMuPDF/issues/423) — Math symbol extraction failure modes: replacement chars, private-use-area, font-substituted ASCII (verified by multiple issues and docs)
- PyMuPDF textpage docs (https://pymupdf.readthedocs.io/en/latest/textpage.html) — rawdict format exposes per-character glyph data
- pymupdf4llm API docs (https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html) — to_markdown() parameters confirmed

### Tertiary (LOW confidence)

- Paul Leasure blog (https://www.paulleasure.com/math/navigating-backslashes-in-json-flask-and-sympy-a-developers-guide/) — LaTeX backslash cascading problem description (single source, not official docs)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in pyproject.toml except pymupdf4llm; versions verified from PyPI
- Architecture patterns: HIGH — validated against existing codebase conventions (test patterns, module structure)
- Pitfalls: HIGH — backed by project's own PITFALLS.md research plus direct library documentation
- Validation script design: MEDIUM — structure is well-grounded, but exact output format for the report is at planner discretion
- json_utils.py fix pattern: HIGH — the specific regex for valid JSON escape sequences is well-defined by JSON spec (RFC 8259)

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable libraries; pymupdf4llm may release new versions but API is stable)
