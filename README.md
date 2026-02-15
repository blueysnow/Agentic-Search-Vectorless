# Agentic Search -- Vectorless RAG on MongoDB

A document retrieval system that **doesn't use vector embeddings**. Instead, it builds a hierarchical tree from your documents (like a table of contents) and lets an LLM **reason its way** to the right answer -- navigating sections, reading summaries, and drilling deeper only when needed.

Think about how you'd actually search a 200-page report. You wouldn't read every paragraph. You'd check the table of contents, pick the right chapter, scan section headings, then read the relevant pages. That's exactly what this system does.

```
PDF upload  -->  Build tree (LLM extracts structure)  -->  Store in MongoDB
                                                              |
User query  -->  Atlas Search (fast keyword hit)  ----+       |
            -->  Tree Navigation (LLM reasoning)  ----+--> Merge --> Answer
```

## Why Vectorless?

Vector search works by converting text into numbers and finding "similar" numbers. It's good, but it has real problems:

- **It's a black box.** You can't explain _why_ result #3 ranked higher than result #7.
- **It loses structure.** A 200-page PDF becomes a flat bag of chunks. Chapter 1 and Appendix G look the same.
- **It hallucinates relevance.** "Revenue in Germany" might match "Revenue in Germany's neighboring countries" because the vectors are close.

This system takes a different approach: **structure the document like a human would read it, then let an LLM navigate that structure.**

Every retrieval step is traceable. The system tells you: "I looked at the Table of Contents, picked Chapter 3 (European Markets), drilled into Section 3.2 (Germany), and read pages 45-48." You can verify every step.

## How It Works

### Ingestion: PDF --> Tree

The system reads your document and builds a hierarchical tree. Three modes, with automatic fallback:

| Mode | When | How |
|------|------|-----|
| **A** | Document has a ToC with page numbers | Extract ToC, map sections to pages, verify with LLM |
| **B** | Document has a ToC but no page numbers | Extract ToC, LLM matches section titles to page content |
| **C** | No ToC at all | LLM reads the document and generates a hierarchy from scratch |

If Mode A gets low accuracy (< 60%), it falls back to B, then C. The system verifies page assignments by checking if section titles actually appear on the expected pages, and auto-corrects errors.

Large sections (> 10 pages or 20K tokens) get recursively split into sub-sections. Every node gets a summary, keywords, content type classification, and cross-reference detection (catches things like "See Appendix G" or "Refer to Table 3.2").

The output is a tree stored across **three MongoDB collections**:

```
documents  (1 doc = 1 record with metadata + ingestion status)
     |
     +---> nodes  (the tree -- titles, summaries, keywords, hierarchy pointers)
     |
     +---> pages  (raw page text, separate from nodes to keep the tree lightweight)
```

### Retrieval: Query --> Answer

When a user asks a question, the system runs two retrieval paths **in parallel**:

**Path 1: Atlas Search (fast, keyword-driven)**

A standard full-text search using MongoDB Atlas Search. Lucene-powered BM25 scoring across titles, summaries, and keywords with configurable boost weights (title: 10x, summary: 5x, keywords: 3x). Returns results in milliseconds.

Falls back to MongoDB `$text` indexes on Community Edition -- same field weights, just a different engine under the hood.

**Path 2: Tree Navigation (slower, reasoning-driven)**

An LLM reads the root nodes (depth 0 -- the "table of contents"), selects 1-3 most relevant branches, loads their children, selects again, and repeats. Up to 5 levels deep. Each selected node gets scored by depth -- deeper means more specific, which usually means more relevant.

```
Root: [Chapter 1] [Chapter 2] [Chapter 3] [Appendix A]
                                    |
LLM picks Chapter 3        [3.1 Overview] [3.2 Germany] [3.3 France]
                                               |
LLM picks 3.2              [3.2.1 Revenue] [3.2.2 Costs] [3.2.3 Outlook]
                                    |
LLM picks 3.2.1            --> Load page content --> Read
```

**Merge & Reason**

Results from both paths are normalized to [0,1] and merged with a weighted blend (Atlas: 0.3, Tree: 0.7). The top candidates get their page content loaded in parallel (ThreadPoolExecutor, 5 workers, 10s timeout).

Then an LLM reasoning loop kicks in (up to 5 iterations):

1. Read the combined content from top candidates
2. Check: "Is this enough to answer the question?"
3. If yes --> generate answer with confidence score
4. If no --> the LLM picks a next action:
   - `navigate_deeper` -- load child nodes
   - `follow_reference` -- follow a cross-reference ("See Table 3.2")
   - `search_different_section` -- give up on this branch
