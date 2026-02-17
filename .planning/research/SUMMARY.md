# Project Research Summary

**Project:** Agentic Search — Math Formula Support for Korean Exam PDFs
**Domain:** Math-aware document ingestion and LaTeX rendering in a vectorless RAG system
**Researched:** 2026-02-17
**Confidence:** MEDIUM (stack HIGH, features HIGH, architecture HIGH, pitfalls HIGH — overall MEDIUM because critical unknowns require empirical validation against real 수능 PDFs before architecture commits)

## Executive Summary

This milestone adds math formula extraction and LaTeX rendering to an existing vectorless RAG system targeting Korean math exam papers (수능/시험 문제지). The core approach is: use `pymupdf4llm` to extract math-aware Markdown from PDF text layers, use Claude Haiku (already integrated) to normalize extracted Unicode math symbols into proper LaTeX, store LaTeX strings as-is in MongoDB, and render them in the frontend using KaTeX via `remark-math` + `rehype-katex` plugins on the existing `react-markdown` component. The architecture is deliberately minimal — one new Python library, three npm packages, and one new enrichment step — with no new services, no GPU requirements, and no external APIs.

The recommended approach is additive to the existing 5-layer pipeline. Backend math extraction belongs in two places in the Ingestion layer: `pdf_parser.py` (pymupdf4llm extraction) and a new `math_extractor.py` enrichment module (regex detection + `has_math` flag). The data model gains `has_math: bool` and `math_expressions: list[str]` on `Page`, and `has_math: bool` on `Node`. The Retrieval layer, LLM provider, and API routes require zero changes — LaTeX passes through as plain text, which the LLM already understands natively.

The critical risk — and the most important thing to validate before writing any production code — is whether real 수능 PDFs actually contain a usable text layer. Korean math exam PDFs are produced by specialized Korean DTP tools (Hangul Word Processor, InDesign), not LaTeX. Mathematical formulas may extract as garbled private-use Unicode, as empty strings, or as usable Unicode math symbols depending entirely on how each PDF was produced. **This must be tested empirically on real PDF samples before any pipeline architecture is finalized.** If text-layer extraction is unreliable, the LLM-based LaTeX reconstruction path becomes mandatory (not optional), substantially changing the cost model.

## Key Findings

### Recommended Stack

The recommended stack adds minimally to the existing project. On the backend, `pymupdf4llm 0.0.17` (by the PyMuPDF authors, Artifex) wraps the existing PyMuPDF dependency and produces math-aware Markdown with `$...$` delimiters for recognized formula regions — no GPU, no network, milliseconds per page. For cases where pymupdf4llm's Unicode preservation is insufficient (fractions, complex structures), a Claude Haiku LLM call with a LaTeX normalization prompt reconstructs proper `\frac`, `\sqrt`, etc. using the Anthropic SDK already present.

On the frontend, `katex 0.16.11` + `remark-math 6.0.0` + `rehype-katex 7.0.1` integrate directly with the existing `react-markdown 10.1.0` installation via two plugin props. KaTeX is strongly preferred over MathJax: synchronous rendering is essential for SSE streaming (MathJax renders asynchronously), bundle size is ~430KB total vs MathJax's 700KB+, and Next.js App Router SSR integration is clean with KaTeX vs problematic with MathJax.

**Core technologies:**
- `pymupdf4llm 0.0.17`: math-aware Markdown extraction from PDF text layer — extends existing PyMuPDF dependency, zero system deps
- Claude Haiku (existing): LaTeX normalization prompt — converts Unicode math to `\frac`/`\sqrt`/etc., applied conditionally to math-detected pages only
- `katex 0.16.11`: core LaTeX-to-HTML renderer — synchronous, pure function, no global state
- `remark-math 6.0.0`: Markdown plugin that parses `$...$` and `$$...$$` as AST math nodes
- `rehype-katex 7.0.1`: converts remark-math AST to KaTeX-rendered HTML

**Not recommended (explicit rejections):**
- Nougat / pix2tex / MathPix — GPU or paid API, out of scope per PROJECT.md constraint (text-layer only)
- MathJax 3 — async rendering conflicts with SSE streaming and Next.js 15 App Router hydration
- pdfminer.six — redundant with existing PyMuPDF capabilities
- Vector embeddings for math — entire project is vectorless by design

### Expected Features

**Must have (table stakes) — nothing works without these:**
- LaTeX delimiter preservation in parsed page text (root input problem; all downstream depends on it)
- LaTeX strings survive tree building: `Node.summary` and `Node.keywords` contain LaTeX where relevant
- LLM prompts explicitly instructed to preserve and reproduce `$...$`/`$$...$$` delimiters
- Frontend KaTeX rendering: `remark-math` + `rehype-katex` plugins on `MessageItem.tsx`
- `has_math: bool` flag on `Page` and `Node` models (enables filtering and ingestion quality diagnostics)

