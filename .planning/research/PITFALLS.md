# PITFALLS — Math-Aware PDF Parsing and LaTeX Rendering

**Research Date:** 2026-02-17
**Milestone:** Adding math formula extraction from Korean math exam PDFs and LaTeX rendering to Vectorless RAG
**Domain:** PDF text-layer extraction (PyPDF/PyMuPDF) + LaTeX rendering (KaTeX/MathJax) + LLM tree building with math content

---

## Pitfall 1: PyMuPDF/PyPDF text extraction produces garbled math symbols, not LaTeX

**Domain:** PDF Parsing — Ingestion Phase

**Description:**
Korean math exam PDFs (수능/시험 문제지) typically use Type1 or TrueType fonts to embed math symbols. `page.get_text()` (PyMuPDF) and `page.extract_text()` (PyPDF) extract the *Unicode codepoint* of each glyph — but PDF publishers often use custom private-use fonts where, for example, the integral sign `∫` is encoded as a font-specific glyph with no predictable Unicode mapping. The result is that the extracted text contains either garbage characters (e.g., `�`, `□`), random ASCII letters substituted for symbols, or empty strings where formulas should be. You get no LaTeX — you get whatever the font encoding says, which is almost never valid LaTeX.

**Warning Signs:**
- Extracted text from a known math page contains long runs of `?`, `□`, or empty lines where formulas should appear
- Token count for math-heavy pages is suspiciously low compared to prose pages
- `page.get_text("rawdict")` or `page.get_text("dict")` reveals glyph names like `uni0041` instead of recognizable symbol names
- Symbols like `≤`, `≥`, `∑`, `∫`, `√` appear as private-use Unicode (U+E000–U+F8FF range) when inspecting raw bytes

**Prevention Strategy:**
1. Test extraction on a real 수능 PDF before designing the math pipeline. Run both backends (`pypdf` and `PyMuPDF`) and inspect raw output for pages 1-5 of a typical exam paper. Compare what is actually extracted vs. what is visually present.
2. If symbols are garbled: accept that text-layer extraction cannot recover formula LaTeX without OCR or PDF structure analysis. The only reliable path at the text-layer level is to detect formula regions and pass them to an LLM (Claude) for reconstruction — not to regex-match LaTeX delimiters that are not present in the raw text.
3. If symbols are partially preserved (Unicode math block U+2200–U+22FF): a symbol-to-LaTeX mapping table can convert common symbols. Libraries like `sympy.parsing.latex` or a custom lookup table can reconstruct simple expressions.
4. Add a per-page diagnostic in `parse_pdf()` that counts math-range Unicode codepoints and warns when a page has zero math characters but comes from a known math document. This will catch extraction failures early in ingestion.

**Phase:** Ingestion — `src/ingestion/parsers/pdf_parser.py` — before designing any downstream formula logic.

---

## Pitfall 2: Assuming `$...$` or `$$...$$` delimiters exist in raw PDF text

**Domain:** PDF Parsing → Math Detection — Ingestion Phase

**Description:**
The project description says "inline ($...$) and block ($$...$$) LaTeX" — but these delimiters only exist in LaTeX source files, not in the text layer of a compiled PDF. A PDF produced from LaTeX source has already been *rendered*: the `$...$` markers are gone and the formula is rasterized glyphs (in image-based PDFs) or Unicode character sequences (in text-layer PDFs). Searching for dollar-sign delimiters in PyMuPDF/PyPDF output will find zero matches in authentic Korean exam PDFs because those PDFs are not generated from LaTeX source — they are produced by Korean typesetting tools (Hangul Word Processor, InDesign, etc.) that use their own math renderers.

**Warning Signs:**
- A regex like `re.findall(r'\$[^$]+\$', page_text)` returns no matches on real exam PDFs
- The LLM prompt asking Claude to "extract LaTeX formulas marked with $" finds no formulas even on math-heavy pages
- Unit tests pass when using synthetic text strings with `$...$` but fail completely on actual uploaded PDFs

