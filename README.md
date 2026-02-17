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

- **It's a black box.** You can't explain _why_ result #3 ranked higher than result #7. Cosine similarity gives you a number, not a reason.
- **It loses structure.** A 200-page PDF becomes a flat bag of chunks. Chapter 1 and Appendix G look the same. The table of contents, section hierarchy, and page flow are gone.
- **It can't navigate.** When a result says "See Appendix G" or "Refer to Table 3.2", vector search has no way to follow that reference. The structural connections between sections are lost at embedding time.

This system takes a different approach: **structure the document like a human would read it, then let an LLM navigate that structure.**

Every retrieval step is fully traceable. The system tells you: "I looked at the Table of Contents, picked Chapter 3 (European Markets), drilled into Section 3.2 (Germany), and read pages 45-48." You can verify every step. No hidden similarity scores -- just a clear navigation path through the document's own structure.

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

Falls back to MongoDB `$text` indexes when search indexes aren't configured -- same field weights, just a different engine under the hood.

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

This isn't just "we needed a database." MongoDB replaces what would normally be **three or four separate systems** -- and the architecture is simpler because of it.

A typical RAG stack looks like: Postgres (data) + Pinecone/Weaviate (search) + Redis (sessions) + application code to sync them. This project uses **one connection string**. MongoDB handles the tree storage, the full-text search, the session persistence, and the retrieval queries -- all in the same cluster, same deployment, same API.

Here's why that matters for this specific architecture:

### 1. The document model IS the tree

A tree node in code maps directly to a document in MongoDB. No ORM translation, no table joins, no impedance mismatch. What you see in your code is what's stored in the database:

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

Three tree-traversal patterns coexist in one document:
- **`parentNodeId`** -- go up one level: O(1)
- **`materializedPath`** -- get all ancestors root-to-here in a single query: O(1)
- **`childNodeIds`** -- ordered children without a query at all: O(1)

In a relational database, this would require a self-referencing table with recursive CTEs for ancestor queries, a separate junction table for ordered children, and a materialized path column that you'd have to maintain manually with triggers. In MongoDB, it's just... fields in a document.

And because different node types have different shapes (a table node has column metadata, an appendix has citation info, a figure has dimensions), MongoDB's flexible schema handles it in one collection. No ALTER TABLE, no schema migrations, no "type" column with nullable fields for every variant.

### 2. Search and data live together -- zero sync

This is the big one.

Most search architectures look like this:

```
App writes to Postgres  -->  Change Data Capture  -->  Elasticsearch
App reads from Postgres (data) + Elasticsearch (search) + joins them in code
```

Two databases, two schemas, a synchronization pipeline, and application-level joins. When a node's summary changes, you update Postgres and **hope** Elasticsearch catches up before the next query.

With MongoDB Atlas Search, the Lucene index sits **on the same data**. No sync. No CDC pipeline. No eventual consistency gap. When a node is inserted during ingestion, it's immediately searchable:

```javascript
// This is one aggregation pipeline. Search + filter + project. One round trip.
[{
  $search: {
    index: "nodes_fulltext",
    compound: {
      must: [{ equals: { path: "documentId", value: "report_2024" } }],
      should: [
        { text: { query: "Germany revenue", path: "title",   score: { boost: { value: 10 } } } },
        { text: { query: "Germany revenue", path: "summary", score: { boost: { value: 5 } } } },
        { text: { query: "Germany revenue", path: "keywords", score: { boost: { value: 3 } } } }
      ]
    }
  }
},
{ $limit: 10 },
{ $project: { nodeId: 1, title: 1, summary: 1, depth: 1, score: { $meta: "searchScore" } } }]
```

The same query that searches also filters by document, scores by field importance, and projects only the fields the LLM needs. One pipeline, one network call. Try doing that across Postgres + Elasticsearch.

And when search indexes aren't configured yet, the system auto-detects at startup and falls back to `$text` indexes with the same field weights. Same application code, different engine under the hood. No code path divergence.

### 3. Every retrieval query is a single indexed operation

The retrieval pipeline's hot path -- the queries that run on every single user question -- maps cleanly to MongoDB's query model:

```javascript
// Step 1: Load the "table of contents" (root nodes)
db.nodes.find({ documentId: "report_2024", depth: 0 })
         .sort({ siblingOrder: 1 })
// Uses compound index: (documentId, depth)

// Step 2: LLM picks 3 branches. Load ALL their children in one query.
db.nodes.find({ documentId: "report_2024",
                parentNodeId: { $in: ["0001", "0003", "0005"] } })
         .sort({ siblingOrder: 1 })
// Uses compound index: (documentId, parentNodeId, siblingOrder)
// One $in query instead of 3 separate queries

// Step 3: Load page content for the final nodes
db.pages.find({ documentId: "report_2024",
                nodeId: { $in: ["0006", "0007"] } })
         .sort({ pageNumber: 1 })
// Uses compound index: (documentId, nodeId)

// Step 4: Load ancestor context via materialized path
// Node 0006 has materializedPath: "/0001/0003/0006"
// Parse path segments, single $in query:
db.nodes.find({ documentId: "report_2024",
                nodeId: { $in: ["0001", "0003"] } },
              { nodeId: 1, title: 1, summary: 1, depth: 1 })
         .sort({ depth: 1 })
// Uses compound index: (documentId, nodeId)
```

