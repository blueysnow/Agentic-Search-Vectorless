---
phase: 01-validation-and-foundation
plan: "01"
subsystem: tooling
tags: [pymupdf, pymupdf4llm, pdf, unicode, math-extraction, validation, diagnostics, korean-hwp, llm-reconstruction]

# Dependency graph
requires: []
provides:
  - Standalone PDF math extraction validator (scripts/validate_pdf_math.py)
  - Dual-backend per-page character classification (PyMuPDF rawdict + pymupdf4llm markdown)
  - 8-category Unicode classifier detecting private_use and replacement chars
  - Machine-readable JSON report for empirical math quality data
  - EMPIRICAL FINDING: Korean 수능 PDFs use HWP custom fonts with missing CMAPs — LLM reconstruction mandatory
affects:
  - 01-02 (json_utils fix — now confirmed critical prerequisite)
  - Phase 2 ingestion design — LLM reconstruction mandatory, regex detection is NOT viable

# Tech tracking
tech-stack:
  added:
    - pymupdf4llm==0.3.4 (PDF-to-markdown with page chunk support)
  patterns:
    - Standalone diagnostic scripts in scripts/ with no src/ imports
    - Dual-backend comparison pattern for empirical PDF quality assessment

key-files:
  created:
    - scripts/validate_pdf_math.py
    - validate_report.json (generated artifact, not committed)
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "pymupdf4llm added as project dependency — enables LLM-ready markdown extraction for comparison against raw PyMuPDF"
  - "Script lives in scripts/ not tests/ — it's a diagnostic/developer tool, not an automated test"
  - "8-category Unicode classifier covers: math_operator, private_use, replacement, hangul, ascii, superscript_subscript, arrow, other"
  - "CRITICAL: LLM reconstruction is MANDATORY for Phase 2 — Korean 수능 PDFs use HWP custom fonts with private-use-area codepoints (U+E000-U+F8FF), all 20 pages DEGRADED under raw PyMuPDF; pymupdf4llm drops garbled content but does not recover math"

patterns-established:
  - "Standalone diagnostic scripts: no src/ imports, use argparse, produce JSON output"
  - "Verdict logic: DEGRADED if private_use>0 or replacement>0; HAS_MATH_UNICODE if math_operator>0; CLEAN otherwise"

# Metrics
duration: ~1 day (task 1: 3min automated; task 2: human verification)
completed: 2026-02-18
---

# Phase 1 Plan 01: PDF Math Extraction Validation Script Summary

**Dual-backend PDF validator confirmed: Korean 수능 PDFs use HWP private-use-area fonts (all 20 pages DEGRADED) — LLM reconstruction is mandatory for Phase 2, regex detection is not viable**

## Performance

- **Duration:** ~1 day (Task 1: ~3 min automated on 2026-02-17; Task 2: human verification on 2026-02-18)
- **Started:** 2026-02-17T15:06:51Z
- **Completed:** 2026-02-18 (human verification complete)
- **Tasks:** 2/2 complete
- **Files modified:** 3 (pyproject.toml, uv.lock, scripts/validate_pdf_math.py)

## Accomplishments

- Added `pymupdf4llm>=0.0.17` to pyproject.toml; installed version 0.3.4
- Created `scripts/validate_pdf_math.py` (484 lines) with full dual-backend analysis
- Script classifies every character in both PyMuPDF rawdict and pymupdf4llm markdown outputs across 8 Unicode categories, flags pages with private_use or replacement chars, produces per-page console table and `validate_report.json`
- Verified: `--help` works, ruff passes with no errors, end-to-end test on generated PDF produces JSON + console output
- **CRITICAL FINDING (Task 2):** Empirically validated on real 수능 math PDF (20 pages) — LLM reconstruction is mandatory for Phase 2

## Empirical Findings (Task 2)

**Test file:** `tests/fixtures/수학영역_문제지_홀수형.pdf` (20 pages, official Korean CSAT math exam)

| Backend | Pages DEGRADED | Pages HAS_MATH_UNICODE | Pages CLEAN | Private-use chars | Replacement chars | Math operator chars |
|---------|---------------|----------------------|-------------|-------------------|-------------------|---------------------|
| PyMuPDF (raw) | **20/20** | 0/20 | 0/20 | 2,014 | 0 | 37 |
| pymupdf4llm | 8/20 | 0/20 | 12/20 | 1,412 | 0 | 42 |