**Should have (competitive differentiators):**
- Math-aware keyword extraction: LLM generates Korean mathematical concept keywords ("이차방정식", "극값", "삼각함수") for better BM25 recall
- Math content type classification: recognize `problem`, `solution`, `theorem`, `proof` types in addition to existing content types
- Graceful degradation: detect image-only formula regions and surface a clear user-facing message rather than silently returning garbage
- LaTeX normalization: post-extraction canonicalization to prevent KaTeX rendering errors from malformed LaTeX

**Defer to v2+:**
- Math-aware text chunking that avoids splitting mid-formula or mid-problem — high complexity, only needed if answer quality measurably suffers
- Multi-document formula cross-referencing — separate milestone, requires retrieval pipeline changes
- Interactive formula editor for queries — target users query in natural-language Korean, not LaTeX

**Anti-features (explicitly out of scope):**
- Image-based OCR formula extraction (Nougat, pix2tex) — PROJECT.md explicitly excludes this
- Vector embeddings for formula semantic search — antithetical to vectorless design; LLM tree navigation handles math meaning better anyway
- Formula similarity/structural search engines — MathML/OMDoc complexity; use case is natural-language Korean queries

### Architecture Approach

Math formula support fits entirely within the existing Ingestion layer, extended at two sub-stages (parser and enrichment), with a thin rendering layer added to the frontend chat component. The Retrieval layer, LLM provider, MongoDB Atlas Search index, API routes, and session management require zero changes. LaTeX strings are stored as plain text in MongoDB (no schema migration, no re-indexing), pass through the retrieval pipeline unchanged, and are rendered only at the frontend boundary. This clean layering is the most defensible architecture: it preserves the existing system's correctness invariants and confines math complexity to isolated, testable modules.

**Major components:**
1. `src/ingestion/parsers/pdf_parser.py` — Extended: add `pymupdf4llm` backend option alongside existing pypdf/PyMuPDF; `ParsedPage` gains `math_expressions: list[str]`
2. `src/ingestion/enrichment/math_extractor.py` — New file: `extract_math_expressions(text) -> list[str]` and `has_math_content(text) -> bool` using regex patterns for `$...$`, `$$...$$`, `\begin{equation}`, `\[...\]`
3. `src/ingestion/pipeline.py` — Extended at `_collect_nodes()` (set `Node.has_math`) and `save_pages()` (set `Page.has_math`, `Page.math_expressions`)
4. `src/models/page.py` and `src/models/node.py` — Extended with `has_math: bool` (and `math_expressions: list[str]` on Page)
5. `frontend/components/chat/MessageItem.tsx` — Extended: add `remarkMath` and `rehypeKatex` plugins to existing `ReactMarkdown`
6. `frontend/app/layout.tsx` — Extended: add `katex/dist/katex.min.css` global import

The build order is strictly: `math_extractor.py` first (no deps) → data model extensions (non-breaking) → pipeline integration → frontend (fully independent, can parallelize). Backend Phases 1-3 and Frontend Phase 4 can be built in parallel.

### Critical Pitfalls

1. **PDF text layer may not contain usable math (Pitfalls 1 and 2)** — Korean exam PDFs are not produced from LaTeX source; `$...$` delimiters do not exist in raw PDF text; math symbols may extract as private-use Unicode garbage. Validate against real 수능 PDFs before writing any math detection code. The LLM reconstruction path (Claude receives raw Unicode text and outputs LaTeX) must be the fallback design, not an afterthought.

2. **LLM hallucinates plausible-but-wrong formulas from corrupted text (Pitfall 3)** — If PyMuPDF extracts `□□ + □□` from a formula region, Claude will guess a mathematically valid formula that may be semantically wrong. Use `[ILLEGIBLE_FORMULA]` placeholder instruction in prompts; add per-page math-quality diagnostics before LLM calls; keep the math enrichment LLM call separate from the tree-building LLM call.

3. **LaTeX backslashes break JSON serialization in LLM responses (Pitfall 9)** — `{"title": "\frac{a}{b}"}` is invalid JSON (single backslash). Current `json_utils.py` fallback to `ast.literal_eval()` does not fix this. Must add a targeted backslash pre-processing step in `extract_json()` before any math-aware LLM calls are made.

4. **Atlas Search BM25 cannot match LaTeX syntax against Korean query terms (Pitfall 4)** — Storing `\frac{d}{dx}\sin(x)` in node keywords means Korean queries like "sin x 미분" will not match. Store both LaTeX (for rendering) and Korean natural-language descriptions (for search). The keyword extractor must generate Korean math concept keywords, not just copy LaTeX strings.