**Prevention Strategy:**
1. Do not design any pipeline step that depends on finding dollar-sign delimiters in PDF-extracted text. The delimiters must be *added* by the pipeline (either through symbol mapping or LLM generation), not found.
2. The correct framing: the pipeline extracts Unicode text (possibly garbled), then uses Claude to interpret regions as math and produce LaTeX markup. Claude receives the raw extracted text and is asked: "Rewrite any mathematical expressions in this text using LaTeX notation ($...$ for inline, $$...$$ for block)."
3. Test this assumption on day one: take a real 수능 PDF, run `parse_pdf()`, print the first math page, and verify whether any dollar signs appear.

**Phase:** Ingestion design — must be settled before writing any math detection code.

---

## Pitfall 3: LLM prompts receive math-corrupted text and produce hallucinated formulas

**Domain:** LLM Tree Building and Enrichment — Ingestion Phase

**Description:**
The current `TREE_GENERATION_INIT_PROMPT`, `NODE_SUMMARY_PROMPT`, and `KEYWORD_EXTRACTION_PROMPT` pass raw page text to Claude. If that text is `f(x) = □□ + □□` (because PyMuPDF could not decode the font), Claude will hallucinate plausible math based on context clues. The hallucinated LaTeX may be structurally valid but semantically wrong — for example, generating `f(x) = x^2 + 3x` when the actual formula is `f(x) = \sin(x) + \cos(x)`. This is especially dangerous because:
1. The wrong formula looks correct — it renders as valid LaTeX.
2. Downstream retrieval queries asking about specific formulas will match the wrong sections.
3. There is no ground truth in the system to detect the error.

**Warning Signs:**
- LLM-generated summaries and keywords mention mathematical concepts that are not visible in the extracted text
- Two different runs of ingestion on the same PDF produce different formula outputs (non-deterministic hallucination)
- The LLM prompt context window contains long runs of `□` or `?` characters
- Keyword extraction returns LaTeX strings like `\int_0^\infty` for a page that clearly extracted as empty

**Prevention Strategy:**
1. Add a math-quality diagnostic step during ingestion: before passing page text to any LLM, count the ratio of recognizable Unicode math symbols to total characters. If the ratio is below a threshold (e.g., fewer than 3 math characters per 100 chars on a page classified as "math-heavy"), log a warning that formula extraction may be unreliable.
2. In math-aware prompts, explicitly instruct Claude: "If a formula cannot be determined from the text, use `[ILLEGIBLE_FORMULA]` as a placeholder rather than guessing." This converts hallucination risk into explicit uncertainty.
3. Add a `formula_confidence` field to node metadata so the retrieval pipeline can deprioritize or flag low-confidence formula sections.
4. Separate the math extraction LLM call from the tree building call. The current pipeline uses one LLM call for tree structure. Adding formula reconstruction to that same call bloats the prompt and degrades tree quality.

**Phase:** Ingestion enrichment — `src/ingestion/enrichment/` — design before writing math LLM prompts.

---

## Pitfall 4: Atlas Search BM25 cannot match LaTeX syntax

**Domain:** Retrieval — Atlas Search — Retrieval Phase

**Description:**
The Atlas Search pipeline in `src/retrieval/atlas_search.py` uses BM25 full-text search on the `title`, `summary`, and `keywords` fields of nodes. If formulas are stored as LaTeX strings like `\frac{d}{dx}\sin(x) = \cos(x)`, a user query like "sin x 미분" (Korean for "derivative of sin x") will not match because:
1. BM25 tokenizes on word boundaries — `\frac`, `{d}`, `{dx}`, `\sin` are separate tokens, none of which match "sin", "미분", or "derivative".
2. LaTeX backslash-prefixed commands are treated as distinct tokens from their natural-language equivalents.
3. Korean query terms are tokenized differently from ASCII math tokens.

The current search pipeline already has TITLE_BOOST=10.0, SUMMARY_BOOST=5.0, KEYWORD_BOOST=3.0 — but none of these boosts help when the tokens don't match at all.

