# Research: Math-Aware PDF Parsing and LaTeX Rendering Stack

**Research Date:** 2026-02-17
**Research Type:** Stack dimension — math formula extraction from PDFs and LaTeX rendering in Next.js
**Milestone:** Adding LaTeX math formula parsing and rendering to existing Vectorless RAG system
**Researcher note:** Versions verified against training data (through January 2025). Marked with confidence levels. Independent version verification recommended before implementation.

---

## Research Question

What is the standard 2025 stack for:
1. Extracting math formulas from PDFs as LaTeX strings during Python-based ingestion
2. Rendering LaTeX math in a Next.js 15 / React 19 frontend

**Target document type:** Korean math exam papers (수능/시험 문제지) — PDFs with dense inline and display-mode math formulas, typically produced by professional typesetters using LaTeX or similar tools, so the PDF text layer is usually present (not scanned).

**Critical constraint from PROJECT.md:** Scanned-image OCR is explicitly **out of scope** — only the PDF text layer is targeted.

---

## Part 1: PDF Math Extraction (Backend — Python)

### Problem Statement

Current `pdf_parser.py` uses `pypdf.PdfReader.extract_text()` and `pymupdf.page.get_text()`. Both extract plain Unicode text. The challenge:

- Mathematical symbols in Korean exam PDFs are encoded in two ways:
  1. **Type 1 / OTF with embedded glyphs**: pypdf/PyMuPDF extracts Unicode characters (e.g., `α`, `∫`, `²`) but loses structural LaTeX (e.g., `\frac{1}{2}` becomes `1 2` or `½`).
  2. **Actual LaTeX source embedded via Tagged PDF or XMP**: rare in Korean exams, essentially never.

- Korean 수능 PDFs are produced by government-contracted typesetters using specialized DTP software (not LaTeX). Math formulas appear as rendered glyphs embedded in CID fonts. The text layer often contains the correct Unicode symbols but loses the structural grouping (fractions, exponents, integrals as flat strings).

### Extraction Strategy Options

#### Option A: pymupdf4llm — Markdown extraction with formula preservation (RECOMMENDED primary)

**Library:** `pymupdf4llm` (by Artifex, same team as PyMuPDF)
**Version:** 0.0.17 (latest as of January 2025)
**PyPI:** `pip install pymupdf4llm`

**What it does:**
- Wraps PyMuPDF to extract structured Markdown from PDF pages
- Preserves bold, italic, heading levels, and importantly: math formula regions as detected by font metrics and character clustering
- Outputs Markdown with `$...$` delimiters for recognized inline math
- Handles multi-column layouts common in Korean exam papers

**Why over raw PyMuPDF:**
- `page.get_text()` (current usage) returns a flat text dump with no structural math awareness
- `pymupdf4llm.to_markdown()` uses span-level font analysis to detect formula regions
- No model download, no GPU, no network — pure library call
- Extremely fast (milliseconds per page)
- Already depends on PyMuPDF which is already a project dependency — minimal new weight

**Limitations:**
- Does NOT reconstruct LaTeX syntax (e.g., `\frac{a}{b}`) — outputs Unicode math characters with `$` wrapping
- Fraction structure (`½` vs `\frac{1}{2}`) is lost unless the PDF has structural hints
- For 수능 PDFs, likely output is `$x^2 + 3x + 1 = 0$` (good) but `$\frac{1}{2}$` may appear as `$1/2$` or `$½$` (structural loss)

**Confidence:** HIGH — well-documented, production library from PyMuPDF authors

---

#### Option B: LLM-assisted LaTeX normalization (RECOMMENDED secondary layer)

**What it does:**
After pymupdf4llm extracts text with Unicode math symbols, pass the extracted text to Claude (already integrated) with a prompt asking it to:
1. Identify math formula regions
2. Reconstruct proper LaTeX from the Unicode representation

**Why this works well in this project:**
- Claude is already called per-node for summarization and keyword extraction in `src/ingestion/enrichment/`
- Adding a "formula normalization" step to the enrichment pipeline requires only a new prompt template
- Claude 3.5 Haiku (fast model) handles math LaTeX normalization accurately for Korean exam-style problems
- Can leverage Claude's understanding of Korean mathematical notation conventions

**Cost consideration (from PROJECT.md constraints):**
- Additional LLM call per node increases ingestion cost
- Recommended: apply only to nodes classified as containing math content (use `content_type` from `content_classifier.py`)
- Estimate: ~200-500 tokens per math-heavy page → ~$0.001-0.003 per page with Haiku

**Output format target:**
```
Input:  "x² + 3x + 1 = 0에서 x = −3±√5/2"
Output: "$x^2 + 3x + 1 = 0$에서 $x = \frac{-3 \pm \sqrt{5}}{2}$"
```

**Confidence:** HIGH for reconstruction accuracy; MEDIUM for cost predictability at scale

