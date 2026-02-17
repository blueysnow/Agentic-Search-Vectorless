# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** 수학 수식이 포함된 PDF 문서를 업로드하면 수식이 LaTeX 형식으로 정확하게 파싱되어, 검색 결과와 답변에서 수식이 올바르게 렌더링되어야 한다.
**Current focus:** Phase 1 — Validation and Foundation

## Current Position

Phase: 1 of 4 (Validation and Foundation)
Plan: 2 of 2 in current phase (complete)
Status: Phase 1 complete — both plans done
Last activity: 2026-02-17 — 01-02 complete; LaTeX JSON fix, math_extractor module, Page.has_math field

Progress: [███░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (01-01 at checkpoint + task 1 done; 01-02 fully complete)
- Average duration: ~6 min (01-02)
- Total execution time: ~6 min (01-02 only measured)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-validation-and-foundation | 2/2 | ~6 min | ~6 min |

**Recent Trend:**
- Last 5 plans: 01-02 (6 min)
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
- [01-02]: Aggressive LaTeX backslash fix escapes ALL \\<letter> sequences — needed because \\frac starts with \\f (valid JSON form-feed escape), strict-only fix misidentifies \\frac as form-feed + "rac"
- [01-02]: LaTeX aggressive fix applied BEFORE strict fix in fallback chain — only reached after direct parse fails, so cannot corrupt valid JSON with true \\n/\\t/\\f escapes
- [01-02]: math_extractor detects delimiters in LLM-processed text only; raw PDF math detection is Phase 2 scope

### Pending Todos

- Run `uv run python scripts/validate_pdf_math.py <suneung_pdf>` on 1-3 real 수능 math PDFs and document findings (resolves CRITICAL architectural unknown for Phase 2 ingestion strategy)

### Blockers/Concerns

- [Phase 1 CHECKPOINT]: Awaiting human to run `scripts/validate_pdf_math.py` on real 수능 PDFs. Result determines whether Phase 2 uses regex detection vs. mandatory LLM reconstruction for math. No action possible until findings are documented.

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 01-02-PLAN.md — LaTeX JSON fix and math_extractor module
Resume file: .planning/phases/01-validation-and-foundation/01-02-SUMMARY.md