**Warning Signs:**
- Queries about specific formulas return zero or low-relevance results even when the correct section is in the index
- `atlas_search()` returns high-scoring results for prose sections but low scores for formula-heavy sections
- User queries in Korean with math intent match only Korean text sections, not math formula sections

**Prevention Strategy:**
1. Store both the LaTeX representation AND a natural-language description of each formula in the node's keywords or a dedicated `formula_descriptions` field. Example: `{"latex": "\\frac{d}{dx}\\sin(x)", "description": "sin x의 도함수, 삼각함수 미분"}`. Search against the description, render the LaTeX.
2. During keyword extraction (`src/ingestion/enrichment/keyword_extractor.py`), instruct the LLM to generate Korean natural-language keywords for each formula: "코사인 함수, 삼각함수 미분, 도함수 공식".
3. Do not store raw LaTeX strings as MongoDB text search fields. LaTeX is a display format, not a search format.
4. The tree navigation component (weight 0.7) is better suited to math queries than Atlas Search (weight 0.3) because Claude can reason about formula meaning. The current weights may need adjustment — consider raising tree navigation weight for documents classified as math-heavy.

**Phase:** Retrieval — must be addressed when designing how formulas are stored in the node schema, before ingestion runs on real exam PDFs.

---

## Pitfall 5: KaTeX SSR/hydration mismatch causes React errors in Next.js 15 App Router

**Domain:** Frontend LaTeX Rendering — Frontend Phase

**Description:**
KaTeX renders math by generating DOM nodes. In Next.js 15 App Router, Server Components render HTML on the server and the client hydrates it. If a `<KaTeX>` or `<MathJax>` component is rendered on the server, it produces specific DOM structure. If the client-side rendering produces even slightly different DOM (e.g., different attribute order, slightly different span nesting), React 19's strict hydration will throw a hydration mismatch error and unmount the component. This is especially common because:
1. KaTeX generates `<span class="katex">` with nested spans — the exact output can vary with KaTeX version.
2. Server and client may have different font metric data, causing different line-breaking decisions.
3. The `suppressHydrationWarning` on `<html>` in `frontend/app/layout.tsx` suppresses the root element warning but does not suppress errors in child components.

**Warning Signs:**
- Console errors: `Error: Hydration failed because the server rendered HTML didn't match the client`
- Math renders correctly on first server load but flickers or disappears after hydration
- `next build` succeeds but `next start` shows hydration errors in production
- KaTeX/MathJax renders during SSR but logs `window is not defined` errors (KaTeX uses browser APIs)

**Prevention Strategy:**
1. Wrap all math rendering components in `'use client'` directive. The current `MessageItem.tsx` is already `'use client'`, which is correct. Any new math renderer component must also be client-only.
2. Use dynamic imports with `ssr: false` for the math rendering library: `const MathRenderer = dynamic(() => import('./MathRenderer'), { ssr: false })`. This prevents server-side rendering entirely and eliminates hydration mismatches.
3. For `react-markdown` (already installed as of v10.1.0), the math plugin integration via `remark-math` + `rehype-katex` requires both packages to be installed and configured in the `ReactMarkdown` component. Missing either will silently skip formula rendering.
4. Test SSR behavior explicitly: run `npm run build && npm run start` (not `npm run dev`, which uses a different rendering path) and check for hydration errors on the chat page.

**Phase:** Frontend — when adding KaTeX/MathJax to `MessageItem.tsx` and any new math display components.

---

## Pitfall 6: `react-markdown` does not render LaTeX by default — requires remark-math + rehype-katex plugin chain

**Domain:** Frontend Markdown/Math Rendering — Frontend Phase