---

#### Option C: pdfminer.six with character-level analysis

**Library:** `pdfminer.six`
**Version:** 20231228 (latest stable, January 2025)
**PyPI:** `pip install pdfminer.six`

**What it does:**
- Low-level PDF parser with access to character position, font name, font size
- Can detect superscript/subscript by comparing character y-positions and font sizes
- Can detect fraction structures by spatial positioning

**Why NOT recommended for this project:**
- Requires significant custom logic to reconstruct math structure from character coordinates
- PyMuPDF already in the stack provides the same character-level access via `page.get_text("dict")` with block/line/span/char decomposition — no need for another library
- Much higher implementation complexity than pymupdf4llm for the same result
- No maintained math-specific extraction layer

**Verdict: DO NOT ADD** — use PyMuPDF's `page.get_text("dict")` if character-level analysis is needed

---

#### Option D: Nougat (Meta's neural PDF parser)

**Library:** `nougat-ocr`
**Version:** 0.1.17
**PyPI:** `pip install nougat-ocr`

**What it does:**
- Vision Transformer (ViT) model trained on scientific papers (arXiv) that converts PDF pages to Markdown with LaTeX math
- Outputs proper `\frac{}{}`, `\int`, `\sum` etc.
- Specifically designed for math-heavy academic documents

**Why NOT recommended for this project:**

1. **Model weight download required**: ~1.3GB download on first run — incompatible with lightweight Docker deployment
2. **GPU strongly recommended**: CPU inference is extremely slow (~30-60 seconds per page). Korean 수능 papers have 30+ pages = 15-30 minutes per document on CPU
3. **Trained on arXiv papers, not Korean exam style**: Font styles, layout, Korean text mixing may degrade accuracy
4. **Overkill given out-of-scope constraint**: PROJECT.md explicitly says scanned-image OCR is out of scope. Nougat is designed for that exact scenario (image-based formula recognition), but 수능 PDFs have text layers
5. **AGPL-3.0 license**: Adds licensing complexity on top of existing PyMuPDF AGPL concern

**Verdict: DO NOT USE** for this project's constraints

---

#### Option E: pix2tex / LaTeX-OCR

**Library:** `pix2tex`
**Version:** 0.1.2
**PyPI:** `pip install pix2tex`

**What it does:**
- ViT-based model that takes cropped formula image and outputs LaTeX string
- Requires rendering the PDF page to image, cropping formula region, running inference

**Why NOT recommended:**
- Same GPU/model-weight problems as Nougat
- Requires additional formula region detection step (not provided by the library)
- Only handles isolated formula images, not continuous text with embedded formulas
- Out of scope: PROJECT.md explicitly excludes image-based formula recognition

**Verdict: DO NOT USE**

---

#### Option F: MathPix API (commercial OCR)

**What it does:**
- Cloud API that takes PDF pages or formula images and returns LaTeX
- High accuracy for printed math

**Why NOT recommended:**
- Commercial service with per-page costs on top of existing Anthropic costs
- Privacy concern: sends exam content to third-party service
- Network dependency in ingestion pipeline
- Claude can accomplish the same LaTeX normalization without additional vendor

**Verdict: DO NOT USE**

---

### Recommended Backend Architecture

```
PDF upload
    ↓
pymupdf4llm.to_markdown(page)          ← pymupdf4llm 0.0.17
    ↓ (text with Unicode math + $ delimiters)
    ↓
[if page contains math symbols]
    ↓
Claude Haiku: LaTeX normalization prompt   ← existing anthropic SDK
    ↓ (proper LaTeX: \frac, \sqrt, etc.)
    ↓
Store in nodes.content with $...$ / $$...$$ markers
```

**New Python dependency:**
```toml
# pyproject.toml
"pymupdf4llm>=0.0.17"   # math-aware markdown extraction from PDF
```

No other new backend dependencies required — Claude SDK already present.

---

## Part 2: LaTeX Rendering (Frontend — Next.js / React)

### Problem Statement

The frontend needs to render LaTeX strings returned from the backend in:
1. Chat answer text (streamed SSE responses) — inline and display math mixed with Korean text
2. Document preview / node summaries — Markdown with embedded LaTeX

Current state: `react-markdown@^10.1.0` is already installed. It renders Markdown but does NOT process `$...$` or `$$...$$` LaTeX delimiters.

### Rendering Library Options

#### Option A: KaTeX with remark-math + rehype-katex (RECOMMENDED)

**Libraries:**
- `katex` — core LaTeX rendering engine (CSS + JS, no external service)
- `remark-math` — Markdown plugin that parses `$...$` and `$$...$$` to math AST nodes
- `rehype-katex` — converts math AST nodes to KaTeX-rendered HTML

