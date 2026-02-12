# PageIndex Cookbook Patterns Research

**Date**: 2026-02-12
**Source**: `/reference/PageIndex/cookbook/`
**Purpose**: Extract proven UX/DX patterns from official PageIndex cookbook to inform UI implementation

---

## 1. Cookbook Contents

| Notebook | Purpose | Key Pattern |
|----------|---------|-------------|
| `pageindex_RAG_simple.ipynb` | Minimal vectorless RAG example | 3-step workflow: tree → search → answer |
| `pageIndex_chat_quickstart.ipynb` | Chat API quick start | Streaming chat interface with doc context |
| `agentic_retrieval.ipynb` | Prompt-driven retrieval | JSON output mode for structured retrieval |
| `vision_RAG_pageindex.ipynb` | Vision-based RAG | No OCR, image-native reasoning |

---

## 2. Critical Discovery: Chat-First Approach

### What They Actually Built (vs. What We Planned)

| Our Plan (Form-Based) | Their Approach (Chat-First) |
|-----------------------|------------------------------|
| Query form → Submit → Results page | Chat interface with streaming responses |
| Single-shot Q&A | Multi-turn conversational context |
| JSON response only | Flexible: natural language OR JSON retrieval |
| Static results | Real-time streaming with thinking process |

### PageIndex Chat API Pattern

```python
# Simple conversational query
for chunk in pi_client.chat_completions(
    messages=[{"role": "user", "content": query}],
    doc_id=doc_id,
    stream=True
):
    print(chunk, end='', flush=True)
```

**Output shows transparent reasoning:**
```
I'll help you find the revenue information. Let me first check the document structure...
{"doc_name": "report.pdf"}
Now let me get content from pages 3-8...
{"doc_name": "report.pdf", "pages": "3-5"}
Perfect! I found the revenue on Page 3...
```

---

## 3. Key UX Patterns Discovered

### Pattern 1: Transparent Reasoning Process
- Shows thinking: "Let me check document structure"
- Shows actions: "Now let me get content from pages X-Y"
- Cites sources: "You can find this on Page 3"
- Builds trust through transparency

### Pattern 2: Streaming Response
- Real-time updates (not wait → show all)
- Interleaved metadata: `{"doc_name": "..."}`, `{"pages": "..."}`
- Feels like human expert walking through document

### Pattern 3: Multi-Turn Context
```python
# First turn
messages=[{"role": "user", "content": "What is revenue?"}]

# Follow-up (maintains context)
messages=[
    {"role": "user", "content": "What is revenue?"},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "What about Q4?"}
]
```

### Pattern 4: Flexible Output Modes

**Mode A: Natural Language (Default)**
```python
chat_completions(messages=[{"role": "user", "content": "What are the conclusions?"}])
# Returns: Conversational answer with page citations
```

**Mode B: JSON Retrieval (Prompted)**
```python
prompt = """
Your job is to retrieve raw relevant content from the document.
Query: {query}
Return in JSON format:
[
  {"page": <number>, "content": "<raw text>"},
  ...
]
"""
chat_completions(messages=[{"role": "user", "content": prompt}])
# Returns: Structured JSON for downstream processing
```

---

## 4. DX Patterns: Simple API Surface

### Document Workflow
```python
# 1. Upload
doc_id = pi_client.submit_document(pdf_path)["doc_id"]

# 2. Check status
doc_info = pi_client.get_document(doc_id)
if doc_info['status'] == 'completed':
    # Ready for queries

# 3. Chat/Query
for chunk in pi_client.chat_completions(..., stream=True):
    print(chunk)
```

**Key Insight**: Only 3 API methods needed for full workflow:
- `submit_document()`
- `get_document()`
- `chat_completions()`

### Additional Utilities
```python
# Get tree structure (for advanced users)
tree = pi_client.get_tree(doc_id, node_summary=True)

# Check if ready for retrieval
is_ready = pi_client.is_retrieval_ready(doc_id)
```

---

## 5. What This Means for Our Implementation

### Architecture Validated ✅
- Tree structure generation (we have this - Phase 2)
- Reasoning-based retrieval (we have this - Phase 3)
- Document management (we have this - Week 2)

### UX Gaps Identified 🚨

