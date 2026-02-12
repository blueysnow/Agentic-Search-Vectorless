# Vectorless RAG System: PageIndex + MongoDB + Atlas Search

**Date:** February 12, 2026
**Status:** ACTIVE -- Phase 1 Complete, Phases 2-5 Remaining
**Language:** Python 3.12+
**Architecture:** PageIndex Hierarchical Trees + MongoDB + Atlas Search (Lucene) + LLM Reasoning

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Reference Code Map](#2-reference-code-map)
3. [Research Index](#3-research-index)
4. [MongoDB Schema Design](#4-mongodb-schema-design)
5. [Atlas Search (Lucene) Index Design](#5-atlas-search-lucene-index-design)
6. [Document Ingestion Pipeline](#6-document-ingestion-pipeline)
7. [Retrieval Pipeline](#7-retrieval-pipeline)
8. [Dual Retrieval Strategy](#8-dual-retrieval-strategy)
9. [LLM Prompts (Stolen from Reference)](#9-llm-prompts-stolen-from-reference)
10. [Technology Stack](#10-technology-stack)
11. [Build Phases](#11-build-phases)
12. [Testing Strategy](#12-testing-strategy)
13. [Production Readiness](#13-production-readiness)
14. [Improvements Over Original PageIndex](#14-improvements-over-original-pageindex)

---

## 1. System Architecture Overview

### 1.1 Core Philosophy

The system replaces vector embeddings with **three complementary retrieval mechanisms**:

1. **Hierarchical Tree Navigation (LLM-driven)** -- The LLM reads the document's table-of-contents tree and reasons about which sections contain the answer, navigating deeper recursively. This is PageIndex's core innovation.
2. **Atlas Search (Lucene full-text)** -- BM25 keyword search across node titles, summaries, and content for fast, deterministic candidate retrieval.
3. **LLM Reasoning Orchestrator** -- An agentic loop that combines signals from both retrieval paths, decides whether to drill deeper, follow cross-references, or generate the final answer.

No vector embeddings. No vector database. No cosine similarity. Just structure, keywords, and reasoning.

### 1.2 Data Flow

```
INGESTION FLOW (maps to reference page_index.py:1058-1100)
================================================================

Document (PDF/MD)
  |
  v
[Parser Layer]          Extract text per page, count tokens
  |                     ref: utils.py:413-437 get_page_tokens()
  v
[ToC Detection]         Scan first N pages for Table of Contents
  |                     ref: page_index.py:688-724 check_toc()
  |                     3 modes detected: A) ToC+pages, B) ToC only, C) No ToC
  v
[Tree Building]         LLM generates hierarchical structure
  |                     Mode A: page_index.py:614-643 process_toc_with_page_numbers()
  |                     Mode B: page_index.py:589-610 process_toc_no_page_numbers()
  |                     Mode C: page_index.py:568-587 process_no_toc()
  v
[Verification]          LLM verifies section titles on expected pages
  |                     ref: page_index.py:892-944 verify_toc()
  |                     Fix incorrect mappings: page_index.py:731-866 fix_incorrect_toc()
  v
[Large Node Split]      Recursively subdivide oversized nodes
  |                     ref: page_index.py:992-1019 process_large_node_recursively()
  v
[Enrichment]            Generate summaries, extract keywords, detect cross-refs
  |                     ref: utils.py:605-623 generate_summaries_for_structure()
  v
[MongoDB Persist]       Write to documents, nodes, pages collections
  |
  v
[Atlas Search Index]    Auto-indexes title, summary, content, keywords


RETRIEVAL FLOW
================================================================

User Query
  |
  +-------> [Atlas Search]  --> Top-N keyword-matched nodes (BM25)
  |              |
  +-------> [Tree Navigator] --> LLM reads root ToC, selects branches
  |              |               ref: tutorials/tree-search/README.md
  v              v
  [Merge & Rank]  --> Combine keyword + tree results
       |            (atlas_score * 0.3) + (tree_score * 0.7)
       v
  [Content Loader] --> Fetch pages for selected nodes
       |
       v
  [LLM Reasoner]  --> Sufficient? YES->answer, NO->navigate deeper
       |
       v
  [Answer + Trace] --> Final answer + reasoning path logged
```

### 1.3 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | MongoDB Atlas | JSON documents natively match hierarchical trees |
| Full-text search | Atlas Search (Lucene) | Built-in, free, BM25 scoring, fuzzy matching |
| Vector search | **NONE** | Vectorless philosophy -- reasoning replaces similarity |
| Tree pattern | Hybrid (parent refs + materialized paths + child refs) | All traversal patterns supported |
| LLM provider | Configurable (Claude/GPT) | Provider-agnostic abstraction layer |
| Language | **Python 3.12+** | Direct PageIndex reference reuse, native tiktoken, AI ecosystem |
| API framework | FastAPI | Async, type-safe with Pydantic, OpenAPI docs |
| Ingestion model | Can differ from retrieval model | Use cheaper model for indexing |

---

## 2. Reference Code Map

### 2.1 PageIndex Repository

**Location:** `reference/PageIndex/` (cloned Feb 12, 2026)
**Stars:** 14,816 | **Accuracy:** 98.7% on FinanceBench

```
reference/PageIndex/
  pageindex/
    page_index.py    (1,143 lines) -- Core tree builder [THE GOLD STANDARD]
    utils.py         (711 lines)   -- LLM calls, PDF utils, tree utilities
    page_index_md.py (338 lines)   -- Markdown variant
    config.yaml      (8 lines)     -- Default config
  run_pageindex.py   (132 lines)   -- CLI entry point
  tutorials/
    tree-search/     -- Tree search prompt patterns
    doc-search/      -- Multi-document search strategies
```

### 2.2 Core Functions Map (page_index.py)

Every function we need to port, with exact line numbers:

#### ToC Detection (Lines 13-235)
| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `check_title_appearance()` | 13-45 | LLM checks if section title appears on page | `ingestion/tree_builder/verifier.py` |
| `check_title_appearance_in_start()` | 48-71 | Checks if section starts at page beginning | `ingestion/tree_builder/verifier.py` |
| `toc_detector_single_page()` | 104-122 | LLM detects ToC on single page | `ingestion/tree_builder/toc_detector.py` |
| `extract_toc_content()` | 160-197 | Extracts ToC text with continuation | `ingestion/tree_builder/toc_detector.py` |
| `detect_page_index()` | 199-217 | Checks if page numbers exist in ToC | `ingestion/tree_builder/toc_detector.py` |
| `toc_extractor()` | 219-235 | Extract ToC + check for page numbers | `ingestion/tree_builder/toc_detector.py` |

#### ToC Transformation (Lines 240-358)
| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `toc_index_extractor()` | 240-266 | Map ToC entries to physical page indices | `ingestion/tree_builder/page_mapper.py` |
| `toc_transformer()` | 270-328 | Convert ToC to JSON with continuation | `ingestion/tree_builder/toc_transformer.py` |
| `find_toc_pages()` | 333-358 | Scan pages to find ToC location | `ingestion/tree_builder/toc_detector.py` |

#### Tree Generation (Lines 418-643)
| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `page_list_to_group_text()` | 418-451 | Split pages into token-limited groups | `ingestion/tree_builder/tree_generator.py` |
| `add_page_number_to_toc()` | 453-483 | LLM maps sections to physical pages | `ingestion/tree_builder/page_mapper.py` |
| `generate_toc_continue()` | 499-531 | Continue tree from previous chunk | `ingestion/tree_builder/tree_generator.py` |
| `generate_toc_init()` | 534-566 | Generate initial tree from text | `ingestion/tree_builder/tree_generator.py` |
| `process_no_toc()` | 568-587 | Mode C: no ToC, LLM generates tree | `ingestion/tree_builder/tree_generator.py` |
| `process_toc_no_page_numbers()` | 589-610 | Mode B: ToC without page numbers | `ingestion/tree_builder/tree_generator.py` |
| `process_toc_with_page_numbers()` | 614-643 | Mode A: ToC with page numbers | `ingestion/tree_builder/tree_generator.py` |

#### Verification & Fix (Lines 688-944)
| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `check_toc()` | 688-724 | Main ToC detection entry | `ingestion/tree_builder/toc_detector.py` |
| `fix_incorrect_toc()` | 731-866 | Fix wrong ToC entries (retry loop) | `ingestion/tree_builder/verifier.py` |
| `verify_toc()` | 892-944 | Verify ToC accuracy with sampling | `ingestion/tree_builder/verifier.py` |

#### Orchestration (Lines 950-1111)
| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `meta_processor()` | 950-989 | Main tree orchestrator (3 modes + fallback) | `ingestion/pipeline.py` |
| `process_large_node_recursively()` | 992-1019 | Split oversized nodes | `ingestion/tree_builder/splitter.py` |
| `tree_parser()` | 1021-1055 | Full tree parsing pipeline | `ingestion/pipeline.py` |
| `page_index_main()` | 1058-1100 | Main entry (parse -> build -> enrich) | `ingestion/pipeline.py` |

### 2.3 Utility Functions Map (utils.py)

| Function | Lines | Purpose | Our Module |
|----------|-------|---------|------------|
| `count_tokens()` | 22-27 | tiktoken encoding | `utils/tokens.py` [DONE] |
| `ChatGPT_API()` | 61-86 | LLM call with retry | `llm/provider.py` [DONE] |
| `ChatGPT_API_async()` | 89-108 | Async LLM call | `llm/provider.py` [DONE] |
| `extract_json()` | 125-156 | JSON extraction from LLM response | `utils/json_utils.py` [DONE] |
| `write_node_id()` | 158-168 | Assign node IDs to tree | `ingestion/tree_builder/tree_utils.py` |
| `get_nodes()` | 170-183 | Flatten tree to node list | `ingestion/tree_builder/tree_utils.py` |
| `structure_to_list()` | 185-196 | Tree to flat list | `ingestion/tree_builder/tree_utils.py` |
| `get_leaf_nodes()` | 199-215 | Get leaf nodes | `ingestion/tree_builder/tree_utils.py` |
| `is_leaf_node()` | 217-241 | Check if node is leaf | `ingestion/tree_builder/tree_utils.py` |
| `get_page_tokens()` | 413-437 | Parse PDF to (text, tokens) list | `ingestion/parsers/pdf_parser.py` [DONE] |
| `get_text_of_pages()` | 262-272 | Get text with page tags | `ingestion/parsers/pdf_parser.py` [DONE] |
| `get_text_of_pdf_pages_with_labels()` | 447-451 | Pages with physical_index tags | `ingestion/parsers/pdf_parser.py` |
| `post_processing()` | 460-479 | Convert flat structure to tree | `ingestion/tree_builder/tree_utils.py` |
| `list_to_tree()` | 350-396 | Flat list to nested tree | `ingestion/tree_builder/tree_utils.py` |
| `add_preface_if_needed()` | 398-409 | Add preface node if doc starts after page 1 | `ingestion/tree_builder/tree_utils.py` |
| `add_node_text()` | 579-589 | Attach page text to nodes | `ingestion/tree_builder/tree_utils.py` |
| `generate_node_summary()` | 605-613 | LLM summary for one node | `ingestion/enrichment/summarizer.py` |
| `generate_summaries_for_structure()` | 616-623 | Parallel summaries for tree | `ingestion/enrichment/summarizer.py` |
| `generate_doc_description()` | 649-658 | LLM doc description | `ingestion/enrichment/summarizer.py` |
| `ConfigLoader` | 681-712 | YAML config loading | `config.py` [DONE] |

### 2.4 Default Config (config.yaml)

```yaml
model: gpt-4o-2024-11-20
toc_check_page_num: 20       # Pages to scan for ToC
max_page_num_each_node: 10   # Max pages per tree node
max_token_num_each_node: 20000  # Max tokens per tree node
```

---

## 3. Research Index

### 3.1 Research Files

All research stored in `docs/research/`:

| File | Lines | Purpose |
|------|-------|---------|
| `RESEARCH_COMPLETE_SUMMARY.md` | 314 | Executive summary of all findings |
| `SOTA_VECTORLESS_RAG_REPORT.md` | 497 | 50+ projects analyzed, SOTA landscape |
| `PAGEINDEX_RESEARCH.md` | 655 | PageIndex deep dive + MongoDB schemas |
| `MONGODB_ATLAS_SEARCH_LUCENE_FOR_PAGEINDEX.md` | 856 | Complete Atlas Search guide for PageIndex |
| `README_RESEARCH.md` | 232 | Navigation guide |
| `INDEX.md` | 301 | Original research index |
| `INDEX_CORRECTED.md` | 226 | Corrected index (no vector noise) |
| **Total** | **3,081** | **Complete research base** |

### 3.2 Key Research Findings

- **PageIndex** (14,816 stars) -- 98.7% accuracy on FinanceBench, vectorless
- **Atlas Search** is Lucene-based, built-in to MongoDB, FREE, `dynamic: false` for production
- **NO Vector Search** -- contradicts vectorless philosophy, separate cost
- **DeepRead** (Feb 2026) -- emerging SOTA, "locate then read" pattern
- **Dual retrieval** -- Atlas Search for keyword candidates, tree nav for reasoning
- **MongoDB** as foundation -- JSON documents = tree nodes natively

### 3.3 MongoDB Skills Applied

Three MongoDB skill sets loaded and applied to this plan:

1. **Schema Design** (30 rules) -- embed vs reference, anti-patterns, tree structures
2. **Query & Index Optimization** (46 rules) -- ESR rule, compound indexes, aggregation
3. **AI Integration** (33 rules) -- Atlas Search, Lucene, NOT vector search

---

## 4. MongoDB Schema Design

### 4.1 Collection Architecture

Five collections, each with a clear responsibility:

```
Collections:
  documents          -- Document-level metadata and config
  nodes              -- Hierarchical tree nodes (the core index)
  pages              -- Raw page/section content (separate for perf)
  retrieval_sessions -- Multi-turn conversation tracking
  analytics          -- Ingestion/retrieval metrics
```

**MongoDB Schema Design Rules Applied:**
- `fundamental-data-together`: Node tree data kept together, page content separate (different access pattern)
- `relationship-tree-structures`: Hybrid pattern (parent ref + materialized path + child refs)
- `antipattern-unbounded-arrays`: crossReferences bounded by document structure, turns bounded per session
- `fundamental-embed-vs-reference`: Pages referenced by nodeId, not embedded (can be 100+ pages per node)

### 4.2 Collection: `documents`

```python
# src/models/document.py [DONE - Phase 1]
class IngestionConfig(BaseModel):
    max_pages_per_node: int = 10
    max_tokens_per_node: int = 20000
    toc_check_pages: int = 20
    add_node_summaries: bool = True

class IngestionInfo(BaseModel):
    status: str = "pending"  # pending | processing | completed | failed
    model: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    config: IngestionConfig = IngestionConfig()
    errors: list[str] = []

class Document(BaseModel):
    document_id: str          # Application-level unique ID
    name: str
    type: str                 # pdf | markdown
    domain: str | None = None
    description: str | None = None
    total_pages: int = 0
    total_nodes: int = 0
    total_tokens: int = 0
    root_node_id: str | None = None
    ingestion: IngestionInfo = IngestionInfo()
    created_at: datetime
    updated_at: datetime
```

### 4.3 Collection: `nodes`

The heart of the system. Each node = a section of the document tree.

```python
# src/models/node.py [DONE - Phase 1]
class Node(BaseModel):
    node_id: str              # PageIndex-style "0001", "0002"
    document_id: str

    # Hierarchy (hybrid tree pattern)
    parent_node_id: str | None = None
    materialized_path: str    # "/0001/0003/0006"
    child_node_ids: list[str] = []
    depth: int = 0
    sibling_order: int = 0

    # Content
    title: str
    summary: str | None = None

    # Page range
    start_page: int
    end_page: int
    token_count: int = 0

    # Search enhancement
    keywords: list[str] = []
    content_type: str = "section"

    # Cross-references
    cross_references: list[dict] = []

    # Flags
    is_leaf: bool = False
    has_table: bool = False
    has_figure: bool = False
```

**Why hybrid tree pattern** (from `relationship-tree-structures` rule):
- `parent_node_id` -- O(1) parent lookup, simple child queries
- `materialized_path` -- O(1) ancestor query via regex, subtree queries
- `child_node_ids` -- O(1) children without query, preserves order

### 4.4 Collection: `pages`

```python
# src/models/page.py [DONE - Phase 1]
class Page(BaseModel):
    document_id: str
    page_number: int          # 1-indexed physical page
    node_id: str | None = None
    content: str
    content_hash: str | None = None
    token_count: int = 0
```

**Why separate from nodes:** Keeps tree traversal fast (nodes are ~200 bytes each). Content only loaded when LLM needs to read. Matches PageIndex pattern where tree structure and content are separate concerns.

### 4.5 Collection: `retrieval_sessions`

```python
# src/models/session.py [DONE - Phase 1]
class RetrievalTrace(BaseModel):
    atlas_search_hits: list[dict] = []
    tree_navigation_path: list[str] = []
    nodes_read: list[str] = []
    cross_references_followed: list[dict] = []
    total_nodes_visited: int = 0
    reasoning_depth: int = 0

class Turn(BaseModel):
    turn_number: int
    query: str
    retrieval_trace: RetrievalTrace
    answer: str | None = None
    model: str | None = None
    latency_ms: int = 0
    timestamp: datetime

class RetrievalSession(BaseModel):
    session_id: str
    document_id: str | None = None
    user_id: str | None = None
    turns: list[Turn] = []
    created_at: datetime
    updated_at: datetime
```

### 4.6 MongoDB Indexes

```python
# src/db/indexes.py [DONE - Phase 1, 13 indexes]
INDEXES = {
    "documents": [
        {"keys": [("document_id", 1)], "unique": True},
        {"keys": [("ingestion.status", 1)]},
        {"keys": [("domain", 1), ("created_at", -1)]},
    ],
    "nodes": [
        {"keys": [("document_id", 1), ("node_id", 1)], "unique": True},
        {"keys": [("document_id", 1), ("parent_node_id", 1), ("sibling_order", 1)]},
        {"keys": [("document_id", 1), ("materialized_path", 1)]},
        {"keys": [("document_id", 1), ("depth", 1)]},
        {"keys": [("document_id", 1), ("is_leaf", 1)]},
        {"keys": [("cross_references.target_node_id", 1)]},
        {"keys": [("document_id", 1), ("content_type", 1)]},
    ],
    "pages": [
        {"keys": [("document_id", 1), ("page_number", 1)], "unique": True},
        {"keys": [("document_id", 1), ("node_id", 1)]},
    ],
    "retrieval_sessions": [
        {"keys": [("session_id", 1)], "unique": True},
    ],
}
```

**Index design follows ESR rule** (`index-compound-field-order`): Equality fields (document_id) first, Sort fields (sibling_order) second, Range fields last.

### 4.7 Key Tree Traversal Queries

**Get children of a node (for LLM tree navigation):**
```python
db.nodes.find({
    "document_id": doc_id,
    "parent_node_id": node_id
}).sort([("sibling_order", 1)])
```

**Get full subtree using $graphLookup:**
```python
db.nodes.aggregate([
    {"$match": {"document_id": doc_id, "node_id": root_id}},
    {"$graphLookup": {
        "from": "nodes",
        "startWith": "$node_id",
        "connectFromField": "node_id",
        "connectToField": "parent_node_id",
        "as": "descendants",
        "maxDepth": 10,
        "depthField": "traversal_depth",
        "restrictSearchWithMatch": {"document_id": doc_id}
    }}
])
```

**Get ancestors using materialized path:**
```python
ancestor_ids = node["materialized_path"].strip("/").split("/")
db.nodes.find({
    "document_id": doc_id,
    "node_id": {"$in": ancestor_ids}
}).sort([("depth", 1)])
```

**Get root-level ToC (for LLM navigation start):**
```python
db.nodes.find({
    "document_id": doc_id,
    "depth": 0
}).sort([("sibling_order", 1)])
```

---

## 5. Atlas Search (Lucene) Index Design

### 5.1 Nodes Fulltext Index

```python
# src/db/search_indexes.py [DONE - Phase 1]
NODES_SEARCH_INDEX = {
    "name": "nodes_fulltext",
    "type": "search",
    "definition": {
        "mappings": {
            "dynamic": False,  # Production best practice
            "fields": {
                "title": {"type": "string", "analyzer": "lucene.english"},
                "summary": {"type": "string", "analyzer": "lucene.english"},
                "keywords": [
                    {"type": "string", "analyzer": "lucene.keyword"},
                    {"type": "token", "normalizer": "lowercase"}
                ],
                "document_id": {"type": "token"},
                "node_id": {"type": "token"},
                "content_type": {"type": "token"},
                "depth": {"type": "number"},
                "start_page": {"type": "number"},
                "end_page": {"type": "number"},
                "is_leaf": {"type": "boolean"},
            }
        }
    }
}
```

### 5.2 Pages Content Index

```python
PAGES_SEARCH_INDEX = {
    "name": "pages_fulltext",
    "type": "search",
    "definition": {
        "mappings": {
            "dynamic": False,
            "fields": {
                "content": {"type": "string", "analyzer": "lucene.english"},
                "document_id": {"type": "token"},
                "node_id": {"type": "token"},
                "page_number": {"type": "number"},
            }
        }
    }
}
```

### 5.3 Atlas Search Query Patterns

**Primary node search (title + summary with boost):**
```python
pipeline = [
    {"$search": {
        "index": "nodes_fulltext",
        "compound": {
            "must": [
                {"equals": {"path": "document_id", "value": doc_id}}
            ],
            "should": [
                {"text": {"query": query, "path": "title",
                          "score": {"boost": {"value": 10}}}},
                {"text": {"query": query, "path": "summary",
                          "score": {"boost": {"value": 5}}}},
            ],
            "minimumShouldMatch": 1
        }
    }},
    {"$limit": 10},
    {"$project": {
        "node_id": 1, "title": 1, "summary": 1, "depth": 1,
        "start_page": 1, "end_page": 1, "content_type": 1,
        "score": {"$meta": "searchScore"}
    }}
]
```

**Fuzzy search (typo tolerance):**
```python
{"text": {
    "query": "fincial stabillity",
    "path": ["title", "summary"],
    "fuzzy": {"maxEdits": 1, "prefixLength": 3}
}}
```

---

## 6. Document Ingestion Pipeline

### 6.1 Pipeline Overview

This is the core of the system. It directly mirrors `page_index.py:1058-1100 page_index_main()`.

```
Input Document
  |
  v
[1. Parse]        get_page_tokens() -> list[(text, token_count)]
  |                ref: utils.py:413-437
  v
[2. ToC Detect]   check_toc() scans first N pages
  |                ref: page_index.py:688-724
  |                Returns: toc_content, has_page_numbers, toc_pages
  v
[3. Build Tree]   meta_processor() orchestrates 3 modes
  |                ref: page_index.py:950-989
  |                Mode A: process_toc_with_page_numbers() -> verify -> fix
  |                Mode B: process_toc_no_page_numbers() -> page mapping
  |                Mode C: process_no_toc() -> LLM generates tree
  |                FALLBACK: if Mode A/B fails -> fall back to Mode C
  v
[4. Verify]       verify_toc() samples sections for correctness
  |                ref: page_index.py:892-944
  |                fix_incorrect_toc() retries up to 3 rounds
  |                ref: page_index.py:731-866
  v
[5. Split]        process_large_node_recursively()
  |                ref: page_index.py:992-1019
  |                Splits nodes > max_pages_per_node or > max_tokens_per_node
  v
[6. Enrich]       tree_parser() -> summaries, node_ids, text
  |                ref: page_index.py:1021-1055
  |                generate_summaries_for_structure() ref: utils.py:616-623
  |                + keyword extraction (new)
  |                + cross-reference detection (new)
  v
[7. Persist]      Write to MongoDB:
  |                 - documents (metadata + status)
  |                 - nodes (tree structure)
  |                 - pages (raw content)
  v
[8. Index]        Atlas Search indexes build automatically
```

### 6.2 Tree Building -- Three Modes (from meta_processor)

The `meta_processor()` function at `page_index.py:950-989` is the orchestration heart:

```python
# Pseudocode matching reference meta_processor()
async def meta_processor(pdf_pages, config, llm):
    # Step 1: Detect ToC
    toc_result = await check_toc(pdf_pages, config, llm)

    if toc_result.has_toc and toc_result.has_page_numbers:
        # MODE A: Best case - ToC with page numbers
        structure = await process_toc_with_page_numbers(
            toc_result.content, pdf_pages, config, llm
        )
    elif toc_result.has_toc:
        # MODE B: ToC without page numbers
        structure = await process_toc_no_page_numbers(
            toc_result.content, pdf_pages, config, llm
        )
    else:
        # MODE C: No ToC - LLM generates from content
        structure = await process_no_toc(pdf_pages, config, llm)

    # Fallback: if Mode A/B fails, fall to Mode C
    if structure is None or structure == []:
        structure = await process_no_toc(pdf_pages, config, llm)

    return structure
```

**Mode A: ToC with Page Numbers** (ref: `page_index.py:614-643`)
1. Extract ToC content from detected pages
2. `toc_transformer()` converts ToC text to JSON structure (with continuation for long ToCs)
3. `toc_index_extractor()` maps ToC page numbers to physical page indices (handling offset)
4. `verify_toc()` samples sections, checks title appears on page
5. `fix_incorrect_toc()` fixes mismatches (up to 3 rounds)

**Mode B: ToC without Page Numbers** (ref: `page_index.py:589-610`)
1. Extract and transform ToC to JSON (same as Mode A steps 1-2)
2. `page_list_to_group_text()` splits document into token-limited groups with `<physical_index_N>` tags
3. `add_page_number_to_toc()` -- LLM reads each group and maps section titles to physical pages
4. Merge results, verify, fix

**Mode C: No ToC** (ref: `page_index.py:568-587`)
1. `page_list_to_group_text()` splits document into groups
2. `generate_toc_init()` -- LLM generates initial tree from first group
3. `generate_toc_continue()` -- LLM continues/extends tree for each subsequent group
4. Merge into single tree

### 6.3 Verification & Fix (ref: page_index.py:731-944)

The reference code's most sophisticated feature: automated verification with self-healing.

```python
# verify_toc() at page_index.py:892-944
# Samples ~20% of sections and checks:
# 1. Does the section title appear on the mapped page?
# 2. Does the section start at the beginning of the page?
#
# fix_incorrect_toc() at page_index.py:731-866
# For each failed verification:
# 1. Scan nearby pages (window of +-5) for the title
# 2. If found, update the mapping
# 3. If not found, try LLM-based correction
# Up to 3 retry rounds
```

### 6.4 Large Node Splitting (ref: page_index.py:992-1019)

```python
# process_large_node_recursively()
# For each node:
#   if pages > max_pages_per_node AND tokens > max_tokens_per_node:
#     Run Mode C (process_no_toc) on just this node's page range
#     Replace node with generated sub-tree
#     Recurse on children
# Concurrency: process sibling nodes in parallel (asyncio.gather)
```

### 6.5 Enrichment

**Summary generation** (ref: `utils.py:605-623`):
```python
# generate_node_summary() prompt:
# "You are given a part of a document, your task is to generate a
#  description of the partial document about what are main points
#  covered in the partial document."
# Uses asyncio.gather for parallel summaries across all nodes
```

**Keyword extraction** (new, not in reference):
- LLM extracts 3-8 keywords per node for Atlas Search faceting
- Cheaper alternative: TF-IDF from node text

**Cross-reference detection** (new, not in reference):
- Scan node text for: "see Appendix [X]", "refer to Section [X]", "Table [X]"
- Map targets to nodeIds via title matching

### 6.6 MongoDB Persistence Strategy

Write order matters for data integrity:

1. Create `documents` record with `status: "processing"`
2. Build complete tree in memory
3. `insert_many` into `nodes` collection (ordered)
4. `insert_many` into `pages` collection (ordered)
5. Update `documents`: `status: "completed"`, set totals
6. On failure: `status: "failed"` with error details

---

## 7. Retrieval Pipeline

### 7.1 Detailed Flow

```python
async def retrieve(query: str, document_id: str, session_id: str | None):
    # Step 1: Query Analysis (LLM classifies query)
    analysis = await analyze_query(query)
    # -> type: factual_lookup | analytical | comparison | multi_hop
    # -> keywords, expected_content_type

    # Step 2: Dual Retrieval (parallel)
    atlas_results, tree_results = await asyncio.gather(
        atlas_search(query, document_id, limit=5),
        tree_navigate(query, document_id, llm)
    )

    # Step 3: Merge & Deduplicate
    candidates = merge_results(atlas_results, tree_results,
                               atlas_weight=0.3, tree_weight=0.7)

    # Step 4: Content Loading
    for candidate in candidates[:5]:
        candidate.content = await load_pages(candidate.node_id, document_id)
        candidate.ancestors = await load_ancestors(candidate.node_id, document_id)

    # Step 5: LLM Reasoning (iterative)
    for iteration in range(max_iterations):
        response = await reason(query, candidates)
        if response.sufficient:
            return response.answer, trace
        # Navigate deeper or follow cross-reference
        candidates = await follow_action(response.next_action)

    # Step 6: Log Session
    await log_session(session_id, query, answer, trace)
```

### 7.2 Tree Navigation (ref: tutorials/tree-search/README.md)

The LLM navigates the tree top-down:

1. Load root-level nodes (depth=0) with titles + summaries
2. LLM selects 1-3 most relevant branches
3. Load children of selected branches
4. LLM narrows further
5. Repeat until leaf or sufficient content found

### 7.3 Multi-Turn Conversation

1. Load previous turns from `retrieval_sessions`
2. Include prior Q&A context in LLM prompt
3. Reuse previously visited nodes as starting context
4. Navigate from where last turn left off

---

## 8. Dual Retrieval Strategy

### 8.1 Why Two Paths

| Scenario | Atlas Search | Tree Navigation | Both |
|----------|-------------|-----------------|------|
| Exact terminology | Excellent | Good | Best |
| Vague/general terms | Poor | Excellent | Best |
| Cross-document refs | N/A | Excellent | Best |
| Typos in query | Good (fuzzy) | Poor | Best |
| Multi-hop reasoning | Poor | Excellent | Best |
| Speed-critical | Excellent (ms) | Slow (LLM) | Balanced |

### 8.2 Merge Strategy

```python
# Weighted merge: atlas_score * 0.3 + tree_score * 0.7
# Tree navigation is more reliable for complex queries
# Adaptive: simple keyword queries -> increase atlas_weight
#           complex analytical queries -> increase tree_weight
```

### 8.3 Fallback

1. Expand Atlas Search (fuzzy + broader fields)
2. Full tree scan (all depth-1 nodes)
3. Direct page content search
4. Return partial answer with confidence score

---

## 9. LLM Prompts (Stolen from Reference)

### 9.1 ToC Detection Prompt (ref: page_index.py:104-122)

```
"Determine if the following page from a document contains
a table of contents (ToC) or table of contents-like structure.
Return 'yes' if the page contains a ToC, 'no' if it does not."
```

### 9.2 ToC Extraction Prompt (ref: page_index.py:160-197)

```
"Extract the table of contents from the following page(s).
Return the exact text of the table of contents, preserving
the hierarchical structure with indentation."
```

### 9.3 Page Number Detection (ref: page_index.py:199-217)

```
"Examine the following table of contents text. Determine if
it contains page numbers for the entries. Return 'yes' if
page numbers are present, 'no' if they are not."
```

### 9.4 ToC to JSON Transform (ref: page_index.py:270-328)

```
"Convert the following table of contents into a JSON structure.
Each entry should have: title, structure (hierarchical code like 1.2.3),
and page_number (if available).
Format: [{"title": "...", "structure": "1", "page_number": N}, ...]"
```

### 9.5 Tree Generation from Content (ref: page_index.py:534-566)

```
"Analyze the following document text and generate a hierarchical
table of contents structure. The text is tagged with physical
page indices like <physical_index_N>.
Generate JSON: [{"title": "...", "structure": "1.1",
"physical_index": "<physical_index_N>"}]"
```

### 9.6 Tree Continuation (ref: page_index.py:499-531)

```
"Continue the following document structure based on new content.
Previous structure: {previous_structure}
New content: {new_content}
Continue or extend the structure maintaining consistency."
```

### 9.7 Title Verification (ref: page_index.py:13-45)

```
"Does the title '{title}' appear in the following page text?
Return 'yes' or 'no'.
Page text: {page_text}"
```

### 9.8 Node Summary (ref: utils.py:605-613)

```
"You are given a part of a document, your task is to generate
a description of the partial document about what are main points
covered in the partial document.
Partial Document Text: {text}
Directly return the description, do not include any other text."
```

### 9.9 Tree Navigation Prompt (for retrieval, ref: tutorials/tree-search/)

```
"You are a document navigation expert. Given the following sections
from a document's table of contents, select which section(s) most
likely contain the answer to the user's question.

Document: {document_name}
Description: {document_description}

Sections:
{sections with titles, page ranges, summaries}

Question: {query}

Respond in JSON:
{"selectedNodeIds": [...], "reasoning": "..."}"
```

### 9.10 Sufficiency Check Prompt (for retrieval)

```
"Analyze this document content to answer the question.

Question: {query}
Content: {content}
Context (ancestors): {ancestor_summaries}
Cross-references: {cross_refs}

Respond in JSON:
{
  "answer": "..." or null,
  "confidence": 0.0-1.0,
  "sufficient": true/false,
  "nextAction": null or {"type": "navigate_deeper"|"follow_reference", ...}
}"
```

---

## 10. Technology Stack

### 10.1 Core Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Language** | Python | 3.12+ | Direct PageIndex reference reuse, native tiktoken |
| **Database** | MongoDB Atlas | 8.0+ | JSON documents, Atlas Search, managed service |
| **Search** | Atlas Search (Lucene) | Built-in | Free, BM25, fuzzy, phrase, faceted |
| **LLM** | Configurable | - | Claude (Anthropic), GPT (OpenAI) |
| **PDF Parsing** | PyPDF2 + PyMuPDF | Latest | Same as PageIndex reference |
| **Token Counting** | tiktoken | Native | Accurate, fast, cached |
| **API Framework** | FastAPI | Latest | Async, Pydantic, OpenAPI docs |
| **Validation** | Pydantic v2 | Latest | Runtime validation, camelCase aliases |
| **Testing** | pytest + pytest-asyncio | Latest | Fixtures, async support |
| **Logging** | structlog | Latest | Structured JSON logging |
| **Config** | pydantic-settings | Latest | Env vars + .env files |

### 10.2 Project Structure

```
agentic-search-mongo/
  src/
    __init__.py
    config.py                    [DONE] Pydantic BaseSettings

    db/
      __init__.py
      client.py                  [DONE] MongoClient singleton + ping()
      collections.py             [DONE] 5 collection accessors
      indexes.py                 [DONE] 13 regular MongoDB indexes
      search_indexes.py          [DONE] 2 Atlas Search indexes

    models/
      __init__.py
      document.py                [DONE] Document, IngestionInfo, IngestionConfig
      node.py                    [DONE] Node with hybrid tree pattern
      page.py                    [DONE] Page with content, contentHash
      session.py                 [DONE] RetrievalSession, Turn, RetrievalTrace
      retrieval.py               [DONE] RetrievalCandidate, ReasonerResponse

    llm/
      __init__.py
      provider.py                [DONE] Abstract + Anthropic + OpenAI providers
      prompts/
        __init__.py
        toc_detection.py         ToC detection prompt templates
        tree_building.py         Tree generation prompts
        verification.py          Title verification prompts
        summarization.py         Node summary prompts
        tree_navigation.py       Retrieval tree nav prompts
        sufficiency_check.py     Answer sufficiency prompts
        query_analysis.py        Query classification prompts

    ingestion/
      __init__.py
      pipeline.py                Main orchestrator (maps to page_index_main)
      parsers/
        __init__.py
        pdf_parser.py            [DONE] PyPDF2 + PyMuPDF
        markdown_parser.py       [DONE] Header extraction
      tree_builder/
        __init__.py
        toc_detector.py          check_toc, toc_detector_single_page, find_toc_pages
        toc_transformer.py       toc_transformer (ToC text -> JSON)
        tree_generator.py        generate_toc_init, generate_toc_continue, process_no_toc
        page_mapper.py           toc_index_extractor, add_page_number_to_toc
        verifier.py              verify_toc, fix_incorrect_toc, check_title_appearance
        splitter.py              process_large_node_recursively
        tree_utils.py            write_node_id, get_nodes, list_to_tree, etc.
      enrichment/
        __init__.py
        summarizer.py            generate_node_summary, generate_summaries_for_structure
        keyword_extractor.py     Extract keywords per node
        cross_ref_detector.py    Detect "see Section X" patterns
        content_classifier.py    Classify section/appendix/table/figure

    retrieval/
      __init__.py
      pipeline.py                Main retrieval orchestrator
      query_analyzer.py          LLM query classification
      atlas_search.py            Atlas Search query builder
      tree_navigator.py          LLM tree navigation
      merger.py                  Weighted merge of dual results
      content_loader.py          Load pages for selected nodes
      reasoner.py                LLM sufficiency check + answer
      session_manager.py         Multi-turn session tracking

    utils/
      __init__.py
      tokens.py                  [DONE] tiktoken counting (cached)
      json_utils.py              [DONE] JSON extraction from LLM
      logger.py                  [DONE] structlog setup

    api/
      __init__.py
      server.py                  FastAPI app setup
      routes/
        __init__.py
        ingest.py                POST /documents (ingest)
        query.py                 POST /query (retrieval)
        documents.py             GET /documents, GET /documents/:id
        sessions.py              GET /sessions/:id

  tests/
    conftest.py                  [DONE] Shared fixtures
    test_config.py               [DONE] Config tests
    test_db.py                   [DONE] DB client tests
    test_models.py               [DONE] Model tests
    test_llm_provider.py         [DONE] LLM provider tests
    test_parsers.py              [DONE] Parser tests
    test_utils.py                [DONE] Utility tests
    # Phase 2+ tests added per module

  reference/
    PageIndex/                   Original code (read-only)

  docs/
    research/                    7 research files (3,081 lines)
    plans/
      VECTORLESS_RAG_SYSTEM_PLAN.md  This file
```

### 10.3 LLM Provider Abstraction

```python
# src/llm/provider.py [DONE]
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages, temperature=0.0, max_tokens=4096,
                   response_format=None) -> LLMResponse: ...

    @abstractmethod
    def count_tokens(self, text: str) -> int: ...

class AnthropicProvider(LLMProvider): ...  # Claude
class OpenAIProvider(LLMProvider): ...     # GPT

# Error hierarchy [DONE]:
# LLMError -> LLMAuthError, LLMBadRequestError, LLMRetryExhaustedError
# Retry: exponential backoff + jitter (pre-Phase-2 fix)
```

---

## 11. Build Phases

### Phase 1: Foundation -- COMPLETE

**Status:** DONE (56/56 tests passing, reviewed, hardened)

**Delivered:**
- [x] Project setup (Python 3.12+, venv, pytest, structlog)
- [x] Config (Pydantic BaseSettings with @lru_cache)
- [x] MongoDB client (singleton + ping())
- [x] 5 collection accessors
- [x] 13 MongoDB indexes
- [x] 2 Atlas Search indexes (nodes_fulltext, pages_fulltext)
- [x] 5 Pydantic models (Document, Node, Page, Session, Retrieval)
- [x] LLM provider abstraction (Anthropic + OpenAI)
- [x] LLM error hierarchy (LLMError -> Auth, BadRequest, RetryExhausted)
- [x] PDF parser (PyPDF2 + PyMuPDF with PDFParseError)
- [x] Markdown parser (header extraction)
- [x] Token counting (tiktoken, native)
- [x] JSON extraction (returns None on failure)
- [x] Structured logging (structlog)

**Review Results:**
- Security: 0 critical, 3 medium (pre-Phase-2 fixes identified)
- Performance: 3 perf-critical for Phase 2 (tiktoken cache, pool config, backoff)
- Quality: A- grade
- Verifier: 10/10 scenarios PASS

**Pre-Phase-2 Fixes Needed:**
- [ ] Create .gitignore (security: prevent .env exposure)
- [ ] Exponential backoff + jitter on LLM retries (replace flat 1s delay)
- [ ] Cache tiktoken encoder at module level (lru_cache)
- [ ] MongoDB pool config (maxPoolSize, timeouts)
- [ ] conftest.py get_settings.cache_clear() between tests

### Phase 2: Ingestion Pipeline

**Goal:** Transform PDF/Markdown into searchable hierarchical tree in MongoDB.

**Deliverables:**

#### 2.1 Pre-Phase-2 Fixes
- [ ] .gitignore, exponential backoff, tiktoken cache, pool config, conftest fix

#### 2.2 Tree Utilities (from utils.py)
Port directly from reference:
- [ ] `write_node_id()` -- assign sequential IDs to tree nodes
- [ ] `get_nodes()` -- flatten tree to list (excluding children)
- [ ] `structure_to_list()` -- full tree to flat list
- [ ] `get_leaf_nodes()` -- extract leaf nodes
- [ ] `is_leaf_node()` -- check if node is leaf
- [ ] `list_to_tree()` -- convert flat list to nested tree
- [ ] `post_processing()` -- convert physical indices to start/end page ranges
- [ ] `add_preface_if_needed()` -- add preface if doc starts after page 1
- [ ] `add_node_text()` -- attach page text to nodes
- [ ] `convert_physical_index_to_int()` -- parse physical index strings

#### 2.3 ToC Detection
Port from reference `page_index.py:104-724`:
- [ ] `toc_detector_single_page()` -- LLM checks one page for ToC
- [ ] `find_toc_pages()` -- scan first N pages for ToC
- [ ] `extract_toc_content()` -- extract ToC text with continuation
- [ ] `detect_page_index()` -- check if page numbers in ToC
- [ ] `toc_extractor()` -- combined extraction
- [ ] `check_toc()` -- main entry point

#### 2.4 ToC Transformation
Port from reference `page_index.py:240-358`:
- [ ] `toc_transformer()` -- ToC text to JSON (with continuation for long ToCs)
- [ ] `toc_index_extractor()` -- map ToC page numbers to physical pages

#### 2.5 Tree Generation
Port from reference `page_index.py:418-643`:
- [ ] `page_list_to_group_text()` -- split pages into token-limited groups
- [ ] `generate_toc_init()` -- LLM generates initial tree from text
- [ ] `generate_toc_continue()` -- LLM continues tree for next chunk
- [ ] `add_page_number_to_toc()` -- LLM maps titles to physical pages
- [ ] `process_toc_with_page_numbers()` -- Mode A pipeline
- [ ] `process_toc_no_page_numbers()` -- Mode B pipeline
- [ ] `process_no_toc()` -- Mode C pipeline

#### 2.6 Verification
Port from reference `page_index.py:731-944`:
- [ ] `check_title_appearance()` -- LLM verifies title on page
- [ ] `check_title_appearance_in_start()` -- checks title at page start
- [ ] `verify_toc()` -- sample verification of tree accuracy
- [ ] `fix_incorrect_toc()` -- fix mismatches (retry loop, up to 3 rounds)

#### 2.7 Large Node Splitting
Port from reference `page_index.py:992-1019`:
- [ ] `process_large_node_recursively()` -- recursive split of oversized nodes

#### 2.8 Enrichment
Port summary from reference + new features:
- [ ] `generate_node_summary()` -- LLM summary per node (ref: utils.py:605-613)
- [ ] `generate_summaries_for_structure()` -- parallel summaries (ref: utils.py:616-623)
- [ ] `generate_doc_description()` -- document-level description (ref: utils.py:649-658)
- [ ] Keyword extraction (new) -- 3-8 keywords per node for Atlas Search
- [ ] Cross-reference detection (new) -- detect "see Section X" patterns
- [ ] Content type classification (new) -- section/appendix/table/figure

#### 2.9 LLM Prompt Templates
Extract all prompts from reference into dedicated module:
- [ ] ToC detection prompts
- [ ] Tree building prompts
- [ ] Verification prompts
- [ ] Summary prompts

#### 2.10 Pipeline Orchestrator
Port from reference `page_index.py:950-1100`:
- [ ] `meta_processor()` -- 3-mode orchestrator with fallback
- [ ] `tree_parser()` -- full tree parsing pipeline
- [ ] `page_index_main()` -- main entry point
- [ ] MongoDB persistence (documents, nodes, pages)

**Acceptance Criteria:**
- Ingest a PDF and produce correct hierarchical tree in MongoDB
- Tree structure matches reference PageIndex output for same document
- All 3 modes (A, B, C) work with fallback
- Verification + fix loop corrects mismatches
- Node summaries generated
- Atlas Search returns relevant results for test queries

### Phase 3: Retrieval Pipeline

**Goal:** Answer questions from ingested documents using dual retrieval.

**Deliverables:**
- [ ] Query analyzer (LLM classifies query type, extracts keywords)
- [ ] Atlas Search query builder (text, phrase, fuzzy, boolean, filtered)
- [ ] Tree navigator (LLM reads ToC, selects branches, drills down)
- [ ] Result merger (weighted: atlas * 0.3 + tree * 0.7)
- [ ] Content loader (fetch pages for selected nodes, include ancestors)
- [ ] LLM reasoner (sufficiency check, answer generation, cross-ref following)
- [ ] Session manager (multi-turn conversation tracking in MongoDB)
- [ ] Retrieval orchestrator (end-to-end async pipeline)

**Acceptance Criteria:**
- Answer factual questions from ingested documents
- Cross-reference following works ("see Appendix G")
- Multi-turn conversations maintain context
- Retrieval traces logged in sessions collection
- Both Atlas Search and tree navigation contribute to results

### Phase 4: API & Integration

**Goal:** REST API for external consumers.

**Deliverables:**
- [ ] FastAPI server setup
- [ ] POST /documents -- upload + ingest document
- [ ] POST /query -- query an ingested document
- [ ] GET /documents -- list documents
- [ ] GET /documents/{id} -- document details with tree summary
- [ ] GET /sessions/{id} -- session history
- [ ] Input validation (Pydantic request/response models)
- [ ] Error handling middleware
- [ ] CORS and rate limiting

**Acceptance Criteria:**
- All endpoints return correct responses
- Input validation rejects malformed requests
- Errors are structured and informative
- API docs auto-generated at /docs

### Phase 5: Testing & Benchmarking

**Goal:** Prove the system works and measure accuracy.

**Deliverables:**
- [ ] Integration tests (full ingest -> query flow)
- [ ] Atlas Search query tests (with real MongoDB)
- [ ] Accuracy benchmarks on test documents
- [ ] Performance benchmarks (latency, throughput)
- [ ] Comparison: our system vs raw Atlas Search vs raw tree nav
- [ ] Cost analysis (LLM tokens per ingest, per query)

**Acceptance Criteria:**
- Integration tests pass for happy path + key error cases
- Accuracy > 90% on structured documents
- Retrieval latency < 5s single-turn (including LLM)
- Ingestion: 100-page PDF in < 5 minutes
- Cost documented per operation

---

## 12. Testing Strategy

### 12.1 Unit Tests (per module)

**Ingestion:**
- Tree utilities: write_node_id, list_to_tree, get_nodes
- ToC detection: mock LLM, verify mode selection
- Tree building: mock LLM, verify structure generation
- Verification: mock LLM, verify fix loop
- Enrichment: mock LLM, verify summary/keyword output
- Persistence: mock MongoDB, verify write order

**Retrieval:**
- Query analyzer: classify different query types (mocked LLM)
- Atlas Search: verify generated aggregation pipelines
- Tree navigator: verify node selection (mocked LLM)
- Merger: verify weighted ranking with known inputs
- Reasoner: verify sufficiency parsing

### 12.2 Integration Tests

- Full ingestion: PDF -> MongoDB tree (requires real LLM + MongoDB)
- Full retrieval: query -> answer (requires ingested doc)
- Atlas Search: real search queries against indexed data
- Multi-turn: follow-up questions maintain context
- Mode fallback: force Mode C by providing no-ToC doc

### 12.3 Test Documents

- 1 financial report (test Mode A: ToC with page numbers)
- 1 technical manual (test Mode B: ToC without page numbers)
- 1 plain text document (test Mode C: no ToC)
- 1 Markdown document (test markdown parser path)

---

## 13. Production Readiness

### 13.1 Configuration

```bash
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=agentic_search

# LLM
LLM_PROVIDER=anthropic
LLM_INGESTION_MODEL=gpt-4o-2024-11-20  # Matches PageIndex default
LLM_RETRIEVAL_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Ingestion (matches reference config.yaml)
MAX_PAGES_PER_NODE=10
MAX_TOKENS_PER_NODE=20000
TOC_CHECK_PAGES=20

# Retrieval
MAX_RETRIEVAL_ITERATIONS=5
ATLAS_SEARCH_WEIGHT=0.3
TREE_NAVIGATION_WEIGHT=0.7
TOP_N_CANDIDATES=5

# API
PORT=8000
LOG_LEVEL=info
```

### 13.2 Scaling

- MongoDB sharding on `document_id` for >1M documents
- Stateless API scales horizontally
- Queue-based ingestion with configurable LLM concurrency
- Cache root ToC structures in memory

### 13.3 Security

- MongoDB Atlas network peering / IP allowlist
- API authentication (API keys)
- LLM API keys via SecretStr (never logged)
- Input sanitization on all endpoints
- Rate limiting on query endpoint
- .gitignore prevents .env exposure

---

## 14. Improvements Over Original PageIndex

| Area | Original PageIndex | Our Implementation |
|------|-------------------|-------------------|
| **Storage** | JSON files on disk | MongoDB with indexes + Atlas Search |
| **Full-text search** | None | Atlas Search (Lucene) with BM25, fuzzy, phrase |
| **Retrieval** | Tree navigation only | Dual: Atlas Search + Tree Navigation |
| **Cross-references** | Not implemented | Explicit detection, storage, navigation |
| **Multi-document** | Single document | Multi-document with cross-doc search |
| **Session tracking** | None | Multi-turn conversation tracking |
| **Keywords** | None | Per-node keywords for Atlas Search |
| **LLM provider** | OpenAI only (hardcoded) | Provider-agnostic (Claude + GPT) |
| **Error handling** | Basic retry | Error hierarchy + exponential backoff |
| **Query analysis** | None | LLM classifies query type |
| **Merge ranking** | N/A | Weighted merge of dual retrieval |
| **Analytics** | JSON log files | MongoDB analytics collection |
| **API** | Python CLI | FastAPI REST API |
| **Config** | YAML only | Pydantic Settings (env + YAML) |

**DeepRead-Inspired Enhancements:**
- Explicit locate phase (Atlas Search + tree nav) -> read phase (content loading)
- Coordinate-style metadata (materialized paths)
- Separate Retrieve + ReadSection tools

---

**Plan Status:** ACTIVE
**Phase 1:** COMPLETE (56/56 tests, reviewed, hardened)
**Next:** Phase 2 (Ingestion Pipeline)
**Build Order:** Phase 1 -> 2 -> 3 -> 4 -> 5

---

**This plan is the single source of truth for the project.**
**Every function maps to a reference line number.**
**Every module maps to a file in the project structure.**
**MongoDB is the foundation. PageIndex is the gold standard.**
