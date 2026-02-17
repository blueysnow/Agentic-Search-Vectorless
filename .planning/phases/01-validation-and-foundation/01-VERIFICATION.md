---
phase: 01-validation-and-foundation
verified: 2026-02-18T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Confirm validate_report.json was produced from a real 수능 PDF"
    expected: "validate_report.json shows 20/20 pages DEGRADED under PyMuPDF rawdict with private_use chars in the thousands"
    why_human: "The generated JSON artifact is not committed; the empirical finding is documented in SUMMARY but cannot be re-run programmatically without the real PDF fixture"
---

# Phase 1: Validation and Foundation Verification Report

**Phase Goal:** Know exactly how real 수능 PDFs encode math, and have a tested math detection module ready for the pipeline
**Verified:** 2026-02-18
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A developer can run a validation script against real 수능 PDF samples and see a documented report of whether math symbols extract as usable Unicode, garbled private-use characters, or empty strings | VERIFIED | `scripts/validate_pdf_math.py` exists (484 lines), implements both PyMuPDF rawdict + pymupdf4llm backends, detects private_use (U+E000-U+F8FF) and replacement (U+FFFD) as distinct failure modes, produces console table + JSON report. Script runs without error on `--help`. SUMMARY documents empirical result from real 수능 PDF (20/20 pages DEGRADED). |
| 2 | The system's behavior when LaTeX backslashes appear in LLM JSON responses is predictable — json_utils.py handles them without silent corruption | VERIFIED | `src/utils/json_utils.py` has `_fix_latex_backslashes()` and `_fix_latex_backslashes_aggressive()` wired as fallback steps inside `extract_json()`. All 6 LaTeX-specific tests pass (frac, sqrt, fenced, valid-escape preservation, None+LaTeX combo, multiple commands). No regressions on existing 10 tests. |
| 3 | A math_extractor.py module exists with regex-based detection of $...$, $$...$$, and \begin{equation} patterns, covered by unit tests | VERIFIED | `src/ingestion/math_extractor.py` exists (87 lines) with module-level compiled regexes for all three delimiter types. `has_math()` and `detect_math_regions()` are pure-function implementations. `tests/test_math_extractor.py` (112 lines, 18 tests) covers inline, block, equation/align/gather/multline envs, false positives (currency, garbled PDF), and overlap avoidance. All 18 tests pass. |
| 4 | The ingestion pipeline can accept a PDF and produce page content with a has_math flag, even if the flag is always False on non-math documents | VERIFIED | `src/models/page.py` has `has_math: bool = Field(False, alias="hasMath")` after the existing `has_figure` field. `Page(...).to_mongo()['hasMath']` returns `False` as default. Serialization alias is wired correctly via Pydantic `model_dump(by_alias=True)` in `to_mongo()`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/validate_pdf_math.py` | Standalone PDF math extraction validation script | VERIFIED | 484 lines. Has argparse CLI (positional pdf_path, --pages, --output-dir). Implements `classify_char`, `analyze_with_pymupdf`, `analyze_with_pymupdf4llm`, `print_console_report`, `write_json_report`. `if __name__ == "__main__":` guard present. |
| `pyproject.toml` | pymupdf4llm dependency added | VERIFIED | Line 20: `"pymupdf4llm>=0.0.17"` present in dependencies list. |
| `src/utils/json_utils.py` | LaTeX-safe JSON extraction | VERIFIED | Contains `_fix_latex_backslashes` (line 23) and `_fix_latex_backslashes_aggressive` (line 36), both called in the `extract_json()` fallback chain (lines 116, 124, 134). |
| `src/ingestion/math_extractor.py` | Math detection functions | VERIFIED | 87 lines. Exports `has_math` and `detect_math_regions`. Module-level compiled regexes: `_RE_BLOCK`, `_RE_INLINE`, `_RE_ENV`. Pure-function, no imports beyond `re`. |
| `tests/test_math_extractor.py` | Unit tests for math_extractor | VERIFIED | 112 lines (minimum 40). 18 tests covering all required pattern types and edge cases. |
| `tests/test_json_utils.py` | Extended tests covering LaTeX backslash cases | VERIFIED | Contains `test_extract_json_latex_frac`, `test_extract_json_latex_sqrt`, `test_extract_json_latex_with_fences`, `test_extract_json_latex_does_not_corrupt_valid_escapes`, `test_extract_json_latex_with_python_none`, `test_extract_json_latex_multiple_commands`. All 6 pass. |
| `src/models/page.py` | Page model with has_math field | VERIFIED | Line 24: `has_math: bool = Field(False, alias="hasMath")`. `to_mongo()` returns `{'hasMath': False}` by default. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/validate_pdf_math.py` | fitz (PyMuPDF) | `fitz.open`, `get_text("rawdict")` | WIRED | Line 108: `fitz.open(pdf_path)`, line 121: `page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)` |
| `scripts/validate_pdf_math.py` | pymupdf4llm | `pymupdf4llm.to_markdown(page_chunks=True)` | WIRED | Line 162: `pymupdf4llm.to_markdown(pdf_path, page_chunks=True)` |
| `src/utils/json_utils.py` | `_fix_latex_backslashes` helper | called as fallback step in `extract_json()` after initial `json.loads` fails | WIRED | `_fix_latex_backslashes_aggressive` called at line 116 (aggressive first), `_fix_latex_backslashes` at line 124 (strict fallback), combined path at line 134. Both only reached after prior parse attempts fail. |
| `src/ingestion/math_extractor.py` | re (stdlib) | compiled regex patterns for LaTeX delimiters | WIRED | Lines 19, 23, 27: `re.compile(...)` for `_RE_BLOCK`, `_RE_INLINE`, `_RE_ENV` respectively. |
| `src/models/page.py` | has_math field | Pydantic `Field` with alias | WIRED | Line 24: `has_math: bool = Field(False, alias="hasMath")`. Pattern `has_math.*alias.*hasMath` confirmed. |

