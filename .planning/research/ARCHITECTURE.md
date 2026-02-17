# Architecture Research: Math Formula Extraction Integration

**Research Type:** Project Research — Architecture dimension
**Milestone:** Subsequent milestone — math formula parsing integration into existing 5-layer pipeline
**Date:** 2026-02-17
**Question:** How should math formula extraction integrate with an existing PDF ingestion pipeline, and how should LaTeX rendering be added to a Next.js frontend?

---

## 1. Summary

The existing system is a 5-layer vectorless RAG pipeline (API → Ingestion → Retrieval → Data → LLM). Math formula extraction fits cleanly as an extension to the **Ingestion layer** — specifically at two sub-stages: the **PDF parser** (extraction) and the **enrichment step** (classification). On the frontend, LaTeX rendering adds a thin rendering layer to the existing **MessageItem** chat component, without touching state management or the API client.

The integration does not require new layers and does not change the retrieval or LLM reasoning pipeline. It adds one new field to the `pages` collection, one new field to the `nodes` collection, and one new npm package to the frontend.

---

## 2. Existing Architecture (Relevant Parts)

### 2.1 Ingestion Pipeline (current)

```
POST /ingest/upload
  └── src/api/routes/ingest.py: _extract_text_from_upload()
        └── src/ingestion/parsers/pdf_parser.py: parse_pdf()
              Returns: List[ParsedPage(page_number, text, token_count, content_hash)]
        └── src/ingestion/pipeline.py: page_index_main(page_list)
              page_list: List[Tuple[str, int]]  ← (text, token_count) per page
              ├── tree_parser()                 ← ToC detect + tree build
              │     ├── check_toc()
              │     ├── meta_processor()        ← 3-mode LLM tree generation
              │     └── post_processing()       ← node IDs, materialized paths
              ├── write_node_id()
              ├── add_node_text()
              └── generate_summaries_for_structure()  ← enrichment
        └── save_document() / save_nodes() / save_pages()
```

### 2.2 Data Model (current)

**pages collection** (`src/models/page.py`):
```python
class Page(BaseModel):
    document_id: str
    page_number: int
    node_id: str
    content: str          # raw extracted text
    content_hash: str
    token_count: int
    has_table: bool
    has_figure: bool
    language: str
```

**nodes collection** (`src/models/node.py`):
```python
class Node(BaseModel):
    node_id: str
    title: str
    summary: str
    start_page: int
    end_page: int
    keywords: List[str]
    content_type: str     # section|appendix|table|figure|preface|bibliography
    has_table: bool
    has_figure: bool
    cross_references: List[CrossReference]
    is_leaf: bool
```

### 2.3 Frontend (current)

- `frontend/components/chat/MessageItem.tsx` renders assistant messages with `<ReactMarkdown>` (already installed)
- `react-markdown@10.1.0` is a direct dependency
- No LaTeX/math rendering exists today
- `@tailwindcss/typography` provides prose styling already

---

## 3. Integration Architecture

### 3.1 Where Math Extraction Fits

Math extraction belongs in **two places** inside the Ingestion layer:

```
Ingestion Layer
├── parsers/
│   └── pdf_parser.py          ← PHASE 1: Extract math alongside text
│         parse_pdf() already uses pypdf or PyMuPDF backends.
│         PyMuPDF can extract formula bounding boxes + render to image.
│         New output: ParsedPage gains a `math_expressions` field.
│
└── enrichment/
    └── math_classifier.py     ← PHASE 2: Classify math-density of nodes
          New enrichment step parallel to content_classifier.py.
          Scans node text for LaTeX patterns, sets has_math flag + math_expressions[].
```

**Not** in the Retrieval layer. Not in the LLM layer. The retrieval pipeline already handles LaTeX text as plain text through Atlas Search BM25 and LLM reasoning — no changes needed there.

### 3.2 Extraction Strategy

Two extraction strategies, selectable by backend:

**Strategy A — Text-pattern extraction (pypdf backend)**
- pypdf extracts text including Unicode math symbols
- Post-process with regex to detect LaTeX delimiters: `$...$`, `$$...$$`, `\begin{equation}`, `\[...\]`
- Works for text-based PDFs that embed LaTeX source
- No additional Python dependencies beyond what is already installed

**Strategy B — Structural extraction (PyMuPDF backend)**
- `page.get_text("dict")` returns blocks with text spans and font metadata
- Detect math by font name heuristic (CMEX, CMMI, Symbol) or explicit math flags
- `page.get_drawings()` + `page.get_text("rawdict")` can isolate formula bounding boxes
- Optionally render formula regions to PNG for display: `page.get_pixmap(clip=bbox)`
- PyMuPDF 1.24+ is already a project dependency (`pyproject.toml`)

Recommended: **Strategy A as default**, Strategy B as opt-in (controlled by a new config setting `math_extraction_backend: str = "regex"`).

### 3.3 New Data Fields

**ParsedPage** (runtime only, not persisted):
```python
@dataclass
class ParsedPage:
    page_number: int
    text: str
    token_count: int
    content_hash: str
    math_expressions: list[str] = field(default_factory=list)  # NEW: LaTeX strings
```

**Page model** (`src/models/page.py`):
```python
class Page(BaseModel):
    # ... existing fields ...
    has_math: bool = Field(False, alias="hasMath")             # NEW
    math_expressions: list[str] = Field(default_factory=list,
                                        alias="mathExpressions")  # NEW
```

**Node model** (`src/models/node.py`):
```python
class Node(BaseModel):
    # ... existing fields ...
    has_math: bool = Field(False, alias="hasMath")             # NEW
```

`content_type` in Node does not need a new value — math sections are still sections, tables, or figures. The `has_math` flag is sufficient for filtering/display.

### 3.4 Enrichment Step Integration

The existing enrichment step in `pipeline.py` (`_collect_nodes`) already:
1. Calls `classify_content_type(title, text)` to set `content_type`
2. Calls `detect_cross_references(text)` to set `cross_references`
3. Has `has_table` and `has_figure` flags on both Node and Page

Math classification follows the same pattern as `cross_ref_detector.py`:

**New file: `src/ingestion/enrichment/math_extractor.py`**
```python
"""Math formula extraction from page text."""

from __future__ import annotations
import re

# Patterns for LaTeX math delimiters
_INLINE_MATH = re.compile(r'\$(?!\$)(.+?)\$', re.DOTALL)
_DISPLAY_MATH = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
_ENV_MATH = re.compile(
    r'\\begin\{(equation|align|gather|multline|math)\*?\}(.+?)\\end\{\1\*?\}',
    re.DOTALL
)
_BRACKET_MATH = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)


def extract_math_expressions(text: str) -> list[str]:
    """Return list of LaTeX math strings found in text."""
    exprs: list[str] = []
    for match in _DISPLAY_MATH.finditer(text):
        exprs.append(f"$${match.group(1).strip()}$$")
    for match in _ENV_MATH.finditer(text):
        exprs.append(f"\\begin{{{match.group(1)}}}{match.group(2).strip()}\\end{{{match.group(1)}}}")
    for match in _BRACKET_MATH.finditer(text):
        exprs.append(f"\\[{match.group(1).strip()}\\]")
    for match in _INLINE_MATH.finditer(text):
        exprs.append(f"${match.group(1).strip()}$")
    return exprs


def has_math_content(text: str) -> bool:
    """Quick check: does this text contain math formulas?"""
    return bool(extract_math_expressions(text))
```

**Integration point in `pipeline.py: _collect_nodes()`**:
```python
# Existing:
content_type = classify_content_type(title, node_dict.get("text", ""))
cross_refs = detect_cross_references(node_dict.get("text", ""))

# New (add after existing enrichment):
from src.ingestion.enrichment.math_extractor import has_math_content
has_math = has_math_content(node_dict.get("text", ""))

node = Node(
    # ... existing fields ...
    has_math=has_math,   # NEW
)
```