5. **KaTeX requires correct plugin chain and CSS; failures are silent (Pitfall 6)** — Missing either `remark-math` or `rehype-katex` causes `react-markdown` to render `$...$` as literal text with no error. Missing `katex.min.css` renders formulas as unstyled illegible HTML. The CSS import must go in `layout.tsx` (Server Component), not inside `MessageItem.tsx` (Client Component).

## Implications for Roadmap

Based on research, suggested phase structure (4 phases):

### Phase 1: Empirical Validation and Foundation
**Rationale:** The entire architecture depends on an empirical unknown — whether real 수능 PDFs have usable text-layer math. This must be settled first, before any pipeline code is written. If validation fails, Phase 2 shifts significantly toward LLM-only reconstruction.
**Delivers:** Confirmed knowledge of PDF extraction quality; `math_extractor.py` module with tests; data model extensions (`has_math`, `math_expressions` fields); baseline ingestion pipeline accepting math content.
**Addresses:** Features 1 (LaTeX extraction) and 5 (`has_math` flag)
**Avoids:** Pitfalls 1, 2 (assumes $...$ delimiters exist without validation), and 3 (LLM hallucination on corrupted text)
**Tasks:**
- Run `page.get_text("dict")` on real 수능 PDF samples; document symbol extraction quality
- Fix `json_utils.py` for LaTeX backslash escaping (Pitfall 9 — must be done before any math LLM calls)
- Create `math_extractor.py` with regex patterns
- Extend `Page` and `Node` models with `has_math` field

### Phase 2: Backend Ingestion Pipeline Integration
**Rationale:** With extraction strategy validated in Phase 1, wire math extraction into the full ingestion pipeline. Update LLM prompts to preserve LaTeX. Add pymupdf4llm as the math-aware PDF extraction backend.
**Delivers:** End-to-end ingestion of math-containing PDFs with LaTeX preserved in `pages.content`, `nodes.summary`, and `nodes.keywords`. LaTeX passes through to retrieval layer.
**Uses:** `pymupdf4llm 0.0.17` (backend extraction); Claude Haiku (LLM normalization, conditional on math detection)
**Implements:** `pdf_parser.py` extension + `pipeline.py` integration at `_collect_nodes()` and `save_pages()`
**Addresses:** Features 2 (LaTeX survives tree building), 3 (LLM prompts preserve LaTeX), 6 (math-aware keywords)
**Avoids:** Pitfalls 3 (LLM hallucination), 4 (BM25 cannot match LaTeX), 7 (Korean tiktoken inflation), 8 (no ToC fallback to mode C)

### Phase 3: Frontend LaTeX Rendering
**Rationale:** Frontend is fully independent of backend — can be built in parallel with Phase 2 but is listed as Phase 3 for clarity. The rendering layer is simple; pitfall avoidance is the main concern.
**Delivers:** Typeset math in chat responses and document summaries. Users see rendered `\frac{1}{2}` instead of raw `$\frac{1}{2}$`.
**Uses:** `katex 0.16.11`, `remark-math 6.0.0`, `rehype-katex 7.0.1`
**Implements:** `MessageItem.tsx` extension + `layout.tsx` global CSS
**Addresses:** Feature 4 (KaTeX rendering)
**Avoids:** Pitfalls 5 (SSR hydration mismatch — use 'use client'), 6 (missing plugin chain or CSS), 10 (MathJax conflicts with streaming), 12 (LaTeX newlines in SSE — verify JSON serialization)

### Phase 4: Differentiators and Polish
**Rationale:** These features improve quality over the baseline but depend on Phases 1-3 being stable. Prioritized by impact vs. complexity.
**Delivers:** Math-aware content type classification, graceful degradation for image-based PDF pages, LaTeX canonicalization for rendering robustness, optional math-aware node splitting if answer quality is poor.
**Addresses:** Features 7 (content type classification), 8 (graceful degradation), 9 (LaTeX normalization), 10 (math-aware chunking — only if needed)
**Avoids:** Pitfall 11 (image-based formula PDFs silently drop all math — surface the limitation explicitly)

### Phase Ordering Rationale