Four queries. Four index hits. Zero collection scans. The compound indexes are designed to match these exact access patterns -- 13 regular indexes + 2 Atlas Search indexes, all created at startup.

| Collection | Indexes | Why |
|-----------|---------|-----|
| `nodes` | 7 regular + text + Atlas Search | Tree traversal in every direction: up, down, by depth, by type, by path |
| `pages` | 3 regular + Atlas Search | Content lookup by node or by page number |
| `documents` | 3 regular | Document listing, status filtering, domain browsing |
| `retrieval_sessions` | 3 regular | Session lookup by user, by document, by ID |

### 4. Atomic multi-operation writes

Multi-turn conversations are a single document with a `turns` array. Adding a turn is one atomic operation that does three things at once:

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

Append a turn, increment counters, update timestamp. One write. Atomic. No transaction needed. No separate "turns" table with a foreign key. No read-modify-write cycle. No race condition between two concurrent requests appending to the same session.

Cross-references work the same way -- they're an array inside the node document. Ingestion detects "See Table A.1" and pushes `{ targetNodeId: "0042", label: "A.1", type: "table" }` directly into the node. During retrieval, the LLM sees the array and follows the reference. No join table, no separate lookup.

### 5. Structure and content at different scales

The tree nodes are deliberately small (~200 bytes). Page content lives in a separate `pages` collection. This lets the system query structure fast and load content only when needed.

During tree navigation, the LLM makes 3-4 selection decisions. At each level, it reads ~50 node summaries to decide which branches to explore. If node documents included full page text, each navigation step would load megabytes of content the LLM never reads.

With separate collections:
- **Tree queries** touch small documents (titles + summaries + pointers) --> fast
- **Content queries** run only after the LLM decides what to read --> no wasted I/O
- **Atlas Search** indexes the lightweight nodes collection --> smaller index, faster search

This is a natural MongoDB pattern: model your data by **access pattern**, not by entity relationship. The system accesses structure and content at different times, so they live in different collections.

### What this replaces

Without MongoDB, this system would need:

| Concern | Typical Stack | MongoDB |
|---------|-------------|---------|
| Tree storage | Postgres with recursive CTEs | Document model with materialized paths |
| Full-text search | Elasticsearch (+ sync pipeline) | Atlas Search (same cluster, zero sync) |
| Session persistence | Redis or Postgres + turns table | `$push` to embedded array |
| Content storage | S3 or file system | `pages` collection (co-located, indexed) |
| Batch child lookups | N+1 queries or complex JOINs | Single `$in` query |
| Schema for mixed node types | Nullable columns or EAV pattern | Flexible documents in one collection |

That's four services collapsed into one. One connection string. One deployment. One set of indexes to think about.

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

Three containers: MongoDB 7.0 (with replica set), FastAPI backend on `:8002`, Next.js frontend on `:3000`.

**With `$search` support (Atlas Search on Community Edition):**

```bash
# Start with the search profile (adds mongot for native $search)
docker compose --profile search up
```

This adds MongoDB Community 8.0+ with the `mongot` binary, enabling native `$search` aggregation pipelines. Five containers total:

| Container | Image | Port | Description |
|-----------|-------|------|-------------|
| mongodb | mongo:7.0 | 27017 | Default MongoDB (replica set, no auth) |
| mongodb-search | mongodb-community-server:8.0.4 | 27018 | MongoDB with mongot integration + auth |
| mongot | mongodb-community-search | 8080, 9946 | Lucene search engine (gRPC on 27028) |
| backend | FastAPI | 8002 | Python API server |
| frontend | Next.js 15 | 3000 | React UI |

Without the search profile, the system automatically falls back to `$text` indexes.

To connect the backend to the search-enabled MongoDB instead of the default one:

```bash
docker compose -f docker-compose.yml -f docker-compose.search.override.yml --profile search up
```

### Local Development

**Backend (using uv):**

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# Start MongoDB (needs replica set)
# Option 1: Use Docker
docker compose up mongodb

# Option 2: Local mongod
mongod --replSet rs0

# Run backend
uvicorn src.api.server:create_app --factory --reload --port 8002
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
LLM_INGESTION_MODEL=claude-haiku-4-5-20251001
LLM_RETRIEVAL_MODEL=claude-haiku-4-5-20251001
ATLAS_SEARCH_WEIGHT=0.3
TREE_NAVIGATION_WEIGHT=0.7
MAX_RETRIEVAL_ITERATIONS=5
TOP_N_CANDIDATES=5
PORT=8002
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
curl -X POST http://localhost:8002/ingest/upload \
  -F "file=@annual-report.pdf" \
  -F "name=Annual Report 2024" \
  -F "domain=finance"

# Ask a question
curl -X POST http://localhost:8002/query/ \
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

tests/                  471 backend tests, 300 frontend tests
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