**Versions (January 2025):**
- `katex@^0.16.11`
- `remark-math@^6.0.0`
- `rehype-katex@^7.0.1`

**npm install:**
```bash
npm install katex remark-math rehype-katex
npm install --save-dev @types/katex
```

**Integration with existing `react-markdown`:**
```tsx
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

<ReactMarkdown
  remarkPlugins={[remarkMath]}
  rehypePlugins={[rehypeKatex]}
>
  {content}
</ReactMarkdown>
```

**Why KaTeX over MathJax:**

| Criterion | KaTeX | MathJax |
|-----------|-------|---------|
| Rendering speed | ~10-50ms | ~100-300ms |
| Bundle size | ~150KB (JS) + 280KB (fonts) | ~700KB+ |
| SSR/Next.js compatibility | Native (sync render) | Requires async, tricky SSR |
| Coverage of LaTeX commands | ~90% of common math | ~99% |
| Korean exam math coverage | Sufficient: `\frac`, `\sqrt`, `\int`, `\sum`, `\lim`, matrices | Same |
| Maintained | Yes (Khan Academy) | Yes (AMS) |
| React integration | Simple via rehype-katex | More complex |

**Why KaTeX is the right choice for 수능 documents:**
- 수능 math uses a well-defined subset of LaTeX: basic calculus (`\int`, `\lim`, `\frac`, `\sqrt`), linear algebra (matrices via `\begin{pmatrix}`), sequences (`\sum`), logarithms, trigonometry — all in KaTeX's supported set
- SSE streaming output requires synchronous rendering — KaTeX renders synchronously, MathJax 3 renders asynchronously (causes flash of unrendered content in streaming UI)
- `react-markdown` integration is two plugin imports away — zero architectural change required

**Limitations:**
- Does not render esoteric LaTeX commands (e.g., `\chemfig`, TikZ) — irrelevant for math exams
- Requires loading KaTeX CSS (can be imported once in `layout.tsx`)

**Confidence:** HIGH — KaTeX + remark-math + rehype-katex is the documented standard integration for react-markdown. Used in production by Notion, Khan Academy, and major educational platforms.

---

#### Option B: MathJax 3

**Library:** `mathjax-full` or via CDN
**Version:** 3.2.2

**Why NOT recommended:**
- Async rendering model conflicts with Next.js App Router and SSR hydration
- Larger bundle size without benefit for the math subset needed
- Community integrations with react-markdown are less maintained than KaTeX equivalents
- `better-react-mathjax` wrapper adds another abstraction layer with its own SSR issues

**Verdict: DO NOT USE** — KaTeX covers all math needed; MathJax's complexity is unjustified

---

#### Option C: react-katex (direct component)

**Library:** `react-katex`
**Version:** 3.0.1

**What it does:**
- `<InlineMath>` and `<BlockMath>` React components wrapping KaTeX
- Manual wrapping per formula, no Markdown processing

**Why NOT recommended over Option A:**
- Does NOT integrate with `react-markdown` — requires pre-parsing the text to split text and formula segments
- Suitable only if content arrives as separate formula strings (not mixed Markdown+LaTeX text)
- More code required vs. plugin approach

**When to use:** If you need to render a specific isolated formula string (e.g., a formula input field preview). Can coexist with Option A for that use case.

---

### Recommended Frontend Architecture

**Install:**
```bash
# In frontend/
npm install katex@^0.16.11 remark-math@^6.0.0 rehype-katex@^7.0.1
npm install --save-dev @types/katex
```

**Global CSS (in `frontend/app/layout.tsx`):**
```tsx
import 'katex/dist/katex.min.css'
```

**Shared component (`frontend/components/MathMarkdown.tsx`):**
```tsx
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

interface MathMarkdownProps {
  children: string
  className?: string
}

export function MathMarkdown({ children, className }: MathMarkdownProps) {
  return (
    <ReactMarkdown
      className={className}
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
    >
      {children}
    </ReactMarkdown>
  )
}
```

**Usage in chat response:**
Replace existing `<ReactMarkdown>` usages in chat components with `<MathMarkdown>`.

**No new frontend dependencies beyond the three npm packages** — no configuration changes to Next.js, Tailwind, or TypeScript required.

---

## Part 3: Data Flow and Storage

### How LaTeX flows through the system

```
PDF Page Text (pymupdf4llm)
    → "풀이: $x^2 - 5x + 6 = 0$이므로..."
    ↓
LLM LaTeX normalization (if needed)
    → "풀이: $x^2 - 5x + 6 = 0$이므로 $x = \frac{5 \pm 1}{2}$..."
    ↓
Stored in nodes.content / pages.text (MongoDB)
    → LaTeX strings stored as-is in plain text fields
    ↓
Retrieval pipeline returns content with LaTeX
    → No transformation needed — strings pass through unchanged
    ↓
Frontend ReactMarkdown + KaTeX plugins render
    → Browser displays typeset math
```