**Description:**
The current `MessageItem.tsx` uses `<ReactMarkdown>{message.content}</ReactMarkdown>` for assistant messages. `react-markdown` renders standard Markdown but treats `$...$` and `$$...$$` as literal text characters — it has no built-in math awareness. Without the `remark-math` plugin (which parses math AST nodes) and `rehype-katex` plugin (which converts them to KaTeX HTML), LaTeX formulas stored in message content will appear as raw dollar-sign-wrapped text: `$\frac{1}{2}$` rendered literally as `$\frac{1}{2}$`.

**Warning Signs:**
- Dollar signs appear literally in the chat UI even after KaTeX is installed
- No error is thrown — `react-markdown` simply ignores delimiters it does not understand
- The formula renders correctly in a standalone KaTeX test but not in the message display

**Prevention Strategy:**
1. Install the full plugin chain: `npm install remark-math rehype-katex katex`. The package `katex` must be explicitly installed as a peer dependency.
2. Import and configure in `MessageItem.tsx`:
   ```typescript
   import remarkMath from 'remark-math'
   import rehypeKatex from 'rehype-katex'
   import 'katex/dist/katex.min.css'
   ```
   Pass plugins to `<ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>`.
3. The KaTeX CSS import (`katex/dist/katex.min.css`) is mandatory. Without it, formulas render as unstyled HTML that is illegible.
4. In Next.js App Router, global CSS must be imported in a Server Component or `layout.tsx`, not in a Client Component (where CSS imports may be dropped). Import `katex/dist/katex.min.css` in `frontend/app/layout.tsx` or `frontend/app/globals.css`, not inside `MessageItem.tsx`.

**Phase:** Frontend — first task when adding math rendering.

---

## Pitfall 7: Korean characters in math context corrupt tiktoken token counting

**Domain:** Ingestion — Token Counting — Ingestion Phase

**Description:**
The current `parse_pdf()` in `src/ingestion/parsers/pdf_parser.py` uses `tiktoken.encoding_for_model(model)` with default model `gpt-4o` to count tokens per page. Korean text (Hangul) tokenizes at roughly 1.5-2.5 tokens per character in tiktoken's cl100k_base encoding (the encoding used by gpt-4o), compared to 0.25 tokens per character for ASCII. A math exam page with 200 characters of Korean + 50 characters of math may actually be 400-600 tokens. If the system uses token counts to decide how many pages to bundle into a node (via `MAX_TOKENS_PER_NODE=20000`), Korean math pages will be bundled at fewer pages per node than expected. The downstream effect: more nodes with less content each, which degrades the tree navigation quality because leaf nodes become very small.

**Warning Signs:**
- Korean math PDFs produce 3-5x more nodes than equivalent English PDFs with the same page count
- Tree visualization shows very shallow, wide trees with many small leaf nodes
- `total_tokens` in the document record is much higher than expected
- Node content when loaded shows only 1-2 pages per leaf node for Korean content

**Prevention Strategy:**
1. Test token counting on a sample Korean math page early: extract a page of 수능 math text, count tokens with tiktoken, and verify the counts are sensible. Document the expected range for a typical Korean math exam page.
2. Consider making `MAX_TOKENS_PER_NODE` configurable per document language. Korean documents may need a higher token budget per node (e.g., 30000-40000 instead of 20000) to keep comparable page ranges per node.
3. The tiktoken `gpt-4o` model is used for consistency with the Anthropic Claude API, but Claude uses its own tokenizer. The token counts are approximations used for chunking decisions — this is acceptable, but the Korean tokenization inflation must be understood.

**Phase:** Ingestion — test before running on real Korean math PDFs.

---

## Pitfall 8: Korean math exam PDFs have no Table of Contents — tree building falls through to mode C (LLM-generated hierarchy)

**Domain:** Ingestion — Tree Building — Ingestion Phase

