# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** 수학 수식이 포함된 PDF 문서를 업로드하면 수식이 LaTeX 형식으로 정확하게 파싱되어, 검색 결과와 답변에서 수식이 올바르게 렌더링되어야 한다.
**Current focus:** Phase 1 — Validation and Foundation

## Current Position

Phase: 1 of 4 (Validation and Foundation)
Plan: 1 of 2 in current phase (paused at checkpoint — awaiting human verification)
Status: Checkpoint — human-verify required for 01-01 Task 2
Last activity: 2026-02-17 — 01-01 Task 1 complete; validator script built and committed

Progress: [█░░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (01-01 at checkpoint, not yet complete)
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-validation-and-foundation | 0/2 | — | — |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-Phase 1]: KaTeX chosen over MathJax — synchronous rendering required for SSE streaming; MathJax async conflicts with Next.js 15 App Router hydration (pending PROJECT.md update)
- [Pre-Phase 1]: PDF math extraction strategy TBD pending empirical validation in Phase 1 — determines whether regex detection is sufficient or LLM reconstruction is mandatory
- [01-01]: pymupdf4llm added as project dependency — enables LLM-ready markdown extraction for dual-backend comparison
- [01-01]: Diagnostic script in scripts/ (not tests/) — it's a developer tool, not an automated test
- [01-01]: 8-category Unicode classifier: math_operator, private_use, replacement, hangul, ascii, superscript_subscript, arrow, other

### Pending Todos

- Run `uv run python scripts/validate_pdf_math.py <suneung_pdf>` on 1-3 real 수능 math PDFs and document findings (resolves CRITICAL architectural unknown for Phase 2 ingestion strategy)

### Blockers/Concerns

- [Phase 1 CHECKPOINT]: Awaiting human to run `scripts/validate_pdf_math.py` on real 수능 PDFs. Result determines whether Phase 2 uses regex detection vs. mandatory LLM reconstruction for math. No action possible until findings are documented.
- [Phase 1]: `json_utils.py` LaTeX backslash escaping must be fixed before any math-aware LLM calls are made — prerequisite for all subsequent phases (addressed in 01-02).

## Session Continuity

Last session: 2026-02-17
Stopped at: 01-01 Task 1 complete (commit 004deda); paused at checkpoint:human-verify Task 2
Resume file: .planning/phases/01-validation-and-foundation/01-01-SUMMARY.md