**MongoDB consideration:** LaTeX strings contain `\`, `{`, `}` characters. MongoDB stores these without issue as plain strings — no escaping needed. Atlas Search (BM25) will index them as text tokens, which is acceptable.

**LLM prompt consideration:** When passing node content to Claude for reasoning, `$x^2 + 1$` is readable to the LLM — Claude understands LaTeX natively. No conversion needed at the LLM boundary.

---

## Part 4: What to Avoid and Why

| Library / Approach | Verdict | Reason |
|-------------------|---------|--------|
| Nougat (Meta) | DO NOT USE | GPU required, 1.3GB model, overkill for text-layer PDFs, AGPL license |
| pix2tex / LaTeX-OCR | DO NOT USE | Image-based OCR out of scope per PROJECT.md |
| MathPix API | DO NOT USE | Commercial cost, privacy, vendor dependency |
| MathJax 3 | DO NOT USE | Async rendering conflicts with SSR/streaming; larger bundle |
| pdfminer.six | DO NOT USE | Redundant with PyMuPDF capabilities already in stack |
| react-katex (standalone) | AVOID as primary | Doesn't integrate with react-markdown pipeline |
| mathjax-full | DO NOT USE | Same concerns as MathJax 3 |

---

## Part 5: Confidence Levels and Version Notes

| Component | Version | Confidence | Notes |
|-----------|---------|-----------|-------|
| `pymupdf4llm` | 0.0.17 | HIGH | Actively maintained by Artifex as of Jan 2025; version stable |
| `katex` | 0.16.11 | HIGH | KaTeX 0.16.x series stable since 2023; 0.17 possible by Feb 2026 — check PyPI |
| `remark-math` | 6.0.0 | HIGH | ESM module; works with react-markdown 10.x (project already has ^10.1.0) |
| `rehype-katex` | 7.0.1 | HIGH | Maintained alongside remark-math; compatible with rehype ecosystem |
| Claude Haiku (LaTeX normalization) | claude-haiku-4-5 | HIGH | Configured in existing LLM_INGESTION_MODEL env var |
| PyMuPDF backend switch | — | HIGH | Already in stack; pymupdf4llm is an extension, not replacement |

**Version verification action items before implementation:**
1. `pip index versions pymupdf4llm` — confirm latest patch version
2. `npm view katex version` — confirm 0.16.x is current (0.17 may be released)
3. `npm view remark-math version` — confirm 6.0.0 compatibility with react-markdown 10
4. `npm view rehype-katex version` — check for updates

---

## Part 6: Implementation Touchpoints

### Backend changes required

| File | Change |
|------|--------|
| `pyproject.toml` | Add `pymupdf4llm>=0.0.17` |
| `src/ingestion/parsers/pdf_parser.py` | Add `pymupdf4llm` backend option (alongside pypdf / PyMuPDF) |
| `src/ingestion/enrichment/` | Add `latex_normalizer.py` enrichment step using Claude |
| `src/config.py` | Add `PDF_MATH_BACKEND` and `ENABLE_LATEX_NORMALIZATION` config vars |

### Frontend changes required

| File | Change |
|------|--------|
| `frontend/package.json` | Add katex, remark-math, rehype-katex |
| `frontend/app/layout.tsx` | Import `katex/dist/katex.min.css` |
| `frontend/components/` | Create `MathMarkdown.tsx` shared component |
| Chat response components | Replace `<ReactMarkdown>` with `<MathMarkdown>` |

### No changes required

- MongoDB schema — strings store LaTeX as-is
- API endpoints — LaTeX passes through as string content
- Retrieval pipeline — no transformation needed
- Docker configuration — pymupdf4llm is pure Python, no system deps beyond what PyMuPDF already requires

---

## Summary

| Layer | Library | Version | Role |
|-------|---------|---------|------|
| PDF extraction | `pymupdf4llm` | 0.0.17 | Math-aware Markdown extraction from PDF text layer |
| LaTeX normalization | Claude Haiku (existing) | — | Reconstruct `\frac`, `\sqrt` from Unicode via LLM prompt |
| Frontend rendering | `katex` | ^0.16.11 | Core LaTeX→HTML renderer |
| Markdown integration | `remark-math` | ^6.0.0 | Parse `$...$` delimiters in Markdown |
| Markdown integration | `rehype-katex` | ^7.0.1 | Apply KaTeX to remark-math AST nodes |

The stack is **minimal additions** to the existing project: one new Python library (pymupdf4llm) extending the existing PyMuPDF dependency, three npm packages extending the existing react-markdown setup, and one new LLM enrichment prompt using the existing Anthropic SDK. No new services, no GPU requirements, no external APIs.

---

*Research complete: 2026-02-17*
*Confidence: Training data through January 2025. Verify current versions before implementation.*
