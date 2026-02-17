# Features: Math-Aware Document Processing and Search

**Research Date:** 2026-02-17
**Milestone:** Adding math formula support to Vectorless RAG (수능 exam papers)
**Scope:** What math-aware document processing systems need — categorized by necessity

---

## Context: What This System Already Has

The existing Vectorless RAG system provides:
- PDF parsing via pypdf and PyMuPDF (text extraction only, no math awareness)
- Hierarchical PageIndex tree building from document structure
- Node enrichment: summaries, keywords, content type classification
- Dual search: Atlas Search (BM25) + LLM tree navigation
- Frontend: ReactMarkdown rendering (no math rendering)
- Data model: `Page.content` (raw text), `Node.summary/keywords` (LLM-enriched text)

Math support must extend this pipeline at three layers:
1. **Parsing layer** — extract formulas from PDF text, wrap in LaTeX delimiters
2. **Ingestion/storage layer** — preserve LaTeX in node content and metadata
3. **Frontend layer** — render LaTeX as typeset math

---

## Table Stakes (Must Have)

These are the minimum for math support to be usable. Without any one of these, the feature is broken for the stated use case (수능 exam papers).

### 1. LaTeX delimiter preservation in parsed text

**What:** When PDF text extraction produces math content, inline formulas must be wrapped in `$...$` and block formulas in `$$...$$` (or `\[...\]`). The raw page text stored in `pages.content` must contain these delimiters.

**Why it's table stakes:** If formulas are not preserved in the text that gets stored and passed to the LLM, every downstream component (summaries, keywords, answers, rendering) will be wrong. This is the root input problem.

**Complexity:** Medium-High. PyMuPDF can extract text with positional metadata; recognizing math regions requires either heuristic rules (character sets, symbol density) or a lightweight model. pypdf alone gives unreliable results for math-heavy PDFs.

**Dependencies:** Determines everything downstream. Must be solved first.

**Options ranked:**
- PyMuPDF text block analysis with heuristics → fastest, good enough for well-typeset PDFs
- PyMuPDF + Pix2Text or similar lightweight OCR/math extractor → higher accuracy
- LLM-based post-processing per page → expensive but most robust for messy PDFs

---

### 2. LaTeX in node content survives tree building

**What:** The LLM-generated tree (Mode A/B/C) and enrichment steps (summarizer, keyword extractor) must receive and forward LaTeX-delimited text without stripping it. The `Node.summary` and `Node.keywords` stored in MongoDB must contain LaTeX where relevant.

**Why it's table stakes:** The LLM reasoning loop reads `Page.content` and `Node.summary` to generate answers. If LaTeX is stripped at tree-building time (e.g., by tokenizer edge cases or prompt mishandling), the LLM cannot reason about formulas and answers will be text descriptions instead of typeset math.

**Complexity:** Low-Medium. The main risk is tiktoken token counting misbehaving on `$` characters (it should not, but needs verification). Prompts passed to the LLM need to explicitly instruct the model to preserve LaTeX delimiters in generated summaries and answers.

**Dependencies:** Depends on Feature 1. Also requires prompt engineering (Feature 3).

---

### 3. LLM prompts that preserve and reproduce LaTeX

**What:** Ingestion prompts (node summary, keyword extraction, tree generation) and retrieval prompts (sufficiency check, answer generation) must explicitly instruct the LLM to preserve `$...$` and `$$...$$` delimiters in its outputs.

**Why it's table stakes:** Without explicit instruction, Claude will often render math formulas as prose ("the quadratic formula") rather than LaTeX. The answer returned to the user must contain LaTeX for the frontend to render it.

**Complexity:** Low. Prompt additions only. Needs testing on actual 수능 content.

**Dependencies:** Depends on Feature 1 and 2. Must happen alongside Feature 2.

---

### 4. Frontend LaTeX rendering (KaTeX)

**What:** The `MessageItem` component currently uses `ReactMarkdown` with no math plugin. It must be extended to render `$...$` (inline) and `$$...$$` (block) LaTeX expressions as typeset math.

**Why it's table stakes:** If answers contain `$\int_0^1 x^2 dx = \frac{1}{3}$` and the frontend displays it as raw text, the math support is visible but broken to users. This is the output problem.

**Complexity:** Low. Standard solution: add `remark-math` + `rehype-katex` + `katex` CSS to the existing ReactMarkdown pipeline. KaTeX is preferred over MathJax: smaller bundle, faster render, no async loading jitter during streaming.

**Dependencies:** Independent of backend changes. Can be built in parallel with Features 1-3. Requires KaTeX CSS to be imported globally in `frontend/app/globals.css` or `layout.tsx`.

---

### 5. `has_math` flag on Page and Node models

**What:** Add `has_math: bool` to the `Page` model and `Node` model (alongside existing `has_table`, `has_figure`). Set during parsing based on presence of extracted math expressions.