**Integration point in `pipeline.py: save_pages()`**:
```python
from src.ingestion.enrichment.math_extractor import extract_math_expressions, has_math_content

# In the page-building loop, access math_expressions from ParsedPage:
page = Page(
    # ... existing fields ...
    has_math=has_math_content(text),           # NEW
    math_expressions=extract_math_expressions(text),  # NEW
)
```

### 3.5 page_list Tuple Extension

The current `page_list` type is `list[tuple[str, int]]` — `(text, token_count)`. This is passed through several layers. Two options:

**Option A (minimal change):** Keep page_list as `List[Tuple[str, int]]`. Extract math expressions separately in `save_pages()` by re-processing the text. No changes to any tree builder or meta_processor code.

**Option B (richer pipeline):** Change page_list to `List[ParsedPage]` objects throughout. More expressive but requires touching `meta_processor`, `tree_generator`, and many helpers that unpack tuples.

**Recommended: Option A.** Extract math from text at the persistence step only. This avoids breaking the tree builder which uses tuple unpacking extensively. The text in `pages.content` is identical to what was parsed, so re-running regex on it at save time has negligible cost.

---

## 4. Data Flow for LaTeX Content

```
PDF File
  │
  ▼
pdf_parser.parse_pdf()
  ├── pypdf/PyMuPDF extracts: text (may include LaTeX source strings)
  ├── ParsedPage.text = raw text with $...$ or \begin{equation}...
  └── page_list: List[Tuple[str, int]]
  │
  ▼
page_index_main()
  ├── tree_parser(): builds node structure from text (LaTeX treated as plain text)
  │     - ToC detector, LLM tree generator work on text unchanged
  │     - No change needed here; LaTeX in titles/summaries is fine for LLM reasoning
  └── generate_summaries_for_structure(): LLM summarizes nodes
        - LLM can read and describe math content in summaries
  │
  ▼
_collect_nodes()
  ├── classify_content_type() - unchanged
  ├── detect_cross_references() - unchanged
  ├── has_math_content(text) → has_math: bool    ← NEW
  └── Node saved with has_math field
  │
  ▼
save_pages()
  ├── pages.content = raw text (including LaTeX strings)
  ├── pages.has_math = has_math_content(text)    ← NEW
  └── pages.math_expressions = extract_math_expressions(text) ← NEW
  │
  ▼
MongoDB pages collection
  └── { content: "...$E=mc^2$...", hasMath: true,
        mathExpressions: ["$E=mc^2$"] }
  │
  ▼
Retrieval Pipeline (unchanged)
  ├── Atlas Search: BM25 on pages.content (LaTeX strings searchable as text)
  ├── Tree Navigation: LLM reads node summaries (already handles math in text)
  └── reasoner.check_sufficiency(): LLM answer includes LaTeX strings as-is
  │
  ▼
QueryResponse.answer: str
  └── May contain LaTeX: "The energy equation is $E=mc^2$..."
  │
  ▼
Frontend: MessageItem.tsx
  └── <ReactMarkdown> + rehype-katex + remark-math
        └── LaTeX rendered inline as typeset math
```

---

## 5. Frontend Rendering Integration

### 5.1 Current State

`frontend/components/chat/MessageItem.tsx` renders assistant responses:
```tsx
<div className="prose prose-sm max-w-none">
  <ReactMarkdown>{message.content}</ReactMarkdown>
</div>
```

`react-markdown@10.1.0` is already installed. `@tailwindcss/typography` provides prose styling.

### 5.2 What Needs to Change

Add two npm packages:
- `remark-math` — parses `$...$` and `$$...$$` in markdown as math nodes
- `rehype-katex` — renders math nodes to HTML using KaTeX
- `katex` — KaTeX runtime (peer dependency of rehype-katex)

No new components required. The change is entirely inside `MessageItem.tsx` — configure ReactMarkdown to use the math plugins.

**Updated `MessageItem.tsx` (assistant message block only)**:
```tsx
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

// Inside MessageItem render:
<div className="prose prose-sm max-w-none">
  <ReactMarkdown
    remarkPlugins={[remarkMath]}
    rehypePlugins={[rehypeKatex]}
  >
    {message.content}
  </ReactMarkdown>
</div>
```

