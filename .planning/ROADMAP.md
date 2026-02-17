# Roadmap: Agentic Search — Math-Aware Vectorless RAG

## Overview

This milestone adds math formula extraction and LaTeX rendering to an existing vectorless RAG system targeting Korean math exam papers (수능/시험 문제지). The work flows in four phases: first validate that real 수능 PDFs actually yield usable text-layer math (a critical empirical unknown), then wire math extraction into the ingestion pipeline, then add LaTeX preservation through retrieval, then render math in the frontend with KaTeX. Each phase delivers a verifiable capability. The frontend phase is largely independent and can proceed in parallel with the backend phases once Phase 1 produces sample math output for testing.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Validation and Foundation** - Empirically verify PDF math extraction quality and build the math detection module
- [ ] **Phase 2: Ingestion Pipeline** - Wire math extraction end-to-end through PDF parsing, tree building, and node enrichment
- [ ] **Phase 3: Retrieval and API Layer** - Ensure LaTeX survives JSON serialization, LLM prompts, and Atlas Search indexing
- [ ] **Phase 4: Frontend Rendering** - Render LaTeX formulas with KaTeX in chat and document views

## Phase Details

### Phase 1: Validation and Foundation
**Goal**: Know exactly how real 수능 PDFs encode math, and have a tested math detection module ready for the pipeline
**Depends on**: Nothing (first phase)
**Requirements**: VAL-01, VAL-02
**Success Criteria** (what must be TRUE):
  1. A developer can run a validation script against real 수능 PDF samples and see a documented report of whether math symbols extract as usable Unicode, garbled private-use characters, or empty strings
  2. The system's behavior when LaTeX backslashes appear in LLM JSON responses is predictable — `json_utils.py` handles them without silent corruption
  3. A `math_extractor.py` module exists with regex-based detection of `$...$`, `$$...$$`, and `\begin{equation}` patterns, covered by unit tests
  4. The ingestion pipeline can accept a PDF and produce page content with a `has_math` flag, even if the flag is always False on non-math documents
**Plans**: TBD

Plans:
- [ ] 01-01: Empirical PDF validation — run PyMuPDF and pymupdf4llm on real 수능 samples, document symbol extraction quality
- [ ] 01-02: Fix `json_utils.py` for LaTeX backslash escaping and create `math_extractor.py` with tests

### Phase 2: Ingestion Pipeline
**Goal**: Uploading a math-containing PDF results in pages and nodes that store LaTeX-formatted formulas, ready for retrieval
**Depends on**: Phase 1
**Requirements**: ING-01, ING-02, ING-03, ING-04
**Success Criteria** (what must be TRUE):
  1. After uploading a 수능 math PDF, the `pages` collection contains documents where inline formulas appear as `$...$` and block formulas appear as `$$...$$` in the `content` field
  2. Node summaries in the `nodes` collection contain LaTeX-formatted formulas where the source page contained math, not garbled Unicode or stripped symbols
  3. Node keyword arrays contain Korean natural-language math concept terms (e.g., "이차방정식", "극값") in addition to any LaTeX, so BM25 search on Korean queries can match math content
  4. Re-ingesting the same PDF after pipeline changes produces consistent LaTeX output (the normalization step is deterministic for the same input text)
**Plans**: TBD

Plans:
- [ ] 02-01: Extend `pdf_parser.py` with pymupdf4llm backend; implement ING-01 formula detection and wrapping
- [ ] 02-02: Implement ING-02 Claude Haiku LaTeX normalization enrichment step
- [ ] 02-03: Update `pipeline.py` and models for ING-03/ING-04 — LaTeX preservation through tree building and enrichment

### Phase 3: Retrieval and API Layer
**Goal**: LaTeX formulas survive the full backend pipeline from ingestion through LLM reasoning to the API response without corruption
**Depends on**: Phase 2
**Requirements**: RET-01, RET-02, RET-03
**Success Criteria** (what must be TRUE):
  1. A query about a math topic returns an answer where LaTeX delimiters (`$...$`, `$$...$$`) are intact in the JSON response body — no double-escaped backslashes, no stripped delimiters
  2. The LLM reasoning loop reproduces LaTeX formulas from retrieved context verbatim in its output, rather than paraphrasing them in plain text or Unicode
  3. A Korean-language query ("이차방정식의 근을 구하시오") returns relevant math content nodes in search results, not just nodes that happen to contain LaTeX strings
**Plans**: TBD

Plans:
- [ ] 03-01: Audit and fix LLM prompts in retrieval pipeline to explicitly preserve `$...$`/`$$...$$` delimiters (RET-01)
- [ ] 03-02: Verify and harden JSON serialization for LaTeX backslashes across all API response paths (RET-02)
- [ ] 03-03: Confirm Korean math keyword extraction from Phase 2 flows into Atlas Search BM25 results (RET-03)

### Phase 4: Frontend Rendering
**Goal**: Users see typeset mathematical formulas in chat responses and document views, not raw LaTeX strings
**Depends on**: Phase 3
**Requirements**: FE-01, FE-02, FE-03
**Success Criteria** (what must be TRUE):
  1. In the chat interface, a response containing `$\frac{1}{2}$` displays as a rendered fraction, not the literal string `$\frac{1}{2}$`
  2. In the document detail page (node/page viewer), LaTeX formulas in node summaries and page content render as typeset math
  3. During SSE streaming of a chat response, formulas render correctly as they stream in — partial LaTeX strings do not flash as broken symbols before completion
  4. The KaTeX CSS is loaded globally and does not conflict with Tailwind prose styles in any existing page
**Plans**: TBD

Plans:
- [ ] 04-01: Install katex, remark-math, rehype-katex; integrate into `MessageItem.tsx` and `layout.tsx` (FE-01, FE-03)
- [ ] 04-02: Add KaTeX rendering to document detail page node/page views (FE-02)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Validation and Foundation | 0/2 | Not started | - |
| 2. Ingestion Pipeline | 0/3 | Not started | - |
| 3. Retrieval and API Layer | 0/3 | Not started | - |
| 4. Frontend Rendering | 0/2 | Not started | - |