**Description:**
The ingestion pipeline has three fallback modes for tree building: A (ToC with page numbers), B (ToC without page numbers), C (LLM-generated from content). Korean math exam papers (수능, 모의고사) typically have no Table of Contents — they are structured as numbered problem sets (문제 1, 문제 2, etc.) without a navigable ToC. Mode C relies entirely on the LLM to infer hierarchical structure from raw page content. With math-corrupted text (Pitfall 1), mode C will try to build a tree from pages containing mostly garbled symbols and Korean problem statements. The LLM may:
1. Create a flat tree (all problems at depth 1) with no meaningful hierarchy
2. Group problems incorrectly because formula content is unreadable
3. Assign wrong page ranges if the physical page markers (`<physical_index_X>`) are adjacent to corrupted text

**Warning Signs:**
- `no_toc_found` appears in logs for every Korean math exam upload
- Tree depth is always 1 (flat list of problems) regardless of document structure
- Node titles are generic ("문제", "수학 문제") rather than meaningful section titles
- `ingestion.errors` in the document record shows multiple `tree_generation` failures before mode C succeeds

**Prevention Strategy:**
1. For Korean math exam PDFs, accept that mode C is the expected path and tune the `TREE_GENERATION_INIT_PROMPT` to handle problem-set structure: "If the document is a math exam with numbered problems, create nodes for each numbered problem or problem group."
2. Add a document-type hint that can be passed at upload time (e.g., `"document_type": "math_exam"`) which selects a specialized mode C prompt optimized for numbered problem sets.
3. Test mode C on a real 수능 PDF early to assess tree quality. Do not assume mode C produces a useful hierarchy without validation.
4. Consider adding problem-number detection as a pre-processing step: scan pages for patterns like `문제\s*\d+` or `[0-9]+\.` at the start of lines. This structured detection can provide anchor points for tree building that are more reliable than the general LLM approach.

**Phase:** Ingestion — design before the first real Korean exam PDF ingestion run.

---

## Pitfall 9: LaTeX backslash sequences break JSON serialization in LLM responses

**Domain:** Ingestion — LLM JSON Parsing — Ingestion / Retrieval Phase

**Description:**
LaTeX commands contain backslashes: `\frac`, `\sqrt`, `\int`, `\alpha`. When an LLM returns a JSON object containing LaTeX in a string field — for example, `{"title": "부등식 \frac{a}{b} \geq 0", "page": 1}` — the backslashes must be double-escaped in JSON: `{"title": "부등식 \\frac{a}{b} \\geq 0", "page": 1}`. Claude frequently returns single-escaped backslashes in JSON (valid LaTeX, invalid JSON), causing `json.JSONDecodeError`. The current `src/utils/json_utils.py` has a "Python literal cleanup" fallback that attempts `ast.literal_eval()` — but `ast.literal_eval()` does not handle backslash-escape sequences in LaTeX either. The result is silent `None` returns from `extract_json()`, which causes entire tree-building LLM calls to produce no output.

**Warning Signs:**
- `json_utils.py` returns `None` for responses that visually contain valid JSON
- Tree building succeeds for prose documents but fails on math documents (falls back from mode A→B→C or returns empty tree)
- Logging shows `json_parse_failed` events specifically when math content is present
- Manual inspection of LLM raw responses shows JSON like `{"formula": "\frac{1}{2}"}` (single backslash — invalid JSON)

**Prevention Strategy:**
1. Add a backslash pre-processing step in `extract_json()`: after extracting the JSON substring, attempt `text.replace('\\', '\\\\')` before the first `json.loads()` call, but only as a fallback when the initial parse fails. This is a targeted fix for the LaTeX case.
2. In LLM prompts that may return formulas in JSON, explicitly instruct Claude: "In JSON strings, use double backslashes for LaTeX commands: \\frac, \\sqrt, \\int." Add this instruction to any prompt that may include math in its JSON output.
3. Add a test case to `tests/test_json_utils.py` that verifies `extract_json()` correctly handles JSON containing single-escaped LaTeX backslashes.
4. Consider storing formulas as a separate structured field outside the primary JSON, or using a delimiter-based format that avoids the backslash problem entirely (e.g., XML CDATA sections, or a custom `[FORMULA]...[/FORMULA]` tag).