KaTeX CSS must be imported once globally (or per-page). The cleanest placement is `frontend/app/layout.tsx` — a single import covers the whole app:
```tsx
// frontend/app/layout.tsx
import 'katex/dist/katex.min.css'
```

### 5.3 No API Changes Required

The retrieval pipeline already returns answers as plain strings. LaTeX strings embedded in the answer text (e.g. `"The formula is $E=mc^2$"`) will be passed through unchanged. The frontend plugin chain converts them to rendered math.

No new API endpoint or response field is needed for the rendering integration. The `math_expressions` field stored in MongoDB pages is available for future use (e.g., highlighting formula regions) but is not needed for basic chat rendering.

### 5.4 Tailwind Typography Compatibility

KaTeX injects its own CSS for `.katex` class elements. Tailwind's `prose` class may conflict with KaTeX's font-sizing. To prevent this, add a Tailwind escape in the component or configure prose to not apply styles inside `.katex`:

```tsx
// In MessageItem.tsx: wrap prose with not-prose exception for katex
<div className="prose prose-sm max-w-none [&_.katex]:not-prose">
```

Or configure `tailwind.config.ts` to exclude `.katex` from typography reset.

---

## 6. Component Boundaries

| Component | Boundary | Input | Output | New? |
|-----------|----------|-------|--------|------|
| `pdf_parser.parse_pdf()` | Extracts text from PDF pages | PDF bytes | `List[ParsedPage]` | Extended (add `math_expressions` to ParsedPage) |
| `math_extractor.extract_math_expressions()` | Detects LaTeX patterns in text | `str` | `List[str]` | **New file** |
| `math_extractor.has_math_content()` | Boolean math presence check | `str` | `bool` | **New file** |
| `pipeline._collect_nodes()` | Node persistence with math flag | node dict | `Node` doc | Extended (add `has_math`) |
| `pipeline.save_pages()` | Page persistence with math data | page text | `Page` doc | Extended (add `has_math`, `math_expressions`) |
| `Page` model | MongoDB page document | — | — | Extended (2 new fields) |
| `Node` model | MongoDB node document | — | — | Extended (1 new field) |
| `MessageItem.tsx` | Chat message renderer | `ChatMessage` | JSX | Extended (add math plugins) |
| `layout.tsx` | Global CSS imports | — | — | Extended (add katex CSS) |

The retrieval pipeline (`src/retrieval/`), Atlas Search index, LLM provider, session management, and all API routes other than `/ingest` remain unchanged.

---

## 7. Suggested Build Order

Dependencies flow strictly downward. Build bottom-up.

```
Phase 1 — Backend: Math Extraction Foundation
  Task 1.1: Create src/ingestion/enrichment/math_extractor.py
            - extract_math_expressions(text) -> List[str]
            - has_math_content(text) -> bool
            - Unit tests: regex patterns for inline, display, environment math
            Dependency: none (pure Python, no new packages)

  Task 1.2: Extend ParsedPage dataclass (src/ingestion/parsers/pdf_parser.py)
            - Add math_expressions: list[str] = field(default_factory=list)
            Dependency: Task 1.1 (math_extractor exists)

Phase 2 — Backend: Data Model Extension
  Task 2.1: Extend Page model (src/models/page.py)
            - Add has_math: bool, math_expressions: list[str]
            Dependency: none (model field additions are non-breaking)

  Task 2.2: Extend Node model (src/models/node.py)
            - Add has_math: bool
            Dependency: none

Phase 3 — Backend: Pipeline Integration
  Task 3.1: Update save_pages() in pipeline.py
            - Call has_math_content() and extract_math_expressions() on page text
            - Populate Page.has_math and Page.math_expressions
            Dependency: Task 1.1, Task 2.1

  Task 3.2: Update _collect_nodes() in pipeline.py
            - Call has_math_content() on node text
            - Populate Node.has_math
            Dependency: Task 1.1, Task 2.2

  Task 3.3: Add MongoDB index on pages.hasMath (optional, for filter queries)
            - Add to src/db/indexes.py: ensure_indexes()
            Dependency: Task 3.1

Phase 4 — Frontend: LaTeX Rendering
  Task 4.1: Install frontend packages
            - npm install remark-math rehype-katex katex
            Dependency: none (parallel with Phase 1-3)

  Task 4.2: Add KaTeX CSS import to frontend/app/layout.tsx
            Dependency: Task 4.1

  Task 4.3: Update MessageItem.tsx with remarkMath + rehypeKatex plugins
            Dependency: Task 4.1, Task 4.2

Phase 5 — Testing
  Task 5.1: Backend unit tests for math_extractor (regex correctness)
            Dependency: Task 1.1

  Task 5.2: Backend integration test: upload PDF with LaTeX → verify pages.mathExpressions
            Dependency: Tasks 3.1, 3.2

  Task 5.3: Frontend component test: MessageItem renders $E=mc^2$ as KaTeX HTML
            Dependency: Task 4.3
```