**Why it's table stakes:** Without this flag, there is no way to filter search results or prioritize math-heavy sections, and no way to debug ingestion quality (e.g., "did this page's math get parsed?"). Also useful for Atlas Search content-type filtering.

**Complexity:** Low. Model change + setting during parsing + MongoDB index if needed for filtering.

**Dependencies:** Depends on Feature 1 (needs to know if math was found). Model changes cascade to the MongoDB save logic in `pipeline.py:save_pages()` and `save_nodes()`.

---

## Differentiators (Competitive Advantage)

These go beyond "it works" to "it works well for math exam documents specifically."

### 6. Math-aware keyword extraction

**What:** The keyword extractor (`keyword_extractor.py`) currently uses an LLM to extract 3-8 general keywords. For math documents, it should also extract mathematical concepts as keywords — e.g., "이차방정식", "극값", "삼각함수", "등차수열" — rather than just natural language terms.

**Why it differentiates:** Atlas Search queries for math content will match poorly if the stored keywords are only structural terms ("introduction", "section 3") rather than mathematical concepts. Korean math exam papers use highly standardized terminology; capturing these terms as keywords dramatically improves BM25 recall.

**Complexity:** Low. Modify the `KEYWORD_EXTRACTION_PROMPT` to explicitly request math concept keywords and Korean mathematical vocabulary. No new infrastructure.

**Dependencies:** Depends on Feature 3 (LaTeX-aware prompting). Feature 1 must have extracted math content for the LLM to detect it.

---

### 7. Math content type classification

**What:** Extend `content_classifier.py` to recognize `problem`, `solution`, `theorem`, `proof`, `formula_sheet` as content types in addition to the existing ones (section, table, figure, appendix). 수능 papers have predictable structure: numbered problems (문제), solution hints (풀이), answer keys (정답).

**Why it differentiates:** The Atlas Search pipeline already supports `content_type_filter`. If problems are classified as `problem` type, a query like "2번 문제 풀어줘" can filter to only problem nodes. This is high-signal for the target use case.

**Complexity:** Low-Medium. Pattern matching (problem number regex) covers most 수능 cases. LLM classification as fallback for ambiguous cases.

**Dependencies:** Depends on Feature 1 (math-containing content needed to classify). Independent of rendering features.

---

### 8. Graceful degradation for unextractable math

**What:** When PyMuPDF extracts a page where math formulas appear as image regions (scanned pages or image-only PDFs), the system should: (a) detect that math is likely present but unextracted, (b) flag the page/node as `math_extraction_failed`, (c) return a clear user-facing message rather than silently returning garbage text.

**Why it differentiates:** 수능 papers distributed as scanned PDFs are common (older exams, photocopied versions). Silently returning incomplete text is worse than surfacing the limitation. Users can then use a different PDF source.

**Complexity:** Medium. Heuristic: if a page has low text density but high image count (PyMuPDF `page.get_images()`), flag as likely-scanned. No OCR integration needed (out of scope per PROJECT.md).

**Dependencies:** Depends on Feature 1's parsing approach. Independent of rendering.

---

### 9. LaTeX normalization and canonicalization

**What:** PDF text extraction often produces non-canonical LaTeX: `x^2+3x` vs `x^{2}+3x`, missing braces, mixed encoding. A normalization step post-extraction converts to canonical KaTeX-compatible LaTeX before storage.

**Why it differentiates:** KaTeX is strict about LaTeX syntax. Malformed LaTeX causes rendering errors in the frontend. Normalization prevents a class of runtime rendering failures that would otherwise require user debugging.