| Feature | Status | Priority |
|---------|--------|----------|
| Chat interface | Missing | CRITICAL |
| Streaming responses (SSE) | Missing | CRITICAL |
| Multi-turn context | Missing | HIGH |
| Transparent reasoning display | Missing | HIGH |
| Page citations in UI | Missing | MEDIUM |
| JSON retrieval mode | Have backend, no UI | LOW |

---

## 6. Recommended Plan Updates

### Week 3 REVISED Scope (Chat-First)

**Remove:**
- Query form component (replaced by chat input)
- Static results page (replaced by chat stream)

**Add:**
- Chat interface component (message list + input)
- SSE streaming from FastAPI
- Multi-turn context management (session-based)
- Thinking process display (metadata extraction)
- Page citation links (navigate to document viewer)

**Keep:**
- Document selection (which doc to chat with)
- TanStack Query for state management
- Error handling patterns from Week 2

### Week 4 REVISED Scope (Multi-Document + Advanced)

**Add:**
- Multi-document chat (select multiple docs)
- Tree visualization in sidebar (explorer mode)
- JSON retrieval mode toggle
- Export conversation

---

## 7. Technical Implementation Notes

### Frontend Architecture

**Chat Component Structure:**
```
app/chat/
├── page.tsx (SSR shell, Suspense)
├── ChatClient.tsx (client component)
│   ├── MessageList (display)
│   ├── ChatInput (send)
│   └── ThinkingProcess (metadata)
└── [sessionId]/page.tsx (resume session)
```

**Streaming Pattern:**
```typescript
// SSE connection to FastAPI
const eventSource = new EventSource(`/api/chat/stream?session_id=${sessionId}`)

eventSource.onmessage = (event) => {
  const chunk = JSON.parse(event.data)

  if (chunk.type === 'thinking') {
    // Show "Let me check..."
  } else if (chunk.type === 'metadata') {
    // Show {"doc_name": "...", "pages": "..."}
  } else if (chunk.type === 'content') {
    // Append to current message
  }
}
```

### Backend API Changes

**New Endpoint:**
```python
@router.get("/chat/stream")
async def chat_stream(
    session_id: str,
    message: str,
    doc_ids: list[str]
):
    async def event_generator():
        # Yield thinking
        yield f"data: {json.dumps({'type': 'thinking', 'content': '...'})}\n\n"

        # Yield metadata
        yield f"data: {json.dumps({'type': 'metadata', 'doc': '...'})}\n\n"

        # Yield answer chunks
        for chunk in reasoning_pipeline.stream_answer(...):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

    return EventSourceResponse(event_generator())
```

---

## 8. Key Takeaways

### What Works (From Cookbook Evidence)

1. **Chat is more natural than forms** - users ask follow-ups naturally
2. **Streaming builds trust** - seeing reasoning process reduces "black box" feel
3. **Page citations are critical** - users want to verify sources
4. **Simple API wins** - 3 methods cover 90% of use cases
5. **Flexible output modes** - same backend, different prompts

### What to Avoid

1. ❌ Form-based query UI (too rigid for conversational flow)
2. ❌ Non-streaming responses (feels slow, no feedback)
3. ❌ Single-turn only (limits exploration)
4. ❌ Hidden reasoning (users distrust black boxes)

---

## 9. Next Steps

1. **Update NEXTJS_UI_PLAN.md** to incorporate chat-first approach
2. **Add Week 3 streaming SSE infrastructure**
3. **Redesign Week 3 scope** from query form → chat interface
4. **Keep Week 2 document management** (upload, list, detail - foundational)
5. **Add backend streaming endpoint** (FastAPI SSE)

---

## 10. References

- Cookbook source: `/reference/PageIndex/cookbook/`
- PageIndex Chat: https://chat.pageindex.ai/
- API Docs: https://docs.pageindex.ai/quickstart
- Our backend: Already implements PageIndex tree + retrieval (Phases 2-3)
- Our frontend: Week 1-2 foundation ready for chat UI

---

**Conclusion**: The cookbook validates our backend architecture but reveals our UI should be **chat-first, streaming, and conversational** - not form-based. This is the "magic experience" users expect from modern AI document assistants.