**Phase:** Ingestion and Retrieval — `src/utils/json_utils.py` — must be fixed before any math-aware LLM calls are made.

---

## Pitfall 10: MathJax is significantly heavier than KaTeX and causes render-blocking in React 19

**Domain:** Frontend — Library Selection — Frontend Phase

**Description:**
MathJax v3 is a full LaTeX rendering engine: the core bundle is 500KB+ minified, loads asynchronously, and uses a global `window.MathJax` configuration object. React 19 with Next.js 15 App Router uses strict concurrent rendering — global singleton state (like `window.MathJax`) conflicts with React's rendering lifecycle, causing intermittent rendering failures when multiple chat messages update concurrently (e.g., during SSE streaming). KaTeX, by contrast, is a pure function: `katex.renderToString(latex, options)` has no global state, is ~300KB minified (including fonts), and integrates cleanly with React's render cycle. The chat page is streaming-heavy (SSE stream updating messages in real time), which makes global-state-based rendering especially fragile.

**Warning Signs:**
- Math formulas disappear during streaming and only appear after streaming stops
- Console errors: `MathJax is not defined` or `Cannot read property 'typeset' of undefined` during fast message updates
- Performance profiler shows main-thread blocking during formula rendering in the streaming phase
- MathJax `typeset()` calls queue up and process out of order during React state updates

**Prevention Strategy:**
1. Use KaTeX for this project. The combination of `remark-math` + `rehype-katex` (via `react-markdown`) is the established, well-tested integration path for React streaming contexts.
2. If KaTeX does not support a specific LaTeX command used in Korean math exams (e.g., certain AMSmath environments), handle the unsupported command by displaying the raw LaTeX as a code block fallback rather than switching to MathJax for the entire page.
3. KaTeX's `throwOnError: false` option prevents the renderer from crashing on unsupported commands — it renders an error placeholder instead. Enable this option in the `rehypeKatex` configuration to prevent render failures from blocking the entire message display.

**Phase:** Frontend — library selection must be made before installing any math renderer.

---

## Pitfall 11: Large Korean exam PDFs with many image-based formula regions exhaust PyMuPDF memory

**Domain:** Ingestion — PDF Parsing — Ingestion Phase

**Description:**
Some Korean math exam PDFs (especially scanned or print-quality versions) use embedded images for formulas while having Korean text in the text layer. When PyMuPDF's `page.get_text()` is called on such pages, it extracts only the text layer (Korean words) and silently omits all formula images. The page text looks complete (Korean sentences with placeholder spaces) but all math is missing. Additionally, calling `doc.load_page(i)` for all pages of a large exam PDF before extracting text can cause memory spikes because PyMuPDF keeps page rendering data in memory. For a 100-page exam PDF with high-resolution embedded images, this can exceed 500MB in the current synchronous parsing implementation.

**Warning Signs:**
- Extracted page text contains Korean sentences but zero math symbols, even for clearly formula-heavy pages
- `token_count` for math pages is identical to or lower than Korean prose pages of the same length
- Memory usage during ingestion grows linearly with PDF page count and does not decrease until parsing is complete
- PyMuPDF logs or OS-level OOM killer events during large PDF ingestion

**Prevention Strategy:**
1. Use `page.get_text("dict")` instead of `page.get_text()` during development to inspect whether the page has image blocks (`"type": 1`) mixed with text blocks (`"type": 0`). If image blocks are present where formulas should be, the PDF is partially or fully image-based.
2. Release page memory explicitly: in the PyMuPDF loop in `parse_pdf()`, the `doc.close()` in the `finally` block is correct, but individual page objects should be set to `None` after text extraction to allow garbage collection within the loop.
3. For the current milestone (text-layer extraction only), document in the upload UI that image-based formula PDFs are not supported. Add a `formula_extraction_method: text_layer` metadata field to documents to make this limitation explicit.
4. Out of scope for text-layer-only extraction: OCR-based formula recognition (e.g., pix2tex, MathPix). This is correctly excluded per the project's `Out of Scope` requirements.