**Complexity:** Medium. Requires a LaTeX normalization library (e.g., `latex2mathml`, sympy's latex parser for validation) or a set of regex transformations for common PDF extraction artifacts. Risk: over-normalization can change meaning.

**Dependencies:** Depends on Feature 1 (extraction must happen first). Feeds into Feature 4 (rendering quality).

---

### 10. Math-aware text chunking for node splitting

**What:** The existing node splitter (`tree_builder/splitter.py`) splits large nodes at page boundaries with token limits. Math-aware splitting avoids breaking in the middle of a formula or problem statement — it finds natural break points between problems, not mid-formula.

**Why it differentiates:** If a 수능 problem is split across two nodes at a `$$...$$` boundary, neither node has the complete problem context. The LLM reasoning loop will see partial problems and may fail to answer correctly.

**Complexity:** High. Requires detecting problem boundaries (problem number regex) and formula boundaries (matching `$$` delimiters). The `process_large_node_recursively` function in `splitter.py` needs significant rework.

**Dependencies:** Depends on Feature 1 (need LaTeX delimiters to find boundaries). This is the riskiest feature — defer unless chunking quality is measurably poor.

---

## Anti-Features (Deliberately Not Building)

These are things math-aware systems often include, but should be explicitly excluded from scope for this project.

### A. Math formula OCR (image-based extraction)

**What:** Extracting formulas from scanned/image PDFs using tools like MathPix, Pix2Text, or Nougat.

**Why excluded:** PROJECT.md explicitly states: "수식 OCR (이미지 기반 수식 인식) — PDF 텍스트 레이어의 수식만 대상." The system only targets PDFs with a text layer. Adding OCR introduces a heavy dependency (GPU or paid API), complex async pipeline, and significantly longer ingestion time. The simpler degradation (Feature 8) is sufficient.

---

### B. Vector embeddings for math semantic search

**Why excluded:** The entire project is "Vectorless RAG." Math formulas create particularly poor embedding representations — $\int_0^1 x^2$ and $\int_0^1 x^3$ are semantically distant by meaning but very close in token space. The tree navigation approach with LLM reasoning is actually better for math content than embeddings.

---

### C. Formula similarity search / math search engine

**What:** Systems like zbMATH, arXiv search, or Wolfram that let you search by formula structure (e.g., "find all equations with a quadratic term").

**Why excluded:** This is a specialized math search engine feature requiring formula parsing into expression trees (MathML/OMDoc). The use case (educators querying exam papers in natural language) does not need structural formula search. The LLM's natural language understanding covers this adequately.

---

### D. Interactive formula editor

**What:** Letting users type or draw math formulas as search queries via a LaTeX editor widget.

**Why excluded:** The target users (educators/researchers) query in natural language Korean ("2차 방정식의 해를 구하는 문제"). LaTeX input would add UI complexity with minimal benefit for this audience.

---

### E. Real-time formula rendering during ingestion status

**What:** Showing formula previews while a document is being processed.

**Why excluded:** Ingestion is async and runs in a thread pool. The status page shows ingestion progress. Adding formula preview streaming during ingestion adds frontend complexity for a feature users will see for at most a few minutes and then never again.

---

### F. Multi-document math formula cross-referencing

**What:** Finding the same formula across multiple uploaded exam papers.

**Why excluded:** The existing system scopes all queries to a single `document_id`. Multi-document search would require significant retrieval pipeline changes unrelated to math support. This is a separate milestone if needed.

---

## Feature Dependencies Summary

```
Feature 1 (LaTeX extraction from PDF)
    └── Feature 2 (LaTeX survives tree building)
        └── Feature 3 (LLM prompts preserve LaTeX)
            └── Feature 6 (Math-aware keywords)
    └── Feature 5 (has_math flag)
    └── Feature 7 (Math content type classification)
    └── Feature 8 (Graceful degradation for image PDFs)
    └── Feature 9 (LaTeX normalization)
        └── Feature 4 (Frontend KaTeX rendering) [also standalone]
    └── Feature 10 (Math-aware chunking) [defer, highest risk]

Feature 4 (KaTeX rendering) — independent of all backend features
```

## Implementation Order Recommendation

**Phase 1 (Table Stakes, ~1-2 days):**
1. Feature 1: PyMuPDF-based math detection and LaTeX wrapping
2. Feature 5: `has_math` flag on Page and Node
3. Feature 4: KaTeX in frontend (parallel, independent)

**Phase 2 (Table Stakes, ~1 day):**
4. Feature 3: Update LLM prompts to preserve LaTeX
5. Feature 2: Verify LaTeX survives full ingestion pipeline end-to-end

**Phase 3 (Differentiators, if Phase 2 works well):**
6. Feature 6: Math-aware keyword extraction
7. Feature 7: Math content type classification
8. Feature 8: Graceful degradation
9. Feature 9: LaTeX normalization (only if rendering errors appear)
10. Feature 10: Math-aware chunking (only if answer quality is poor)

---

## Open Questions for Requirements Phase

1. **How does PyMuPDF represent 수능 math on PDFs with text layers?** Run `page.get_text("dict")` on a real 수능 PDF to see if formulas appear as distinct text blocks, as Unicode math symbols, or as garbled characters. This determines whether heuristic detection is viable.

2. **Which 수능 PDF sources will be used?** Official KSAT PDFs from CSAT (수능시험관리위원회) have proper text layers. Unofficial scans do not. Knowing the input source determines whether Feature 8 (graceful degradation) is needed urgently.

3. **KaTeX vs MathJax for Feature 4?** KaTeX is recommended (smaller, faster, works in SSE streaming). MathJax has better coverage of obscure LaTeX commands but adds ~200KB to bundle. Decision: KaTeX unless specific 수능 notation is not supported.

4. **Which LaTeX encoding does the PDF use?** PDFs using Type 3 fonts for math may extract as private-use Unicode characters rather than LaTeX. If this is the case, a character mapping table is needed (significant complexity).

---

*Research basis: codebase analysis of existing system + domain knowledge of math-aware document processing patterns. No external web search used.*
