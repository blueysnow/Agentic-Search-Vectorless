# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** 수학 수식이 포함된 PDF 문서를 업로드하면 수식이 LaTeX 형식으로 정확하게 파싱되어, 검색 결과와 답변에서 수식이 올바르게 렌더링되어야 한다.
**Current focus:** Phase 1 — Validation and Foundation (complete — ready for Phase 2)

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
- [Pre-Phase 1 RESOLVED 2026-02-18]: **LLM reconstruction is MANDATORY for Phase 2** — Korean 수능 PDFs use HWP custom fonts with private-use-area codepoints (U+E000-U+F8FF); all 20 pages DEGRADED under raw PyMuPDF; pymupdf4llm drops garbled content but does NOT recover math. Regex detection is NOT viable. Empirically confirmed on `수학영역_문제지_홀수형.pdf` (20 pages).
- [01-01]: pymupdf4llm added as project dependency — enables LLM-ready markdown extraction for dual-backend comparison
- [01-01]: Diagnostic script in scripts/ (not tests/) — it's a developer tool, not an automated test
- [01-01]: 8-category Unicode classifier: math_operator, private_use, replacement, hangul, ascii, superscript_subscript, arrow, other
- [01-02]: Aggressive LaTeX backslash fix escapes ALL \\<letter> sequences — needed because \\frac starts with \\f (valid JSON form-feed escape), strict-only fix misidentifies \\frac as form-feed + "rac"
- [01-02]: LaTeX aggressive fix applied BEFORE strict fix in fallback chain — only reached after direct parse fails, so cannot corrupt valid JSON with true \\n/\\t/\\f escapes
- [01-02]: math_extractor detects delimiters in LLM-processed text only; raw PDF math detection is Phase 2 scope

### Pending Todos

None — Phase 1 is complete. Phase 2 planning may begin.

### Blockers/Concerns

- [Phase 2 design]: LLM reconstruction mandatory — Phase 2 ingestion must NOT attempt regex-based math detection on raw PDF text. Must use LLM-based formula reconstruction from page images or equivalent. See validate_report.json for empirical evidence.
- [Phase 2 prerequisite RESOLVED]: json_utils.py LaTeX backslash escaping fixed in 01-02 (commit 857beb8) — prerequisite for all math-aware LLM calls is now met.

## Session Continuity

Last session: 2026-02-18
Stopped at: Completed 01-01-PLAN.md — Task 2 human verification resolved; LLM reconstruction mandatory decision documented
Resume file: .planning/phases/01-validation-and-foundation/01-01-SUMMARY.md