**Phase:** Ingestion — test on representative Korean math PDFs before committing to the architecture.

---

## Pitfall 12: Streaming SSE responses break when formula strings contain special SSE characters

**Domain:** API — SSE Streaming — API Phase

**Description:**
The streaming endpoint in `src/api/routes/stream.py` uses Server-Sent Events. SSE protocol uses `data:`, `event:`, and `id:` field prefixes, with events separated by double newlines (`\n\n`). LaTeX formulas can contain characters that break SSE encoding:
1. Newlines in LaTeX (`\\` for line break in align environments) will split an SSE event prematurely
2. The colon character (`:`) in LaTeX like `\mathbb{R}: x > 0` may be misinterpreted if it appears at the start of an SSE line
3. JSON-serialized LaTeX in the `data:` field must be double-JSON-encoded if the formula itself contains double quotes

The current SSE implementation in `stream.py` serializes events as JSON objects. If the answer text contains `\n\n` (a LaTeX display math separator or a paragraph break containing math), the SSE parser in the browser will treat it as an event separator and split the data payload, corrupting the JSON.

**Warning Signs:**
- Frontend SSE parser (`use-chat-stream.ts`) receives malformed JSON events when responses contain math
- Chat messages with block math (`$$...$$`) appear cut off or missing
- Browser developer tools show SSE events with empty `data:` fields following math-heavy responses
- The `EventSource` connection closes unexpectedly mid-stream when formula content is being sent

**Prevention Strategy:**
1. Ensure all SSE `data:` payloads are JSON-serialized using `json.dumps()` with no additional escaping. Python's `json.dumps()` handles newline escaping (`\n` → `\\n`) correctly within string values, so LaTeX newlines will be safely encoded.
2. Verify that the SSE event construction in `stream.py` uses `f"data: {json.dumps(event_dict)}\n\n"` — the double newline must follow the *entire* JSON object, not be split by content within it.
3. Add an integration test specifically for streaming responses that contain LaTeX block math: send a mock answer containing `$$\n\alpha = \beta\n$$` and verify the SSE stream delivers it intact.

**Phase:** API — `src/api/routes/stream.py` — verify when first adding math to streaming responses.

---

## Summary Table

| # | Pitfall | Domain | Phase | Severity |
|---|---------|--------|-------|----------|
| 1 | PDF text layer produces garbled symbols, not LaTeX | PDF Parsing | Ingestion | Critical |
| 2 | Assuming `$...$` delimiters exist in PDF text | PDF Parsing | Ingestion | Critical |
| 3 | LLM hallucinates formulas from corrupted text | LLM Enrichment | Ingestion | High |
| 4 | Atlas Search BM25 cannot match LaTeX syntax | Retrieval | Retrieval | High |
| 5 | KaTeX SSR/hydration mismatch in Next.js 15 | Frontend | Frontend | High |
| 6 | `react-markdown` skips math without plugin chain | Frontend | Frontend | High |
| 7 | Korean text inflates tiktoken counts, disrupts chunking | Token Counting | Ingestion | Medium |
| 8 | Korean exam PDFs have no ToC, fall to mode C | Tree Building | Ingestion | Medium |
| 9 | LaTeX backslashes break JSON serialization | JSON Parsing | Ingestion + Retrieval | High |
| 10 | MathJax conflicts with React 19 concurrent rendering | Frontend | Frontend | Medium |
| 11 | Image-based formula PDFs silently drop all math | PDF Parsing | Ingestion | Medium |
| 12 | LaTeX newlines corrupt SSE stream protocol | Streaming | API | Medium |

---

*Research date: 2026-02-17. Based on: codebase analysis of src/ingestion/parsers/pdf_parser.py, src/utils/json_utils.py, src/retrieval/atlas_search.py, src/api/routes/stream.py, frontend/components/chat/MessageItem.tsx, and domain knowledge of PDF text extraction, LaTeX rendering in React, and Korean font encoding challenges.*