5. Load the new content, repeat from step 2

The reasoning path is fully traced and returned with the response.

## Why MongoDB

This is not a "we needed a database and picked one" situation. The document model is specifically why this architecture works.

### The tree is a document

Each node in the tree is a MongoDB document with three hierarchy patterns:

```json
{
  "nodeId": "0006",
  "documentId": "report_2024",
  "parentNodeId": "0003",
  "materializedPath": "/0001/0003/0006",
  "childNodeIds": ["0007", "0008", "0009"],
  "depth": 2,
  "siblingOrder": 1,

  "title": "3.2 Germany",
  "summary": "Covers Q3 revenue growth in Germany...",
  "keywords": ["germany", "revenue", "q3", "european-markets"],
  "contentType": "section",

  "startPage": 45,
  "endPage": 48,
  "isLeaf": true,

  "crossReferences": [
    { "targetNodeId": "0042", "label": "A.1", "type": "appendix" }
  ]
}
```

Three traversal patterns in one document:
- **`parentNodeId`** -- go up one level: `O(1)`
- **`materializedPath`** -- get all ancestors from root to here in a single query: `O(1)`
- **`childNodeIds`** -- get ordered children without a query: `O(1)`

A relational database would need self-joins or recursive CTEs for this. A key-value store couldn't index the nested fields. MongoDB stores and queries this natively.

### Atlas Search lives next to your data

The Atlas Search indexes sit on the same cluster as the tree. No separate search service, no data synchronization, no network hop. One `$search` aggregation stage in the pipeline:

```javascript
[{
  $search: {
    index: "nodes_fulltext",
    compound: {
      must: [{ equals: { path: "documentId", value: "report_2024" } }],
      should: [
        { text: { query: "Germany revenue", path: "title", score: { boost: { value: 10 } } } },
        { text: { query: "Germany revenue", path: "summary", score: { boost: { value: 5 } } } },
        { text: { query: "Germany revenue", path: "keywords", score: { boost: { value: 3 } } } }
      ]
    }
  }
}]
```

And when Atlas Search isn't available (Community Edition, local dev), the system auto-detects at startup and falls back to `$text` search with matching weights. Same API, same code path.

### Batch operations fit the access patterns

The retrieval pipeline's hot path is:

1. **Load root nodes**: `find({ documentId, depth: 0 }).sort({ siblingOrder: 1 })` -- index hit
2. **Load children of selected nodes**: `find({ documentId, parentNodeId: { $in: [...] } })` -- single `$in` query instead of N queries
3. **Load page content**: `find({ documentId, nodeId: { $in: [...] } }).sort({ pageNumber: 1 })` -- batched read
4. **Load ancestors**: `find({ documentId, nodeId: { $in: path_segments } })` -- one query from materialized path

Every query is covered by a compound index. 13 regular indexes + 2 Atlas Search indexes, all created at startup:

| Collection | Indexes | Key Patterns |
|-----------|---------|-------------|
| `documents` | 3 | documentId (unique), ingestion status, domain + date |
| `nodes` | 7 + text + Atlas Search | documentId+nodeId (unique), parent+sibling, materialized path, depth, leaf, content type, cross-refs |
| `pages` | 3 + Atlas Search | documentId+page (unique), documentId+nodeId, nodeId |
| `retrieval_sessions` | 3 | sessionId (unique), userId+date, documentId+date |

### Sessions are append-only arrays

Multi-turn conversations are stored as a single document with a `turns` array. Each new turn is a `$push` -- atomic, no read-modify-write:

```javascript
db.retrieval_sessions.updateOne(
  { sessionId: "abc-123" },
  {
    $push: { turns: { query: "...", answer: "...", trace: {...} } },
    $inc: { "summary.totalTurns": 1, "summary.totalNodesVisited": 5 },
    $set: { updatedAt: new Date() }
  }
)
```

One write, three operations, atomic. The conversation history stays ordered, the summary stats stay consistent, and you never need a separate "turns" table.

### Content is separate from structure

The tree nodes are small (~200 bytes each -- just titles, summaries, and pointers). Page content lives in a separate `pages` collection. This means tree traversal queries touch small documents (fast), and content is only loaded when the LLM actually needs to read it.

This is a deliberate design choice. During tree navigation, the LLM makes 3-4 selection decisions. Each decision needs to see ~50 node summaries. If each node included its full page text, you'd be loading megabytes of unused content on every navigation step.

## Inspired by PageIndex

