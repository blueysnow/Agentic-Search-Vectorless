---
phase: 01-validation-and-foundation
plan: "01"
subsystem: tooling
tags: [pymupdf, pymupdf4llm, pdf, unicode, math-extraction, validation, diagnostics]

# Dependency graph
requires: []
provides:
  - Standalone PDF math extraction validator (scripts/validate_pdf_math.py)
  - Dual-backend per-page character classification (PyMuPDF rawdict + pymupdf4llm markdown)
  - 8-category Unicode classifier detecting private_use and replacement chars
  - Machine-readable JSON report for empirical math quality data
affects:
  - 01-02 (json_utils fix)
  - Phase 2 ingestion design — math extraction strategy depends on validator output

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
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "pymupdf4llm added as project dependency — enables LLM-ready markdown extraction for comparison against raw PyMuPDF"
  - "Script lives in scripts/ not tests/ — it's a diagnostic/developer tool, not an automated test"
  - "8-category Unicode classifier covers: math_operator, private_use, replacement, hangul, ascii, superscript_subscript, arrow, other"
  - "CHECKPOINT: awaiting human to run script on real 수능 PDF — result determines Phase 2 math ingestion strategy"

patterns-established:
  - "Standalone diagnostic scripts: no src/ imports, use argparse, produce JSON output"
  - "Verdict logic: DEGRADED if private_use>0 or replacement>0; HAS_MATH_UNICODE if math_operator>0; CLEAN otherwise"

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 1 Plan 01: PDF Math Extraction Validation Script Summary

**Dual-backend PDF validator using PyMuPDF rawdict + pymupdf4llm markdown, classifying chars into 8 Unicode categories to detect private-use-area failure modes in Korean 수능 math PDFs**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-17T15:06:51Z
- **Completed:** 2026-02-17T15:10:01Z (checkpoint reached — awaiting human verification)
- **Tasks:** 1/2 complete (Task 2 is a human-verify checkpoint)
- **Files modified:** 3

## Accomplishments

- Added `pymupdf4llm>=0.0.17` to pyproject.toml; installed version 0.3.4
- Created `scripts/validate_pdf_math.py` (484 lines) with full dual-backend analysis
- Script classifies every character in both PyMuPDF rawdict and pymupdf4llm markdown outputs across 8 Unicode categories, flags pages with private_use or replacement chars, produces per-page console table and `validate_report.json`
- Verified: `--help` works, ruff passes with no errors, end-to-end test on generated PDF produces JSON + console output

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pymupdf4llm dependency and create validation script** - `004deda` (feat)
2. **Task 2: Run validation script on real PDF samples** - PENDING (human-verify checkpoint)

**Plan metadata:** TBD (after checkpoint completion)

## Files Created/Modified

- `scripts/validate_pdf_math.py` - Standalone PDF math extraction validator with dual backend (PyMuPDF rawdict + pymupdf4llm), 8-category Unicode classifier, JSON + console output
- `pyproject.toml` - Added pymupdf4llm>=0.0.17 dependency
- `uv.lock` - Updated lock file

## Decisions Made

- Used `pymupdf4llm.to_markdown(path, page_chunks=True)` so each page chunk is individually analyzed — enables per-page verdict comparison between backends
- `unicodedata.category()` added to `classify_char` to catch Mathematical Alphanumeric Symbols (U+1D400-U+1D7FF) which are letters/numbers in math context
- Quality verdict logic: `DEGRADED` > `HAS_MATH_UNICODE` > `CLEAN` — conservative approach ensures degraded pages are never silently passed through

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

## Checkpoint Status

**PAUSED at Task 2 (checkpoint:human-verify)**

The script is ready for human verification on real 수능 PDFs. This checkpoint resolves the critical architectural unknown for Phase 2 ingestion design.

**To run:**
```bash
uv run python scripts/validate_pdf_math.py path/to/suneung_math.pdf
```

**Expected outcomes:**
- "Mostly private_use/replacement" → LLM reconstruction mandatory in Phase 2
- "math_operator chars present" → regex detection may be viable in Phase 2
- "Mixed" → requires per-page routing logic in Phase 2 ingestion

## User Setup Required

None - no external service configuration required. Script uses local PDF file only.

## Next Phase Readiness

- Validator script ready for immediate use on real PDF samples
- Phase 2 design blocked until human runs script and documents findings
- Once checkpoint complete, continue to plan 01-02 (json_utils LaTeX fix)

## Self-Check: PASSED

- FOUND: scripts/validate_pdf_math.py
- FOUND: pyproject.toml (with pymupdf4llm dependency)
- FOUND: .planning/phases/01-validation-and-foundation/01-01-SUMMARY.md
- FOUND commit: 004deda

---
*Phase: 01-validation-and-foundation*
*Completed: 2026-02-17 (checkpoint — awaiting human verify)*