### Critical Path

```
1.1 → 3.1 → 5.2
1.1 → 3.2
2.1 → 3.1
2.2 → 3.2
4.1 → 4.2 → 4.3 → 5.3
```

Backend (Phase 1-3) and Frontend (Phase 4) are independent and can be built in parallel. Phase 5 testing requires both to be complete.

---

## 8. Dependency Assessment

### New Python Dependencies

None required for regex-based extraction. If PyMuPDF structural extraction is used (optional Strategy B), PyMuPDF 1.24+ is already in `pyproject.toml`.

Optional future: `sympy` or `latex2sympy2` for semantic math understanding (not needed for storage/rendering).

### New npm Packages

```json
{
  "remark-math": "^6.0.0",
  "rehype-katex": "^7.0.0",
  "katex": "^0.16.0"
}
```

All three are well-maintained, ESM-compatible, and work with Next.js 15 App Router. `react-markdown` already supports plugin injection via `remarkPlugins`/`rehypePlugins` props.

### No Changes Required

- MongoDB schema: MongoDB is schemaless; adding fields to documents is non-breaking. Existing documents without `hasMath` will have the field absent (treated as falsy).
- Atlas Search index: LaTeX text is already indexed as plain text. No reindex needed.
- Retrieval pipeline: No changes. LLM already handles math text in reasoning prompts.
- API response models: No new fields in `QueryResponse`. Answer is already a `str`.
- Session management: No changes.

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| pypdf strips LaTeX delimiters from text | Medium | Use PyMuPDF backend for math-heavy PDFs; add a backend fallback config |
| KaTeX fails to render malformed LaTeX | Low | KaTeX renders what it can and shows raw fallback for errors; no crash |
| Tailwind prose conflicts with KaTeX font sizes | Low | Use `[&_.katex]:not-prose` CSS escape in MessageItem wrapper div |
| `math_expressions` array grows very large for equation-dense pages | Low | Cap at N expressions (e.g., 50) per page in extract_math_expressions() |
| PyMuPDF structural extraction too slow for large documents | Low | Keep as optional backend; default to regex |

---

## 10. Quality Gate Verification

- [x] **Components clearly defined with boundaries**: Section 6 provides a boundary table with input/output for each component
- [x] **Data flow direction explicit**: Section 4 shows the complete data flow from PDF bytes to rendered frontend output with arrow notation
- [x] **Build order implications noted**: Section 7 provides explicit phase ordering with dependency statements per task, plus a critical path diagram

---

*Research produced for: downstream phase structure in roadmap*
*Analysis based on codebase at: `/home/moamath/work/Agentic-Search-Vectorless`*
*Key files inspected: `src/ingestion/pipeline.py`, `src/ingestion/parsers/pdf_parser.py`, `src/models/page.py`, `src/models/node.py`, `src/ingestion/enrichment/content_classifier.py`, `src/ingestion/enrichment/math_extractor.py` (proposed), `frontend/components/chat/MessageItem.tsx`, `frontend/package.json`, `pyproject.toml`*