### Requirements Coverage

Requirements VAL-01 and VAL-02 are satisfied:
- VAL-01 (validation script for real PDF samples): SATISFIED — script exists, runs, was used on real 수능 PDF, empirical finding documented.
- VAL-02 (math detection module): SATISFIED — `math_extractor.py` with unit tests and Page model `has_math` field both delivered.

### Anti-Patterns Found

Scanned key files modified in this phase:

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `scripts/validate_pdf_math.py` | No TODOs, no placeholders, no stub returns | None | Clean |
| `src/utils/json_utils.py` | No stubs; full fallback chain implemented with 6 try/except paths | None | Clean |
| `src/ingestion/math_extractor.py` | No stubs; all regex patterns compiled at module level, both functions fully implemented | None | Clean |
| `src/models/page.py` | `has_math` field added with correct default and alias; no placeholder | None | Clean |

No blocker or warning anti-patterns found.

### Human Verification Required

#### 1. Empirical PDF findings confirmation

**Test:** Obtain a Korean 수능 math PDF (e.g., `tests/fixtures/수학영역_문제지_홀수형.pdf` as documented in SUMMARY) and run: `uv run python scripts/validate_pdf_math.py <path-to-pdf>`
**Expected:** All or most pages show `DEGRADED` verdict under PyMuPDF rawdict backend due to HWP private-use-area fonts. The `validate_report.json` should show `recommendation: LLM_RECONSTRUCTION_MANDATORY`.
**Why human:** The PDF fixture is not committed to the repository (documented in SUMMARY as "generated artifact, not committed"). The empirical finding is documented in the SUMMARY but cannot be re-verified programmatically without access to the actual PDF file.

### Gaps Summary

No gaps. All four success criteria are fully verified in the codebase:

1. The validation script (`scripts/validate_pdf_math.py`) is substantive and complete — 484 lines, dual-backend, 8-category Unicode classifier, per-page console table + JSON output. The SUMMARY documents empirical results from running it on real 수능 PDFs.

2. `json_utils.py` LaTeX handling is correct and tested — the fallback chain uses an aggressive form (`_fix_latex_backslashes_aggressive`) that correctly handles `\frac` (which starts with `\f`, a valid JSON escape that the strict variant misses). All 6 LaTeX tests and all 10 pre-existing tests pass.

3. `math_extractor.py` is a pure-function module with compiled regexes covering inline `$...$`, block `$$...$$`, and `\begin{equation|align|gather|multline}` environments. 18 unit tests cover all required cases including false-positive prevention.

4. `Page.has_math` field exists with `Field(False, alias="hasMath")` and `to_mongo()` serializes it correctly as `hasMath`.

Commits verified: `004deda` (plan 01-01), `857beb8` and `370fa83` (plan 01-02).

---

_Verified: 2026-02-18_
_Verifier: Claude (gsd-verifier)_