**Root cause:** HWP custom fonts with missing CMAPs. Font names are garbled Korean HWP fonts (e.g., `*½Å¸í-°ß¸íÁ¶`, `*ÇÑ¾ç°ß°íµñ`). All math content is stored as private-use-area codepoints (U+E000-U+F8FF) that cannot be decoded without the original HWP font files.

**Key observations:**
- Zero replacement characters — all failures are private-use-area, not corrupted Unicode
- pymupdf4llm's "CLEAN" pages simply drop the garbled content; they do NOT recover math
- The 37-42 math_operator chars found are scattered punctuation, not formula content
- Script recommendation output: `LLM_RECONSTRUCTION_MANDATORY`

**Phase 2 implication:** Regex-only math detection on raw PDF text will NOT work for Korean 수능 PDFs. Phase 2 ingestion must use LLM-based formula reconstruction from page images or similar approach. Architectural unknown is now resolved with empirical evidence.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymupdf4llm dependency and create validation script** - `004deda` (feat)
2. **Task 2: Run validation script on real PDF samples** - human verification (no code changes — findings documented in SUMMARY)

**Plan metadata:** TBD (this commit)

## Files Created/Modified

- `scripts/validate_pdf_math.py` - Standalone PDF math extraction validator with dual backend (PyMuPDF rawdict + pymupdf4llm), 8-category Unicode classifier, JSON + console output
- `pyproject.toml` - Added pymupdf4llm>=0.0.17 dependency
- `uv.lock` - Updated lock file
- `validate_report.json` - Generated artifact in project root (not committed); contains full per-page classification data

## Decisions Made

- Used `pymupdf4llm.to_markdown(path, page_chunks=True)` so each page chunk is individually analyzed — enables per-page verdict comparison between backends
- `unicodedata.category()` added to `classify_char` to catch Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF) which are letters/numbers in math context
- Quality verdict logic: `DEGRADED` > `HAS_MATH_UNICODE` > `CLEAN` — conservative approach ensures degraded pages are never silently passed through
- **[CRITICAL — Task 2 finding]:** LLM reconstruction is mandatory for Phase 2 — empirically confirmed on real 수능 math PDF. Regex detection is NOT viable. Phase 2 must reconstruct math from page images or equivalent LLM-based approach.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unused unicodedata import causing ruff F401**

- **Found during:** Task 1 (ruff check verification)
- **Issue:** Plan specified using `unicodedata` stdlib for character name lookups, but initial implementation only imported it without use, causing ruff F401 failure
- **Fix:** Added `unicodedata.category()` check in `classify_char` to handle Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF) — extends math detection beyond the base math operators block
- **Files modified:** scripts/validate_pdf_math.py
- **Verification:** `ruff check` passes with "All checks passed!"
- **Committed in:** `004deda` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix)
**Impact on plan:** Extends math symbol detection to include Mathematical Alphanumeric Symbols block. No scope creep — unicodedata use was already specified in the plan.

## Issues Encountered

- ruff not in PATH directly; required `uv run --with ruff ruff check` invocation — resolved automatically
- pymupdf4llm "CLEAN" result is misleading — it drops garbled content rather than recovering it; this was only discoverable by running on real HWP-based PDFs (anticipated by the plan design)

## User Setup Required

None - no external service configuration required. Script uses local PDF file only.

## Next Phase Readiness

- Plan 01-01 complete — both tasks done, architectural unknown resolved
- **Critical decision documented:** LLM reconstruction mandatory for Phase 2 — Phase 2 must NOT attempt regex-based math detection on raw PDF text
- Plan 01-02 (json_utils LaTeX fix) remains the prerequisite for any math-aware LLM calls — this is now confirmed as blocking Phase 2

## Self-Check: PASSED

- FOUND: scripts/validate_pdf_math.py
- FOUND: pyproject.toml (with pymupdf4llm dependency)
- FOUND: .planning/phases/01-validation-and-foundation/01-01-SUMMARY.md
- FOUND commit: 004deda
- FOUND: validate_report.json (generated artifact in project root)
- Task 2 findings documented with empirical data from real 수능 PDF

---
*Phase: 01-validation-and-foundation*
*Completed: 2026-02-18*
