---
phase: 01-validation-and-foundation
plan: 02
subsystem: api
tags: [json, latex, math, regex, pydantic, ingestion]

# Dependency graph
requires: []
provides:
  - LaTeX-safe JSON extraction in src/utils/json_utils.py via _fix_latex_backslashes_aggressive()
  - Math delimiter detection module src/ingestion/math_extractor.py (has_math, detect_math_regions)
  - Page model has_math field (alias hasMath) with False default
affects: [02-math-ingestion, 03-retrieval, 04-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LaTeX fallback chain: aggressive \\<letter> doubling applied before strict invalid-escape fix"
    - "Pure-function detection module: no imports beyond re stdlib, safe to use anywhere"
    - "Pydantic model boolean flags use Field(False, alias='camelCase') pattern"

key-files:
  created:
    - src/ingestion/math_extractor.py
    - tests/test_math_extractor.py
  modified:
    - src/utils/json_utils.py
    - tests/test_json_utils.py
    - src/models/page.py

key-decisions:
  - "Aggressive LaTeX backslash fix (_fix_latex_backslashes_aggressive) escapes ALL \\<letter> sequences, not just invalid JSON ones, because \\frac starts with \\f which is a valid JSON form-feed escape -- using strict regex alone left \\frac incorrectly decoded"
  - "LaTeX fallback chain uses aggressive fix BEFORE strict fix, since aggressive never runs unless prior parses have already failed (guaranteeing the content is not valid JSON to begin with)"
  - "math_extractor detects delimiters in processed text only (LLM output/LaTeX source) -- not in raw PDF where no delimiters exist, keeping scope well-defined"
  - "Block math pattern matched before inline pattern to prevent $$ from being misidentified as two inline $ delimiters"

patterns-established:
  - "extract_json() fallback chain: direct parse -> Python literals -> trailing comma -> aggressive LaTeX -> strict LaTeX -> combined"
  - "Module-level compiled regex constants in math_extractor.py for performance"

# Metrics
duration: 6min
completed: 2026-02-17
---

# Phase 1 Plan 02: LaTeX JSON Fix and Math Extractor Summary

**LaTeX-safe JSON extraction with aggressive backslash doubling, plus a pure-function math delimiter detector (has_math/detect_math_regions) and Page.has_math field for downstream filtering**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-02-17T15:07:03Z
- **Completed:** 2026-02-17T15:13:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Fixed `extract_json()` to parse LLM responses containing LaTeX commands (`\frac`, `\sqrt`, `\geq`, `\alpha`, etc.) without returning None or corrupting valid JSON escapes (`\n`, `\t`, `\\`)
- Created `src/ingestion/math_extractor.py` as a pure-function module with `has_math()` and `detect_math_regions()` using compiled regexes for `$...$`, `$$...$$`, and `\begin{equation|align|gather|multline}` patterns
- Added `has_math: bool = Field(False, alias="hasMath")` to the Page model following the existing `has_table`/`has_figure` convention
- Added 24 new unit tests (16 for json_utils, 18 for math_extractor); full suite: 495 passed, 11 skipped, 0 regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix json_utils.py LaTeX backslash escaping** - `857beb8` (feat)
2. **Task 2: Create math_extractor.py and add has_math to Page model** - `370fa83` (feat)

## Files Created/Modified

- `src/utils/json_utils.py` - Added `_fix_latex_backslashes()`, `_fix_latex_backslashes_aggressive()`, and extended fallback chain in `extract_json()`
- `tests/test_json_utils.py` - Added 6 LaTeX-specific test cases covering `\frac`, `\sqrt`, fenced JSON, valid escape preservation, None+LaTeX combo, multi-command
- `src/ingestion/math_extractor.py` - New pure-function module: `has_math()` and `detect_math_regions()` with module-level compiled regexes
- `tests/test_math_extractor.py` - 18 unit tests covering inline/block/equation-env detection, false positives (currency, garbled PDF), and overlap avoidance
- `src/models/page.py` - Added `has_math: bool = Field(False, alias="hasMath")` after `has_figure`

## Decisions Made

- **Aggressive vs. strict LaTeX fix ordering:** `\frac` starts with `\f` which IS a valid JSON escape (form-feed). A strict regex that only fixes invalid escapes would leave `\frac` intact -- json.loads then parses `\f` as form-feed and `rac{...}` as literal text, producing wrong output without throwing. Putting the aggressive fix (which doubles ALL `\<letter>`) before the strict fix ensures `\frac` is correctly preserved. The aggressive path is only reached after direct parsing has already failed, so it cannot corrupt valid JSON that includes true `\n`/`\t`/`\f` escapes.
- **math_extractor scope boundary:** The module detects delimiters in LLM-processed text. Raw PDF output from PyMuPDF does not contain LaTeX delimiters, so this module intentionally returns `has_math=False` for raw PDF text -- that gap will be addressed in Phase 2 with heuristic detection for PDF math regions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reordered LaTeX fallback from strict-before-aggressive to aggressive-before-strict**

- **Found during:** Task 1 verification
- **Issue:** `\frac` starts with `\f` -- a valid JSON escape (form-feed). The strict fix (`\\(?!["\\/bfnrtu])`) excludes `f`, so `\frac` was left for json.loads to parse as form-feed + `rac`. This produced a wrong dict (no exception) and the aggressive fix was never reached.
- **Fix:** Swapped order: try `_fix_latex_backslashes_aggressive` first (doubles all `\<letter>`), then `_fix_latex_backslashes` strict as a lower-priority fallback. Valid JSON with `\n`/`\t` never reaches either path (first parse succeeds).
- **Files modified:** `src/utils/json_utils.py`
- **Verification:** All 16 json_utils tests pass including `test_extract_json_latex_frac` and `test_extract_json_latex_does_not_corrupt_valid_escapes`
- **Committed in:** `857beb8` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in ordering logic)
**Impact on plan:** Fix was essential for correctness -- without it the `\frac` test would return wrong data rather than raising an error. No scope creep.

## Issues Encountered

- First implementation of `_fix_latex_backslashes` correctly identified invalid JSON escapes but missed the `\f`-from-`\frac` case since `f` is in the JSON valid-escape list. Caught by test failure on first run, fixed immediately by adding aggressive variant and reordering.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `extract_json()` is now safe for all math-aware LLM calls (prerequisite for Phase 2 ingestion pipeline changes)
- `has_math()` and `detect_math_regions()` are ready for integration into the ingestion pipeline
- `Page.has_math` field is in place for the pipeline to populate and for retrieval to filter on
- No blockers for Phase 1 Plan 03 or later phases

## Self-Check: PASSED

All files verified on disk:
- FOUND: src/utils/json_utils.py
- FOUND: src/ingestion/math_extractor.py
- FOUND: tests/test_math_extractor.py
- FOUND: tests/test_json_utils.py
- FOUND: src/models/page.py
- FOUND: .planning/phases/01-validation-and-foundation/01-02-SUMMARY.md

Task commits verified:
- FOUND: 857beb8 feat(01-02): fix LaTeX backslash escaping in extract_json()
- FOUND: 370fa83 feat(01-02): add math_extractor module and has_math field to Page model

---
*Phase: 01-validation-and-foundation*
*Completed: 2026-02-17*