The tree-building approach is based on [PageIndex](https://github.com/VectifyAI/PageIndex) by VectifyAI, which demonstrated that structured hierarchical retrieval can outperform vector-based RAG (98.7% on FinanceBench). Their insight -- treat documents like trees, not flat bags of chunks -- is the foundation of this project.

This implementation diverges from PageIndex in a few key areas:

| | PageIndex | This Project |
|--|-----------|-------------|
| **Storage** | JSON files on disk | MongoDB (indexed, queryable, persistent) |
| **Search** | Tree navigation only | Dual path: Atlas Search + Tree Navigation |
| **Multi-document** | One PDF = one file | Multiple documents in one database, queryable together |
| **Cross-references** | Not handled | Auto-detected during ingestion, followable during retrieval |
| **Sessions** | None | Multi-turn conversations with full retrieval traces |
| **LLM** | OpenAI only | Provider-agnostic (Claude, GPT) |
| **API** | Python CLI | FastAPI with REST endpoints + SSE streaming |
| **Retrieval** | Not implemented (indexing only) | Full agentic pipeline with reasoning loop |

PageIndex builds the tree. This project builds the tree **and** searches it.

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY or OPENAI_API_KEY to .env

docker compose up
```

Three containers: MongoDB 7.0 (with replica set), FastAPI backend on `:8000`, Next.js frontend on `:3000`.

### Local Development

**Backend:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Start MongoDB (needs replica set for Atlas Search)
mongod --replSet rs0

# Run backend
uvicorn src.api.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

```bash
# Required
MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0
MONGODB_DATABASE=agentic_search

# LLM (pick one)
LLM_PROVIDER=anthropic          # or "openai"
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional
LLM_INGESTION_MODEL=claude-3-5-haiku-20241022
LLM_RETRIEVAL_MODEL=claude-sonnet-4-20250514
ATLAS_SEARCH_WEIGHT=0.3
TREE_NAVIGATION_WEIGHT=0.7
MAX_RETRIEVAL_ITERATIONS=5
TOP_N_CANDIDATES=5
```

## API

```
POST /ingest/upload        Upload a document (PDF, Markdown, or text)
POST /query/               Ask a question about a document
POST /query/stream         Same, but with SSE streaming

GET  /documents            List all documents
GET  /documents/{id}       Get document details + tree structure

GET  /sessions             List retrieval sessions
GET  /sessions/{id}        Get session with full conversation history
DELETE /sessions/{id}      Delete a session

GET  /health               Health check (includes MongoDB status)
```

### Example

```bash
# Upload a document
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@annual-report.pdf" \
  -F "name=Annual Report 2024" \
  -F "domain=finance"

# Ask a question
curl -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the revenue in Germany?", "documentId": "..."}'

# Response includes the answer + full retrieval trace
{
  "answer": "Revenue in Germany was $4.2B in Q3...",
  "confidence": 0.92,
  "sessionId": "sess-abc123",
  "trace": {
    "atlas_hits": 3,
    "tree_hits": 2,
    "merged_candidates": 4,
    "iterations": 1,
    "navigation_path": ["0001", "0003", "0006"],
    "nodes_read": ["0006", "0007"]
  }
}
```

## Project Structure

```
src/
  api/                  FastAPI routes + middleware
  db/                   MongoDB client, collections, indexes
  ingestion/
    parsers/            PDF + Markdown extraction
    tree_builder/       ToC detection, tree generation, verification, splitting
    enrichment/         Summaries, keywords, cross-references, content classification
  retrieval/
    pipeline.py         Orchestrator: query analysis -> dual retrieval -> merge -> reason
    atlas_search.py     Atlas Search $search aggregation (+ $text fallback)
    tree_navigator.py   LLM-driven top-down tree traversal
    merger.py           Weighted merge of both retrieval paths
    content_loader.py   Batch content loading with ThreadPoolExecutor
    reasoner.py         LLM sufficiency checking + iterative reasoning
    session_manager.py  Multi-turn session persistence
  llm/                  Provider abstraction (Anthropic/OpenAI) + prompt templates
  models/               Pydantic models for all 5 collections

frontend/               Next.js 15 + React 19 UI
  app/chat/             Chat interface with document selector
  app/documents/        Document upload + tree visualization
  app/sessions/         Session history + replay

tests/                  453 backend tests, 300 frontend tests
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | MongoDB 7.0 + Atlas Search (Lucene) |
| Backend | Python 3.12, FastAPI, Pydantic, PyMongo |
| Frontend | Next.js 15, React 19, TanStack Query |
| LLM | Claude (Anthropic) or GPT (OpenAI) |
| PDF Parsing | pypdf + PyMuPDF |
| Deployment | Docker Compose |

## License

MIT