- Phase 1 must be first because the architecture of Phase 2 depends on knowing what real 수능 PDFs actually produce. Building the LLM normalization path as a fallback (not optional) changes implementation decisions in `pdf_parser.py`.
- Phase 2 before Phase 4 because differentiators (math keywords, content types) depend on the core extraction pipeline being stable and validated.
- Phase 3 (frontend) is truly independent and can run in parallel with Phase 2 once the `math_extractor.py` module is ready to generate sample outputs for testing.
- The `json_utils.py` LaTeX backslash fix (Pitfall 9) must be done in Phase 1, not later — it is a prerequisite for any math-aware LLM calls.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (PDF Validation):** PDF font encoding and text-layer behavior in Korean DTP-produced documents is not well-documented. The empirical validation step IS the research. Block time for this before committing to pipeline design.
- **Phase 2 (pymupdf4llm behavior):** pymupdf4llm's math detection heuristics on Korean exam PDF layouts (multi-column, problem numbering, dense symbol sets) are untested. May need custom post-processing if pymupdf4llm's `$...$` wrapping is insufficient.

Phases with standard, well-documented patterns (skip research):
- **Phase 3 (KaTeX frontend):** `remark-math` + `rehype-katex` + `react-markdown` is a documented, production-proven integration. Used by Notion, Khan Academy. No surprises expected beyond the pitfalls already catalogued.
- **Phase 4 content type classification:** Extends existing `content_classifier.py` pattern. Standard LLM prompt engineering.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pymupdf4llm and KaTeX ecosystem are production-mature. Versions verified through January 2025 training data. |
| Features | HIGH | Feature set is derived from codebase analysis + domain knowledge. Scope is well-bounded by existing PROJECT.md constraints. |
| Architecture | HIGH | Architecture plan is grounded in existing codebase structure; additive-only changes with no breaking modifications. |
| Pitfalls | HIGH | Pitfalls are grounded in known behaviors of PyMuPDF text extraction, JSON backslash escaping, KaTeX/React integration, and Korean font encoding. |

**Overall confidence:** MEDIUM

The individual research areas are individually high confidence, but the critical unknown — how well real 수능 PDF text layers encode mathematical formulas — cannot be resolved without empirical testing. This single empirical gap is the reason overall confidence is MEDIUM. Everything else flows from it.

### Gaps to Address

- **PDF extraction quality on real 수능 PDFs:** Run extraction on 3-5 representative PDFs (official KSAT releases, different years) before finalizing Phase 2 design. The outcome determines whether regex-based `$...$` detection is sufficient or whether LLM reconstruction is mandatory.
- **pymupdf4llm's behavior on Korean multi-column layouts:** The library is tested on Western academic documents. Korean exam papers use dense multi-column problem layouts with mixed Korean/math. Test `pymupdf4llm.to_markdown()` on a real sample before relying on it.
- **tiktoken vs Claude tokenizer divergence for Korean:** The existing system uses `gpt-4o` tiktoken encoding for token counting. For Korean math content this may inflate counts by 2-3x versus Claude's actual tokenizer. Verify `MAX_TOKENS_PER_NODE` is appropriate for Korean content before bulk ingestion.
- **Tailwind prose + KaTeX CSS interaction:** The `[&_.katex]:not-prose` workaround is a recommendation; actual behavior depends on Tailwind version and KaTeX output. Needs visual verification in the actual UI.
- **SSE streaming with math content:** The theoretical analysis (Pitfall 12) concludes that `json.dumps()` handles LaTeX newlines correctly. An integration test using real SSE output with `$$...$$` block math is needed to confirm.

## Sources

### Primary (HIGH confidence)
- Codebase analysis at `/home/moamath/work/Agentic-Search-Vectorless` — all architectural claims grounded in actual code inspection
- `pymupdf4llm` documentation (Artifex) — extraction behavior, math detection heuristics
- KaTeX project (Khan Academy) — rendering scope, SSR compatibility, supported LaTeX commands
- `remark-math` / `rehype-katex` npm packages — integration compatibility with `react-markdown 10.x`

### Secondary (MEDIUM confidence)
- Domain knowledge of Korean math exam PDF production methods (Korean DTP tools vs LaTeX) — explains why text-layer LaTeX extraction is uncertain
- KaTeX's `throwOnError: false` behavior for unsupported commands — standard configuration, behavior documented in KaTeX README
- tiktoken cl100k_base encoding rates for Korean (Hangul) — 1.5-2.5 tokens/character, based on OpenAI tokenizer documentation

### Tertiary (LOW confidence — needs empirical validation)
- pymupdf4llm math detection on Korean multi-column layouts — no documented evidence; inferred from library's span-level font analysis approach
- Atlas Search BM25 behavior on mixed LaTeX/Korean token streams — theoretical; needs testing with actual Atlas Search cluster
- Actual 수능 PDF text-layer quality — the entire foundation assumption; completely unvalidated

---
*Research completed: 2026-02-17*
*Ready for roadmap: yes — with the caveat that Phase 1 empirical PDF validation must occur before Phase 2 architecture is finalized*
