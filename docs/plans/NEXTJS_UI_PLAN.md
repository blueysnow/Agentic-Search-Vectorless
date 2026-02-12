# Next.js 15 UI for Vectorless RAG System

**Date:** February 12, 2026
**Last Updated:** February 12, 2026 (Chat-first revision)
**Status:** WEEK 1-2 COMPLETE, WEEK 3-4 READY
**Backend:** FastAPI (Phase 1-5 COMPLETE, 439/439 tests passing)
**Frontend:** Next.js 15 + React 19 + shadcn/ui
**Research Reference:** `docs/research/2026-02-12-pageindex-cookbook-patterns.md`

---

## 🎯 Key Update: Chat-First Architecture (Week 3-4 Revised)

This plan has been updated to incorporate **chat-first streaming patterns** from the PageIndex cookbook, replacing the original form-based query interface with a conversational design.

**What Changed:**
- ❌ **REMOVED**: Query form → Submit → Results page
- ✅ **ADDED**: Chat interface with real-time streaming
- ✅ **ADDED**: Transparent reasoning display ("Let me check...")
- ✅ **ADDED**: Multi-turn conversation context
- ✅ **ADDED**: Page citations with click navigation
- ✅ **ADDED**: Multi-document chat support

**Inspired By:** PageIndex Chat (https://chat.pageindex.ai/)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [PageIndex UX Patterns](#2-pageindex-ux-patterns)
3. [Technology Stack](#3-technology-stack)
4. [Vercel Patterns Integration](#4-vercel-patterns-integration)
5. [Project Structure](#5-project-structure)
6. [Core Features](#6-core-features)
7. [Component Architecture](#7-component-architecture)
8. [Backend Integration Strategy](#8-backend-integration-strategy)
9. [Real-Time Streaming](#9-real-time-streaming)
10. [State Management](#10-state-management)
11. [Testing Strategy](#11-testing-strategy)
12. [Build Phases](#12-build-phases)
13. [Performance Targets](#13-performance-targets)
14. [Deployment Strategy](#14-deployment-strategy)
15. [Memory Notes (For Workflow-Final Persistence)](#15-memory-notes-for-workflow-final-persistence)
16. [Router Contract](#16-router-contract)

---

## 1. Architecture Overview

### 1.1 System Context

The Next.js UI is the **presentation layer** for the vectorless RAG system. The backend (FastAPI) handles:
- Document ingestion (PDF/Markdown → MongoDB tree structure)
- Retrieval pipeline (Atlas Search + Tree Navigation + LLM reasoning)
- Session management (multi-turn conversations)

The UI provides:
- Document upload interface
- Real-time query/chat interface with streaming
- Session history visualization
- Document library management

### 1.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | Next.js 15 (App Router) | RSC, Suspense, streaming, Vercel deployment |
| **React Version** | React 19 | Server Components, `use()` hook, improved Suspense |
| **Styling** | Tailwind CSS + shadcn/ui | Consistency, accessibility, fast development |
| **Data Fetching** | TanStack Query v5 | Client-side caching, deduplication, retry logic |
| **Real-time** | Server-Sent Events (SSE) | Browser-native, simpler than WebSocket for unidirectional streaming |
| **State Management** | React Context + TanStack Query | Minimal client state, leverage server state |
| **Forms** | React Hook Form + Zod | Type-safe validation, performance |
| **Icons** | lucide-react (direct imports) | **Vercel Pattern 2.1**: avoid barrel imports |
| **Deployment** | Vercel | Optimal Next.js performance, edge runtime |

### 1.3 Client vs Server Component Strategy

**Vercel Pattern 3.2**: Minimize serialization at RSC boundaries

```
Server Components (default):
  - Layout shells (sidebar, header, footer)
  - Document list pages
  - Session history pages
  - Static content

Client Components ("use client"):
  - File upload form (file input handling)
  - Query input (real-time validation, streaming UI)
  - Chat message list (streaming updates, scroll behavior)
  - Interactive filters and search
```

**RSC Boundary Rule**: Pass only **primitives** and **serializable data** across RSC boundaries. Never pass functions, class instances, or DOM elements.

---

## 2. PageIndex UX Patterns

### 2.1 Research Source

**Reference:** `docs/research/2026-02-12-pageindex-cookbook-patterns.md`
**Cookbook Location:** `/reference/PageIndex/cookbook/`
**Live Demo:** https://chat.pageindex.ai/

### 2.2 Core UX Patterns Adopted

#### Pattern 1: Transparent Reasoning Process

**Why:** Builds user trust by showing the AI's thinking process.

**Implementation:**
```
User: "What is the revenue?"

AI Response (streamed):
→ "Let me check document structure..."
   [metadata: {"doc_name": "report.pdf"}]
→ "Now looking at pages 3-5..."
   [metadata: {"pages": "3-5"}]
→ "Perfect! The revenue for Q4 2024 is $2.5M."
   [citation: Page 3]
```

**Components:**
- `ThinkingProcess.tsx` - Displays reasoning steps in muted text
- `metadata` chunks shown as info badges

#### Pattern 2: Real-Time Streaming (Not Wait-Then-Show)

**Why:** Feels like human expert walking through document, not loading spinner.

**Implementation:**
- SSE chunks appear immediately as they arrive
- Word-by-word streaming (not sentence-by-sentence)
- Thinking steps interleaved with content
- No "loading..." state - show partial content

**Hook:** `useChatStream()` with chunk type routing

#### Pattern 3: Multi-Turn Conversational Context

**Why:** Users naturally ask follow-up questions.

**Implementation:**
```typescript
// Turn 1
messages: [{ role: "user", content: "What is revenue?" }]

// Turn 2 (maintains context)
messages: [
  { role: "user", content: "What is revenue?" },
  { role: "assistant", content: "Revenue is $2.5M" },
  { role: "user", content: "What about Q4?" }, // No need to repeat context
]
```

**Backend:** Session stores full conversation history
**Frontend:** MessageList displays all turns in chronological order

#### Pattern 4: Page Citations (Trust Through Verification)

**Why:** Users want to verify sources, not trust blindly.

**Implementation:**
- Citations embedded in answer: "You can find this on Page 3"
- Clickable badges link to document viewer
- Cite page number + snippet of text

**Component:** `PageCitation.tsx`
```tsx
<PageCitation
  page={3}
  text="Q4 revenue: $2.5M"
  onClick={() => navigateToDocument(docId, page: 3)}
/>
```

#### Pattern 5: Flexible Output Modes

**Why:** Different use cases need different formats.

**Modes:**
1. **Natural Language (Default)**: Conversational answer with citations
2. **JSON Retrieval (Prompt-Driven)**: Structured data for downstream processing

**Implementation:**
```typescript
// Mode A: Natural language
sendMessage("What are the conclusions?", [docId])
// Returns: "The main conclusion is..."

// Mode B: JSON retrieval (via prompt)
const prompt = `
Your job is to retrieve raw relevant content from the document.
Query: ${userQuery}
Return in JSON format:
[
  {"page": <number>, "content": "<raw text>"},
  ...
]
`
sendMessage(prompt, [docId])
// Returns: [{"page": 3, "content": "..."}]
```

### 2.3 Design Philosophy

**From PageIndex:**
- **"Show, don't hide"**: Expose reasoning, don't black-box it
- **"Stream, don't wait"**: Real-time feedback > loading spinners
- **"Cite, don't assert"**: Every claim backed by page reference
- **"Converse, don't query"**: Multi-turn dialogue > one-shot Q&A

**Applied to Our UI:**
- Chat-first interface (not form-based)
- Thinking steps visible by default (collapsible)
- Citations integrated into answer flow
- Multi-document support from day 1

---

## 3. Technology Stack

### 2.1 Core Dependencies

```json
{
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.6.0",

    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-query-devtools": "^5.62.0",

    "tailwindcss": "^3.4.0",
    "@radix-ui/react-accordion": "^1.2.2",
    "@radix-ui/react-dialog": "^1.1.4",
    "@radix-ui/react-dropdown-menu": "^2.1.4",
    "@radix-ui/react-toast": "^1.2.4",
    "@radix-ui/react-tooltip": "^1.1.6",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.6.0",

    "lucide-react": "^0.460.0",
    "react-hook-form": "^7.54.0",
    "zod": "^3.24.0",

    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "eslint": "^9.17.0",
    "eslint-config-next": "^15.1.0",
    "prettier": "^3.4.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.5.0",
    "@playwright/test": "^1.49.0"
  }
}
```

### 3.2 Backend API Base URL

```typescript
// lib/config.ts
export const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  endpoints: {
    documents: '/api/documents',
    query: '/api/query',
    sessions: '/api/sessions',
  },
  timeouts: {
    upload: 300000,    // 5 min for large PDF uploads
    query: 60000,      // 1 min for streaming queries
    default: 10000,    // 10s for standard requests
  },
} as const
```

---

## 4. Vercel Patterns Integration

This section maps **45 Vercel best practices** to our UI implementation. Each component/feature references the specific pattern(s) it follows.

### 4.1 Critical Patterns (MUST IMPLEMENT)

#### Pattern 1.1: Defer Await Until Needed
**Applied to:** Document list loading, session history

```tsx
// app/documents/page.tsx
async function DocumentsPage({ searchParams }: PageProps) {
  // Don't await if user is filtering by status
  if (searchParams.filter === 'pending') {
    // Fast path: only fetch pending documents
    const pending = await fetchPendingDocuments()
    return <DocumentList documents={pending} />
  }

  // Full fetch only when needed
  const allDocuments = await fetchAllDocuments()
  return <DocumentList documents={allDocuments} />
}
```

#### Pattern 1.4: Promise.all() for Independent Operations
**Applied to:** Dashboard data loading

```tsx
// app/dashboard/page.tsx
async function Dashboard() {
  // Fetch stats, recent docs, recent sessions in parallel
  const [stats, recentDocs, recentSessions] = await Promise.all([
    fetchStats(),
    fetchRecentDocuments({ limit: 5 }),
    fetchRecentSessions({ limit: 5 }),
  ])

  return (
    <div>
      <StatsCards stats={stats} />
      <RecentActivity docs={recentDocs} sessions={recentSessions} />
    </div>
  )
}
```

#### Pattern 1.5: Strategic Suspense Boundaries
**Applied to:** Every page with data fetching

```tsx
// app/sessions/[id]/page.tsx
function SessionPage({ params }: PageProps) {
  return (
    <div className="container">
      <SessionHeader /> {/* Static, renders immediately */}

      <Suspense fallback={<SessionSkeleton />}>
        <SessionContent sessionId={params.id} /> {/* Async RSC */}
      </Suspense>

      <Footer /> {/* Static, renders immediately */}
    </div>
  )
}

async function SessionContent({ sessionId }: { sessionId: string }) {
  const session = await fetchSession(sessionId) // Only blocks this component
  return <SessionDetail session={session} />
}
```

#### Pattern 2.1: Avoid Barrel File Imports
**Applied to:** All icon imports

```tsx
// WRONG:
import { Check, X, Menu, Upload, Search } from 'lucide-react'
// Loads 1,583 modules, 200-800ms cold start penalty

// CORRECT:
import Check from 'lucide-react/dist/esm/icons/check'
import X from 'lucide-react/dist/esm/icons/x'
import Menu from 'lucide-react/dist/esm/icons/menu'
import Upload from 'lucide-react/dist/esm/icons/upload'
import Search from 'lucide-react/dist/esm/icons/search'
// Loads only 5 modules, ~2KB vs ~1MB
```

**Alternative:** Use Next.js 15's `optimizePackageImports`:

```js
// next.config.js
module.exports = {
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
}
```

#### Pattern 2.4: Dynamic Imports for Heavy Components
**Applied to:** PDF viewer, streaming message renderer

```tsx
// components/pdf-viewer.tsx (heavy, ~200KB)
import dynamic from 'next/dynamic'

const PDFViewer = dynamic(() => import('./pdf-viewer-impl'), {
  ssr: false, // PDF.js requires browser APIs
  loading: () => <PDFSkeleton />,
})

export default PDFViewer
```

#### Pattern 3.4: Per-Request Deduplication with React.cache()
**Applied to:** Server-side document fetching

```tsx
// lib/api/server.ts
import { cache } from 'react'

export const fetchDocument = cache(async (documentId: string) => {
  const res = await fetch(`${API_CONFIG.baseUrl}/api/documents/${documentId}`)
  if (!res.ok) throw new Error('Document not found')
  return res.json()
})

// Usage across multiple RSCs in same request:
// app/documents/[id]/page.tsx
async function DocumentPage({ params }) {
  const doc = await fetchDocument(params.id) // Fetch 1
  return <DocumentDetail doc={doc} />
}

// components/document-sidebar.tsx
async function DocumentSidebar({ documentId }) {
  const doc = await fetchDocument(documentId) // Fetch 2 (deduplicated!)
  return <Sidebar nodes={doc.totalNodes} />
}
```

#### Pattern 4.2: Use SWR/TanStack Query for Client-Side Deduplication
**Applied to:** Client-side data fetching

```tsx
// hooks/use-documents.ts
import { useQuery } from '@tanstack/react-query'

export function useDocuments(filters?: DocumentFilters) {
  return useQuery({
    queryKey: ['documents', filters],
    queryFn: () => fetchDocuments(filters),
    staleTime: 30_000, // Consider fresh for 30s
    refetchOnWindowFocus: true,
  })
}

// Multiple components calling useDocuments() with same filters:
// Only ONE network request is made!
```

#### Pattern 5.2: Extract to Memoized Components
**Applied to:** Message list items

```tsx
// components/chat/message-item.tsx
import { memo } from 'react'

export const MessageItem = memo(function MessageItem({ message }: Props) {
  // Expensive markdown rendering
  const rendered = useMemo(
    () => renderMarkdown(message.content),
    [message.content]
  )

  return <div>{rendered}</div>
})

// Parent re-renders won't re-render MessageItem if message prop unchanged
```

### 4.2 High-Impact Patterns (SHOULD IMPLEMENT)

#### Pattern 3.3: Parallel Data Fetching with Component Composition
**Applied to:** Document detail page

```tsx
// app/documents/[id]/page.tsx
function DocumentDetailPage({ params }: PageProps) {
  return (
    <div>
      <Suspense fallback={<HeaderSkeleton />}>
        <DocumentHeader documentId={params.id} />
      </Suspense>

      <Suspense fallback={<TreeSkeleton />}>
        <DocumentTree documentId={params.id} />
      </Suspense>

      <Suspense fallback={<SessionsSkeleton />}>
        <RelatedSessions documentId={params.id} />
      </Suspense>
    </div>
  )
}

// Each component fetches independently in parallel!
async function DocumentHeader({ documentId }) {
  const doc = await fetchDocument(documentId)
  return <Header {...doc} />
}

async function DocumentTree({ documentId }) {
  const tree = await fetchDocumentTree(documentId)
  return <Tree nodes={tree} />
}

async function RelatedSessions({ documentId }) {
  const sessions = await fetchDocumentSessions(documentId)
  return <SessionsList sessions={sessions} />
}
```

#### Pattern 5.7: Use Transitions for Non-Urgent Updates
**Applied to:** Search filtering

```tsx
// components/document-search.tsx
'use client'

import { useTransition } from 'react'

export function DocumentSearch() {
  const [isPending, startTransition] = useTransition()
  const router = useRouter()
  const searchParams = useSearchParams()

  const handleSearch = (value: string) => {
    startTransition(() => {
      const params = new URLSearchParams(searchParams)
      if (value) {
        params.set('q', value)
      } else {
        params.delete('q')
      }
      router.replace(`/documents?${params.toString()}`)
    })
  }

  return (
    <div>
      <input
        type="search"
        onChange={(e) => handleSearch(e.target.value)}
        className={isPending ? 'opacity-50' : ''}
      />
      {isPending && <Spinner />}
    </div>
  )
}
```

#### Pattern 6.3: Hoist Static JSX Elements
**Applied to:** Chat message structure

```tsx
// WRONG: Avatar re-created on every render
function Message({ content }: Props) {
  return (
    <div>
      <div className="avatar">
        <UserIcon size={24} />
      </div>
      <div>{content}</div>
    </div>
  )
}

// CORRECT: Avatar hoisted outside component
const AVATAR_ELEMENT = (
  <div className="avatar">
    <UserIcon size={24} />
  </div>
)

function Message({ content }: Props) {
  return (
    <div>
      {AVATAR_ELEMENT}
      <div>{content}</div>
    </div>
  )
}
```

### 4.3 Medium-Impact Patterns (NICE TO HAVE)

#### Pattern 2.5: Preload Based on User Intent
**Applied to:** Document hover preloading

```tsx
// components/document-card.tsx
'use client'

import { useRouter } from 'next/navigation'

export function DocumentCard({ document }: Props) {
  const router = useRouter()

  const handleMouseEnter = () => {
    // Preload document detail page on hover
    router.prefetch(`/documents/${document.id}`)
  }

  return (
    <Link
      href={`/documents/${document.id}`}
      onMouseEnter={handleMouseEnter}
      onFocus={handleMouseEnter}
    >
      <Card>{document.name}</Card>
    </Link>
  )
}
```

#### Pattern 7.11: Use Set/Map for O(1) Lookups
**Applied to:** Session turn deduplication

```tsx
// hooks/use-session-updates.ts
function useSessionUpdates(sessionId: string) {
  const [turns, setTurns] = useState<Turn[]>([])
  const seenTurnsRef = useRef(new Set<string>())

  const addTurn = (turn: Turn) => {
    if (seenTurnsRef.current.has(turn.id)) return
    seenTurnsRef.current.add(turn.id)
    setTurns(prev => [...prev, turn])
  }

  return { turns, addTurn }
}
```

---

## 5. Project Structure

```
frontend/                          # Next.js app (separate from backend)
  app/
    (auth)/                        # Route group for auth pages
      login/
      signup/

    (dashboard)/                   # Route group for authenticated pages
      layout.tsx                   # Dashboard layout (sidebar + header)
      page.tsx                     # Dashboard home

      documents/
        page.tsx                   # Document list (RSC)
        [id]/
          page.tsx                 # Document detail (RSC)
          layout.tsx               # Document detail layout

      chat/
        page.tsx                   # Chat interface (new session)
        [sessionId]/
          page.tsx                 # Resume existing conversation

      sessions/
        page.tsx                   # Session list
        [id]/
          page.tsx                 # Session detail

    api/
      chat/
        stream/
          route.ts                 # SSE streaming endpoint for chat

    layout.tsx                     # Root layout
    page.tsx                       # Landing page
    providers.tsx                  # TanStack Query provider

  components/
    ui/                            # shadcn/ui components
      button.tsx
      card.tsx
      dialog.tsx
      input.tsx
      skeleton.tsx
      toast.tsx
      ...

    documents/
      document-card.tsx            # Client: hover preload (Pattern 2.5)
      document-list.tsx            # Server: data fetching
      document-upload-form.tsx     # Client: file input
      pdf-viewer.tsx               # Client: dynamic import (Pattern 2.4)

    chat/
      chat-client.tsx              # Client: main container
      message-list.tsx             # Client: scrollable history
      message-item.tsx             # Client: memoized (Pattern 5.2)
      chat-input.tsx               # Client: input with send
      thinking-process.tsx         # Client: reasoning steps display
      page-citation.tsx            # Client: clickable page refs
      document-selector.tsx        # Client: multi-doc picker
      message-skeleton.tsx         # Client: streaming placeholder
      conversation-export.tsx      # Client: export as JSON/MD

    sessions/
      session-card.tsx
      session-detail.tsx
      turn-timeline.tsx

    layout/
      sidebar.tsx                  # Server: static navigation
      header.tsx                   # Server: user menu
      footer.tsx                   # Server: static

  hooks/
    use-documents.ts               # TanStack Query: documents
    use-chat-stream.ts             # SSE streaming hook
    use-scroll-anchor.ts           # Auto-scroll to bottom
    use-sessions.ts                # TanStack Query: sessions
    use-conversation-export.ts     # Export conversation logic
    use-toast.ts                   # Toast notifications

  lib/
    api/
      client.ts                    # Client-side fetch wrapper
      server.ts                    # Server-side fetch with React.cache()
      types.ts                     # Backend API types

    utils/
      cn.ts                        # Tailwind merge utility
      date.ts                      # Date formatting
      validation.ts                # Zod schemas

    config.ts                      # API config

  public/
    icons/
    images/

  styles/
    globals.css                    # Tailwind base + custom styles

  tests/
    components/                    # Vitest component tests
    e2e/                           # Playwright E2E tests

  .env.local                       # NEXT_PUBLIC_API_URL
  next.config.js                   # optimizePackageImports
  tailwind.config.ts
  tsconfig.json
  package.json
```

### 5.1 File Naming Conventions

- **Server Components**: `component-name.tsx` (default)
- **Client Components**: `component-name.tsx` with `"use client"` directive
- **Hooks**: `use-feature-name.ts`
- **Utils**: `kebab-case.ts`
- **Types**: `types.ts` or `schema.ts`

---

## 6. Core Features

### 6.1 Feature: Document Upload

**User Story:** As a user, I can upload a PDF or Markdown file and track ingestion progress.

**Components:**
- `documents/document-upload-form.tsx` (Client)
- `documents/upload-progress.tsx` (Client)

**Vercel Patterns Applied:**
- **Pattern 2.4**: Dynamic import for file validation library
- **Pattern 5.6**: Lazy state init for large file preview

**Flow:**
```
1. User selects file (PDF/Markdown, max 50MB)
2. Client validates: file type, size, not duplicate
3. POST /api/documents with multipart/form-data
4. Poll GET /api/documents/{id} for status every 2s
5. Display progress: processing → completed (with tree stats)
```

**Implementation:**

```tsx
// documents/document-upload-form.tsx
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'

const uploadSchema = z.object({
  file: z.instanceof(File)
    .refine(file => file.size <= 50 * 1024 * 1024, 'Max 50MB')
    .refine(
      file => ['application/pdf', 'text/markdown'].includes(file.type),
      'Only PDF or Markdown'
    ),
  domain: z.string().optional(),
})

export function DocumentUploadForm() {
  const queryClient = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(uploadSchema),
  })

  const mutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const res = await fetch('/api/documents', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error('Upload failed')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      toast({ title: 'Document uploaded', description: 'Processing...' })
    },
  })

  const onSubmit = (data: { file: File; domain?: string }) => {
    const formData = new FormData()
    formData.append('file', data.file)
    if (data.domain) formData.append('domain', data.domain)
    mutation.mutate(formData)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input type="file" {...register('file')} accept=".pdf,.md" />
      {errors.file && <ErrorText>{errors.file.message}</ErrorText>}

      <Input placeholder="Domain (optional)" {...register('domain')} />

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? <Spinner /> : 'Upload'}
      </Button>
    </form>
  )
}
```

### 6.2 Feature: Chat Interface with Streaming

**User Story:** As a user, I can have a conversation with my documents through a chat interface that shows real-time streaming responses with transparent reasoning.

**Components:**
- `chat/chat-client.tsx` (Client) - Main chat container
- `chat/message-list.tsx` (Client) - Scrollable message history
- `chat/chat-input.tsx` (Client) - Message input with document selector
- `chat/message-item.tsx` (Client) - Individual message display (memoized)
- `chat/thinking-process.tsx` (Client) - Shows LLM reasoning steps
- `chat/page-citation.tsx` (Client) - Clickable page references

**Vercel Patterns Applied:**
- **Pattern 4.1**: Deduplicate scroll event listeners
- **Pattern 5.2**: Memoize message items
- **Pattern 5.7**: Use transitions for input debouncing
- **Pattern 6.3**: Hoist static JSX for avatars

**Flow:**
```
1. User selects document(s) to chat with
2. User types message in chat input
3. POST /api/chat/stream with sessionId + message + docIds
4. Backend streams response via SSE with multiple chunk types:
   - type: 'thinking' → "Let me check document structure..."
   - type: 'metadata' → {"doc_name": "report.pdf", "pages": "3-5"}
   - type: 'content' → Answer text chunks
   - type: 'citation' → {"page": 3, "text": "..."}
5. Client renders chunks in real-time:
   - Thinking steps shown in muted text
   - Metadata displayed as info badges
   - Content streamed word-by-word
   - Citations become clickable links
6. Conversation history persisted in session
7. User can ask follow-up questions with full context
```

**Key UX Patterns from PageIndex Cookbook:**
- **Transparent Reasoning**: Show thinking process ("Let me check...", "Now looking at pages...")
- **Real-time Streaming**: Chunks appear immediately, not wait-then-show-all
- **Page Citations**: "You can find this on Page 3" with click → document viewer
- **Multi-turn Context**: Maintains conversation history in messages array
- **Flexible Output**: Natural language (default) OR JSON retrieval (prompt-driven)

**Implementation:**

```tsx
// hooks/use-chat-stream.ts
'use client'

import { useState, useEffect, useRef } from 'react'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string[]  // Array of reasoning steps
  metadata?: Record<string, any>  // Document metadata, pages accessed
  citations?: Array<{ page: number; text: string }>
  timestamp: number
}

interface StreamChunk {
  type: 'thinking' | 'metadata' | 'content' | 'citation' | 'done' | 'error'
  content?: string
  data?: any
}

export function useChatStream(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const currentMessageRef = useRef<ChatMessage | null>(null)

  const sendMessage = async (message: string, documentIds: string[]) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMessage])

    setIsStreaming(true)

    // Close existing stream
    eventSourceRef.current?.close()

    // Initialize assistant message
    currentMessageRef.current = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      thinking: [],
      citations: [],
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, currentMessageRef.current!])

    // Open new SSE stream
    const params = new URLSearchParams({
      sessionId,
      message,
      documentIds: documentIds.join(','),
    })
    const url = `/api/chat/stream?${params.toString()}`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      const chunk: StreamChunk = JSON.parse(event.data)
      const current = currentMessageRef.current!

      switch (chunk.type) {
        case 'thinking':
          // Add thinking step (e.g., "Let me check document structure...")
          current.thinking = [...(current.thinking || []), chunk.content!]
          break

        case 'metadata':
          // Store metadata (doc_name, pages accessed, etc.)
          current.metadata = { ...current.metadata, ...chunk.data }
          break

        case 'content':
          // Append content chunk to message
          current.content += chunk.content
          break

        case 'citation':
          // Add page citation
          current.citations = [...(current.citations || []), chunk.data]
          break

        case 'done':
          setIsStreaming(false)
          eventSource.close()
          return

        case 'error':
          console.error('Stream error:', chunk.content)
          current.content += '\n\n[Error: ' + chunk.content + ']'
          setIsStreaming(false)
          eventSource.close()
          return
      }

      // Trigger re-render with updated message
      setMessages(prev => [...prev.slice(0, -1), { ...current }])
    }

    eventSource.onerror = () => {
      setIsStreaming(false)
      eventSource.close()
    }
  }

  useEffect(() => {
    return () => eventSourceRef.current?.close()
  }, [])

  return { messages, isStreaming, sendMessage }
}
```

```tsx
// components/chat/chat-client.tsx
'use client'

import { useState } from 'react'
import { useChatStream } from '@/hooks/use-chat-stream'
import { MessageList } from './message-list'
import { ChatInput } from './chat-input'
import { DocumentSelector } from './document-selector'

export function ChatClient({ sessionId }: { sessionId: string }) {
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const { messages, isStreaming, sendMessage } = useChatStream(sessionId)

  const handleSend = (message: string) => {
    if (!message.trim() || selectedDocIds.length === 0) return
    sendMessage(message, selectedDocIds)
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="border-b p-4">
        <DocumentSelector
          selectedIds={selectedDocIds}
          onChange={setSelectedDocIds}
        />
      </div>

      <MessageList messages={messages} className="flex-1 overflow-y-auto" />

      <ChatInput
        onSend={handleSend}
        disabled={isStreaming || selectedDocIds.length === 0}
        placeholder={
          selectedDocIds.length === 0
            ? 'Select a document to start chatting...'
            : 'Ask a question...'
        }
      />
    </div>
  )
}
```

```tsx
// components/chat/message-item.tsx (Pattern 5.2: Memoized)
'use client'

import { memo } from 'react'
import { ChatMessage } from '@/hooks/use-chat-stream'
import { ThinkingProcess } from './thinking-process'
import { PageCitation } from './page-citation'

// Pattern 6.3: Hoist static avatars
const USER_AVATAR = (
  <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
    <span className="text-white text-sm">U</span>
  </div>
)

const ASSISTANT_AVATAR = (
  <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
    <span className="text-white text-sm">AI</span>
  </div>
)

export const MessageItem = memo(function MessageItem({
  message,
}: {
  message: ChatMessage
}) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 p-4 ${isUser ? 'bg-gray-50' : ''}`}>
      {isUser ? USER_AVATAR : ASSISTANT_AVATAR}

      <div className="flex-1 space-y-2">
        {/* Thinking steps (assistant only) */}
        {!isUser && message.thinking && message.thinking.length > 0 && (
          <ThinkingProcess steps={message.thinking} />
        )}

        {/* Main content */}
        <div className="prose prose-sm">
          {message.content || <span className="text-gray-400">Thinking...</span>}
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.citations.map((citation, idx) => (
              <PageCitation
                key={idx}
                page={citation.page}
                text={citation.text}
                documentId={message.metadata?.doc_id}
              />
            ))}
          </div>
        )}

        {/* Metadata badges */}
        {message.metadata && (
          <div className="flex gap-2 text-xs text-gray-500">
            {message.metadata.doc_name && (
              <span className="px-2 py-1 bg-gray-100 rounded">
                {message.metadata.doc_name}
              </span>
            )}
            {message.metadata.pages && (
              <span className="px-2 py-1 bg-gray-100 rounded">
                Pages: {message.metadata.pages}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
})
```

```tsx
// app/api/chat/stream/route.ts
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const message = searchParams.get('message')
  const documentIds = searchParams.get('documentIds')?.split(',') || []
  const sessionId = searchParams.get('sessionId')

  if (!message || documentIds.length === 0) {
    return new Response('Missing parameters', { status: 400 })
  }

  // Create SSE stream
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Call FastAPI backend chat endpoint
        const res = await fetch(`${process.env.API_URL}/api/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            document_ids: documentIds,
            session_id: sessionId,
          }),
        })

        if (!res.ok) throw new Error('Chat request failed')
        if (!res.body) throw new Error('No response body')

        const reader = res.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          // Backend sends newline-delimited JSON chunks
          const lines = decoder.decode(value).split('\n')

          for (const line of lines) {
            if (!line.trim()) continue

            try {
              const chunk = JSON.parse(line)

              // Forward chunk to client
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`)
              )
            } catch (e) {
              console.error('Failed to parse chunk:', line)
            }
          }
        }

        // Signal completion
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`)
        )
        controller.close()
      } catch (error) {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ type: 'error', content: error.message })}\n\n`
          )
        )
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
```

**Backend API Contract (FastAPI):**

```python
# POST /api/chat/stream
# Request body:
{
  "message": "What is the revenue?",
  "document_ids": ["doc_123"],
  "session_id": "session_456"  # optional
}

# Response: Newline-delimited JSON chunks
{"type": "thinking", "content": "Let me check document structure..."}
{"type": "metadata", "data": {"doc_name": "report.pdf", "doc_id": "doc_123"}}
{"type": "thinking", "content": "Now looking at pages 3-5..."}
{"type": "metadata", "data": {"pages": "3-5"}}
{"type": "content", "content": "The revenue for Q4 2024 is "}
{"type": "content", "content": "$2.5 million. "}
{"type": "citation", "data": {"page": 3, "text": "Q4 revenue: $2.5M"}}
{"type": "content", "content": "You can find this on Page 3."}
{"type": "done"}
```

### 6.3 Feature: Session History

**User Story:** As a user, I can view past conversations with retrieval traces.

**Components:**
- `sessions/session-list.tsx` (Server)
- `sessions/session-detail.tsx` (Server/Client hybrid)
- `sessions/turn-timeline.tsx` (Client)

**Vercel Patterns Applied:**
- **Pattern 1.5**: Suspense boundaries for session list
- **Pattern 3.4**: React.cache() for session fetching
- **Pattern 6.2**: content-visibility for long turn lists

**Implementation:**

```tsx
// app/sessions/page.tsx (Server Component)
async function SessionsPage() {
  return (
    <div>
      <h1>Sessions</h1>
      <Suspense fallback={<SessionListSkeleton />}>
        <SessionList />
      </Suspense>
    </div>
  )
}

async function SessionList() {
  const sessions = await fetchSessions() // Cached
  return (
    <div>
      {sessions.map(session => (
        <SessionCard key={session.id} session={session} />
      ))}
    </div>
  )
}
```

### 6.4 Feature: Document Library

**User Story:** As a user, I can browse uploaded documents with filters and search.

**Components:**
- `documents/document-list.tsx` (Server)
- `documents/document-card.tsx` (Client: hover preload)
- `documents/document-filters.tsx` (Client)

**Vercel Patterns Applied:**
- **Pattern 2.5**: Preload on hover/focus
- **Pattern 5.7**: Transitions for filter updates

**Implementation:**

```tsx
// app/documents/page.tsx (Server Component)
async function DocumentsPage({ searchParams }: PageProps) {
  const filters = {
    status: searchParams.status,
    domain: searchParams.domain,
    q: searchParams.q,
  }

  return (
    <div>
      <DocumentFilters initialFilters={filters} /> {/* Client */}
      <Suspense fallback={<DocumentListSkeleton />}>
        <DocumentList filters={filters} /> {/* Server */}
      </Suspense>
    </div>
  )
}

async function DocumentList({ filters }: { filters: DocumentFilters }) {
  const documents = await fetchDocuments(filters)

  return (
    <div className="grid grid-cols-3 gap-4">
      {documents.map(doc => (
        <DocumentCard key={doc.id} document={doc} />
      ))}
    </div>
  )
}
```

---

## 7. Component Architecture

### 7.1 shadcn/ui Components

Install shadcn/ui CLI:

```bash
npx shadcn@latest init
```

Components to install:

```bash
npx shadcn@latest add button card dialog input textarea
npx shadcn@latest add dropdown-menu toast tooltip accordion
npx shadcn@latest add skeleton badge separator progress
npx shadcn@latest add avatar scroll-area tabs
```

### 7.2 Chat Component Architecture

**Chat-first design pattern from PageIndex cookbook:**

```
app/chat/
├── page.tsx                   # SSR shell with Suspense
├── [sessionId]/
│   └── page.tsx               # Resume existing session
└── layout.tsx                 # Chat layout with document selector

components/chat/
├── chat-client.tsx            # Main container (Client)
├── message-list.tsx           # Scrollable history (Client)
├── message-item.tsx           # Individual message (Client, memoized)
├── chat-input.tsx             # Input with send button (Client)
├── thinking-process.tsx       # Shows reasoning steps (Client)
├── page-citation.tsx          # Clickable page reference (Client)
├── document-selector.tsx      # Multi-document picker (Client)
├── message-skeleton.tsx       # Loading state for streaming
└── conversation-export.tsx    # Export chat as JSON/MD (Client)

hooks/
├── use-chat-stream.ts         # SSE streaming management
├── use-scroll-anchor.ts       # Auto-scroll to bottom
└── use-conversation-export.ts # Export conversation logic
```

**Key Patterns:**
- **ChatClient**: Container component, manages session state
- **MessageList**: Pattern 6.2 (content-visibility) for long lists
- **MessageItem**: Pattern 5.2 (memoized), Pattern 6.3 (hoisted avatars)
- **ThinkingProcess**: Collapsible accordion showing reasoning steps
- **PageCitation**: Click → navigate to document viewer at specific page

### 7.3 Custom Component Patterns

#### Pattern: Server Component with Suspense

```tsx
// components/documents/document-tree.tsx (Server Component)
import { Suspense } from 'react'

export async function DocumentTree({ documentId }: Props) {
  const tree = await fetchDocumentTree(documentId)

  return (
    <div>
      <h2>Document Structure</h2>
      <TreeView nodes={tree.nodes} />
    </div>
  )
}

// Wrap in Suspense at call site:
<Suspense fallback={<TreeSkeleton />}>
  <DocumentTree documentId={id} />
</Suspense>
```

#### Pattern: Client Component with TanStack Query

```tsx
// components/documents/document-stats.tsx (Client Component)
'use client'

import { useQuery } from '@tanstack/react-query'

export function DocumentStats({ documentId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['document-stats', documentId],
    queryFn: () => fetchDocumentStats(documentId),
  })

  if (isLoading) return <Skeleton />

  return (
    <div>
      <Stat label="Nodes" value={data.totalNodes} />
      <Stat label="Pages" value={data.totalPages} />
      <Stat label="Tokens" value={data.totalTokens} />
    </div>
  )
}
```

### 7.4 Error Boundaries

```tsx
// components/error-boundary.tsx (Client Component)
'use client'

import { Component, ReactNode } from 'react'

export class ErrorBoundary extends Component<
  { children: ReactNode; fallback: (error: Error) => ReactNode },
  { error: Error | null }
> {
  state = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return this.props.fallback(this.state.error)
    }
    return this.props.children
  }
}

// Usage:
<ErrorBoundary fallback={(error) => <ErrorCard error={error} />}>
  <DocumentList />
</ErrorBoundary>
```

---

## 8. Backend Integration Strategy

### 8.1 API Client (Client-Side)

```tsx
// lib/api/client.ts
import { API_CONFIG } from '../config'

class APIClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = API_CONFIG.baseUrl
  }

  async fetch<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${res.status}`)
    }

    return res.json()
  }

  // Documents
  async uploadDocument(formData: FormData) {
    return this.fetch('/api/documents', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    })
  }

  async getDocuments(filters?: DocumentFilters) {
    const params = new URLSearchParams(filters as Record<string, string>)
    return this.fetch(`/api/documents?${params}`)
  }

  async getDocument(id: string) {
    return this.fetch(`/api/documents/${id}`)
  }

  // Sessions
  async getSessions(params?: { documentId?: string; limit?: number }) {
    const query = new URLSearchParams(params as Record<string, string>)
    return this.fetch(`/api/sessions?${query}`)
  }

  async getSession(id: string) {
    return this.fetch(`/api/sessions/${id}`)
  }
}

export const apiClient = new APIClient()
```

### 8.2 API Server Functions (Server-Side with React.cache)

```tsx
// lib/api/server.ts
import { cache } from 'react'
import { API_CONFIG } from '../config'

export const fetchDocument = cache(async (documentId: string) => {
  const res = await fetch(`${API_CONFIG.baseUrl}/api/documents/${documentId}`, {
    next: { revalidate: 60 }, // Cache for 60s
  })

  if (!res.ok) throw new Error('Document not found')
  return res.json()
})

export const fetchDocuments = cache(async (filters?: DocumentFilters) => {
  const params = new URLSearchParams(filters as Record<string, string>)
  const res = await fetch(`${API_CONFIG.baseUrl}/api/documents?${params}`, {
    next: { revalidate: 30 },
  })

  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
})

export const fetchSession = cache(async (sessionId: string) => {
  const res = await fetch(`${API_CONFIG.baseUrl}/api/sessions/${sessionId}`, {
    next: { revalidate: 10 }, // Sessions update frequently
  })

  if (!res.ok) throw new Error('Session not found')
  return res.json()
})
```

### 8.3 Type Definitions

```tsx
// lib/api/types.ts
export interface Document {
  documentId: string
  name: string
  type: 'pdf' | 'markdown'
  domain?: string
  description?: string
  totalPages: number
  totalNodes: number
  totalTokens: number
  rootNodeId?: string
  ingestion: {
    status: 'pending' | 'processing' | 'completed' | 'failed'
    model?: string
    startedAt?: string
    completedAt?: string
    errors: string[]
  }
  createdAt: string
  updatedAt: string
}

export interface Session {
  sessionId: string
  documentId?: string
  userId?: string
  turns: Turn[]
  createdAt: string
  updatedAt: string
}

export interface Turn {
  turnNumber: number
  query: string
  retrievalTrace: {
    atlasSearchHits: Array<{ nodeId: string; score: number }>
    treeNavigationPath: string[]
    nodesRead: string[]
    totalNodesVisited: number
    reasoningDepth: number
  }
  answer?: string
  model?: string
  latencyMs: number
  timestamp: string
}

export interface DocumentFilters {
  status?: 'pending' | 'processing' | 'completed' | 'failed'
  domain?: string
  q?: string
}
```

---

## 9. Real-Time Streaming

### 9.1 SSE vs WebSocket Decision

**Choice:** Server-Sent Events (SSE)

**Rationale:**
- Unidirectional (server → client) fits LLM streaming
- Browser-native, no library needed
- Simpler than WebSocket for this use case
- Automatic reconnection handling
- Works over HTTP (no upgrade protocol)

### 9.2 SSE Streaming Architecture

**Pattern 1.5 Applied:** Stream response chunks to client while maintaining UI responsiveness.

**Chunk Types (from PageIndex pattern):**

```typescript
// Thinking step (transparent reasoning)
{ type: 'thinking', content: 'Let me check document structure...' }

// Metadata (document context)
{ type: 'metadata', data: { doc_name: 'report.pdf', pages: '3-5' } }

// Content chunk (answer text)
{ type: 'content', content: 'The revenue is ' }

// Citation (page reference)
{ type: 'citation', data: { page: 3, text: 'Q4 revenue: $2.5M' } }

// Completion signal
{ type: 'done' }

// Error handling
{ type: 'error', content: 'Failed to retrieve data' }
```

**Implementation:**

```tsx
// hooks/use-chat-stream.ts (detailed in Feature 5.2 above)
```

**Key Features:**
- **Multi-chunk types**: thinking, metadata, content, citation, done, error
- **Real-time updates**: Each chunk triggers immediate UI update
- **Transparent reasoning**: Users see thinking process as it happens
- **Graceful errors**: Errors displayed inline, stream closes cleanly
- **Auto-reconnect**: EventSource handles reconnection automatically

### 9.3 Auto-scroll and UX Polish

**Auto-scroll behavior (Pattern 4.1: event listener deduplication):**

```tsx
// hooks/use-scroll-anchor.ts
import { useEffect, useRef } from 'react'

export function useScrollAnchor() {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  })

  return messagesEndRef
}

// Usage in MessageList:
export function MessageList({ messages }: Props) {
  const messagesEndRef = useScrollAnchor()

  return (
    <div className="overflow-y-auto">
      {messages.map(msg => <MessageItem key={msg.id} message={msg} />)}
      <div ref={messagesEndRef} />
    </div>
  )
}
```

### 9.4 Fallback for SSE Unavailable

```tsx
// hooks/use-chat-stream.ts
export function useChatStream(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  const sendMessage = async (message: string, documentIds: string[]) => {
    // Check if SSE is supported
    if (typeof EventSource === 'undefined') {
      // Fallback: polling
      return sendMessageWithPolling(message, documentIds)
    }

    // Standard SSE implementation
    // ...
  }

  const sendMessageWithPolling = async (
    message: string,
    documentIds: string[]
  ) => {
    // POST message, get turnId, poll GET /api/sessions/{sessionId}/turns/{turnId}
    const res = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, documentIds, sessionId }),
    })
    const { turnId } = await res.json()

    // Poll for completion
    const pollInterval = setInterval(async () => {
      const turn = await fetch(`/api/sessions/${sessionId}/turns/${turnId}`)
      const data = await turn.json()

      if (data.status === 'completed') {
        clearInterval(pollInterval)
        setMessages(prev => [...prev, data.message])
      }
    }, 1000)
  }

  return { messages, isStreaming, sendMessage }
}
```

---

## 10. State Management

### 10.1 State Architecture

**Philosophy:** Minimize client state, leverage server state.

```
Server State (TanStack Query):
  - Documents list
  - Document details
  - Sessions list
  - Session details (conversation history)

Client State (React Context):
  - Current session ID
  - Selected document IDs for chat
  - UI preferences (theme, sidebar collapsed)
  - Toast notifications

Ephemeral State (useState):
  - Chat input text
  - Modal open/close
  - Streaming message buffer (thinking steps, citations)
  - Scroll position
```

**Conversation Context Management:**

Multi-turn conversations require maintaining message history:

```typescript
// lib/context/conversation-context.tsx
'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

interface ConversationContextValue {
  currentSessionId: string | null
  setCurrentSessionId: (id: string | null) => void
  selectedDocumentIds: string[]
  setSelectedDocumentIds: (ids: string[]) => void
  messages: ChatMessage[]
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
}

const ConversationContext = createContext<ConversationContextValue | null>(null)

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const addMessage = (message: ChatMessage) => {
    setMessages(prev => [...prev, message])
  }

  const clearMessages = () => {
    setMessages([])
  }

  return (
    <ConversationContext.Provider
      value={{
        currentSessionId,
        setCurrentSessionId,
        selectedDocumentIds,
        setSelectedDocumentIds,
        messages,
        addMessage,
        clearMessages,
      }}
    >
      {children}
    </ConversationContext.Provider>
  )
}

export function useConversation() {
  const context = useContext(ConversationContext)
  if (!context) throw new Error('useConversation must be within ConversationProvider')
  return context
}
```

### 10.2 TanStack Query Setup

```tsx
// app/providers.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  // Pattern 5.6: Lazy state init for QueryClient
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000, // 30s
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### 10.3 Multi-Turn Context Management

**Key Pattern from PageIndex:** Maintain messages array for conversation context

```tsx
// Backend API maintains full conversation history
POST /api/chat/stream
{
  "message": "What about Q4?",  // Current question
  "document_ids": ["doc_123"],
  "session_id": "session_456",   // Links to conversation history
}

// Backend retrieves previous turns from session:
// Turn 1: "What is revenue?" → "Revenue is $2.5M"
// Turn 2: "What about Q4?" → [uses context from Turn 1]
```

**Frontend Context Hydration:**

```tsx
// app/chat/[sessionId]/page.tsx (Resume existing session)
async function ChatPage({ params }: { params: { sessionId: string } }) {
  // Fetch existing session messages
  const session = await fetchSession(params.sessionId)

  return (
    <Suspense fallback={<ChatSkeleton />}>
      <ChatClient
        sessionId={params.sessionId}
        initialMessages={session.turns.map(turn => ({
          id: turn.id,
          role: 'user',
          content: turn.query,
          timestamp: turn.timestamp,
        }))}
      />
    </Suspense>
  )
}
```

**Client-side context tracking:**

```tsx
// hooks/use-chat-stream.ts
export function useChatStream(sessionId: string, initialMessages: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)

  // Messages array maintains full conversation history
  // Backend receives sessionId to retrieve context server-side
  // Frontend displays full history in MessageList
}
```

---

## 11. Testing Strategy

### 11.1 Test Coverage Goals

- **Unit tests**: 80%+ coverage for hooks, utilities
- **Component tests**: All interactive client components
- **Integration tests**: Key user flows (upload → query → view)
- **E2E tests**: Critical paths (full upload-to-answer flow)

### 11.2 Vitest for Unit/Component Tests

```tsx
// tests/components/query-input.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryInput } from '@/components/query/query-input'
import { describe, it, expect, vi } from 'vitest'

describe('QueryInput', () => {
  it('calls onSubmit with query text', () => {
    const onSubmit = vi.fn()
    render(<QueryInput onSubmit={onSubmit} />)

    const input = screen.getByPlaceholderText('Ask a question...')
    fireEvent.change(input, { target: { value: 'What is ROE?' } })

    const button = screen.getByRole('button', { name: 'Send' })
    fireEvent.click(button)

    expect(onSubmit).toHaveBeenCalledWith('What is ROE?')
  })

  it('disables submit when streaming', () => {
    render(<QueryInput onSubmit={vi.fn()} isStreaming={true} />)

    const button = screen.getByRole('button', { name: 'Send' })
    expect(button).toBeDisabled()
  })
})
```

### 11.3 Playwright for E2E Tests

```tsx
// tests/e2e/upload-and-query.spec.ts
import { test, expect } from '@playwright/test'

test('upload document and query', async ({ page }) => {
  await page.goto('http://localhost:3000/documents')

  // Upload document
  await page.click('text=Upload Document')
  await page.setInputFiles('input[type="file"]', './fixtures/test.pdf')
  await page.click('button:has-text("Upload")')

  // Wait for processing
  await page.waitForSelector('text=completed', { timeout: 60000 })

  // Navigate to query
  await page.click('text=Query')
  await page.fill('input[placeholder="Ask a question..."]', 'What is the main topic?')
  await page.click('button:has-text("Send")')

  // Wait for streaming response
  await page.waitForSelector('[data-testid="streaming-message"]')
  await page.waitForSelector('text=The main topic', { timeout: 30000 })

  expect(await page.textContent('[data-testid="message-content"]')).toContain('topic')
})
```

### 11.4 Testing Checklist

- [ ] Unit tests for all hooks
- [ ] Component tests for interactive UI
- [ ] SSE streaming tests (mock EventSource)
- [ ] Error boundary tests
- [ ] Form validation tests (Zod schemas)
- [ ] TanStack Query cache invalidation tests
- [ ] E2E: upload → processing → completed
- [ ] E2E: query → streaming → answer displayed
- [ ] E2E: session history navigation

---

## 12. Build Phases

### Phase 1: Project Setup & Foundation (Week 1)

**Goal:** Scaffold Next.js app with core dependencies and design system.

**Deliverables:**
- [ ] Initialize Next.js 15 project with TypeScript
- [ ] Install and configure Tailwind CSS
- [ ] Install shadcn/ui and core components
- [ ] Set up TanStack Query with providers
- [ ] Create base layout (sidebar, header, footer)
- [ ] Implement routing structure (dashboard, documents, query, sessions)
- [ ] Configure `next.config.js` with `optimizePackageImports` (Pattern 2.1)
- [ ] Set up API client utilities (client.ts, server.ts)
- [ ] Define TypeScript types for backend API
- [ ] Create placeholder pages (Home, Dashboard, Documents, Query, Sessions)

**Acceptance Criteria:**
- App runs locally on http://localhost:3000
- All routes accessible with placeholder content
- Tailwind + shadcn/ui components render correctly
- TanStack Query devtools visible in dev mode

**Vercel Patterns Applied:**
- **2.1**: optimizePackageImports for lucide-react
- **3.4**: React.cache() setup in server.ts

### Phase 2: Document Management (Week 2)

**Goal:** Implement document upload, list, and detail pages.

**Deliverables:**
- [ ] Document upload form with file validation (Pattern 5.6: lazy state init)
- [ ] Document list page (Server Component with Suspense - Pattern 1.5)
- [ ] Document card with hover preload (Pattern 2.5)
- [ ] Document detail page with tree visualization
- [ ] Document filters (status, domain, search)
- [ ] Upload progress tracking (polling backend)
- [ ] Error handling for failed uploads
- [ ] TanStack Query hooks: `useDocuments`, `useDocument`

**Acceptance Criteria:**
- Upload PDF/Markdown (max 50MB)
- View document list with filters
- Click document card → detail page
- See document tree structure
- Track ingestion status (pending → processing → completed)

**Vercel Patterns Applied:**
- **1.5**: Suspense boundaries for document list
- **2.5**: Preload on hover/focus
- **3.3**: Parallel data fetching with component composition
- **5.6**: Lazy state initialization for file preview

### Phase 3: Chat Interface & Streaming (Week 3) - REVISED

**Goal:** Build chat-first interface with transparent streaming reasoning (PageIndex pattern).

**Context:** This phase replaces the original query form approach with a conversational chat interface based on PageIndex cookbook patterns.

**Deliverables:**
- [ ] Chat page layout (`app/chat/page.tsx`)
- [ ] ChatClient component with document selector
- [ ] SSE streaming hook (`use-chat-stream.ts`) with multi-chunk support:
  - `type: 'thinking'` - reasoning steps
  - `type: 'metadata'` - document context
  - `type: 'content'` - answer chunks
  - `type: 'citation'` - page references
- [ ] MessageList component with auto-scroll
- [ ] Memoized MessageItem (Pattern 5.2)
- [ ] ThinkingProcess component (collapsible accordion)
- [ ] PageCitation component (clickable links)
- [ ] ChatInput with multi-document selector
- [ ] Session creation and persistence
- [ ] Error handling for streaming failures
- [ ] Backend SSE endpoint (`/api/chat/stream`)

**Acceptance Criteria:**
- Select one or multiple documents
- Type message and send
- See thinking steps appear in real-time ("Let me check...")
- See metadata badges (doc name, pages accessed)
- See answer stream word-by-word
- Click page citation → navigate to document viewer
- Messages persist in session
- Auto-scroll to latest message
- Can start new conversation or continue existing

**Vercel Patterns Applied:**
- **1.5**: Streaming with Suspense
- **4.1**: Deduplicate scroll event listeners
- **5.2**: Memoize message items
- **5.7**: Transitions for input debouncing
- **6.3**: Hoist static JSX (avatars)

**Tests Required:**
- [ ] SSE stream handles all chunk types correctly
- [ ] Multi-turn context maintained in session
- [ ] Thinking steps display/collapse correctly
- [ ] Citations link to correct document pages
- [ ] Auto-scroll works during streaming
- [ ] Error messages display inline
- [ ] Polling fallback works when SSE unavailable

### Phase 4: Multi-Document Chat & Conversation Export (Week 4) - REVISED

**Goal:** Advanced chat features: multi-document conversations and export capabilities.

**Context:** This phase extends Week 3's chat interface with multi-document support and conversation management features.

**Deliverables:**
- [ ] Multi-document selector with visual indicators
- [ ] Document switcher in chat (add/remove docs mid-conversation)
- [ ] Conversation export:
  - Export as Markdown (human-readable)
  - Export as JSON (structured data)
  - Include thinking steps and citations
- [ ] Session history page (list all conversations)
- [ ] Resume session from history
- [ ] Delete conversation functionality
- [ ] Session filters (by document, date range)
- [ ] Session detail page with full conversation replay
- [ ] Retrieval trace visualization (tree navigation path)
- [ ] TanStack Query hooks: `useSessions`, `useSession`

**Acceptance Criteria:**
- Select multiple documents in chat
- Add/remove documents during conversation
- Backend retrieves from all selected documents
- Export conversation maintains formatting
- View list of past sessions with previews
- Click session → resume conversation
- Filter sessions by documents used
- See retrieval trace for each turn
- Delete unwanted sessions

**Vercel Patterns Applied:**
- **1.4**: Promise.all() for parallel session fetching
- **3.4**: React.cache() for session deduplication
- **6.2**: content-visibility for long turn lists
- **7.11**: Use Set/Map for document ID lookups

**Tests Required:**
- [ ] Multi-document queries retrieve from all docs
- [ ] Export generates valid Markdown/JSON
- [ ] Session list filters work correctly
- [ ] Resume session loads conversation history
- [ ] Retrieval trace displays tree path correctly
- [ ] Delete session removes data from backend

### Phase 5: Polish & Optimization (Week 5)

**Goal:** Performance optimization, accessibility, and production readiness.

**Deliverables:**
- [ ] Implement loading skeletons for all Suspense boundaries
- [ ] Add toast notifications for all actions
- [ ] Improve error messages and error boundaries
- [ ] Accessibility audit (keyboard navigation, ARIA labels, color contrast)
- [ ] Performance audit (Lighthouse, bundle analysis)
- [ ] Optimize images and icons (Pattern 2.1: direct imports)
- [ ] Add animations for state transitions
- [ ] Implement dark mode (optional)
- [ ] Documentation: README, component storybook

**Acceptance Criteria:**
- Lighthouse score: Performance 90+, Accessibility 95+
- All interactive elements keyboard-accessible
- Bundle size < 200KB (main chunk)
- No console errors or warnings
- Error boundaries catch and display all errors gracefully

**Vercel Patterns Applied:**
- **2.4**: Dynamic imports for heavy components (PDF viewer)
- **6.3**: Hoist static JSX elements
- **6.7**: Explicit conditional rendering
- **7.11**: Use Set/Map for O(1) lookups

### Phase 6: Testing & Deployment (Week 6)

**Goal:** Comprehensive testing and production deployment.

**Deliverables:**
- [ ] Unit tests for all hooks (Vitest)
- [ ] Component tests for interactive UI
- [ ] E2E tests for critical paths (Playwright)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Environment variable management (.env.local, Vercel env vars)
- [ ] Deploy to Vercel staging
- [ ] Load testing (simulate 50 concurrent users)
- [ ] Deploy to Vercel production
- [ ] Monitoring setup (Vercel Analytics, Sentry)

**Acceptance Criteria:**
- 80%+ test coverage
- All E2E tests pass
- Staging deployment successful
- Load test: 50 concurrent users, no errors
- Production deployment successful
- Monitoring dashboards live

---

## 13. Performance Targets

### 13.1 Lighthouse Scores (Mobile)

- **Performance**: 90+
- **Accessibility**: 95+
- **Best Practices**: 100
- **SEO**: 90+

### 13.2 Core Web Vitals

- **LCP (Largest Contentful Paint)**: < 2.5s
- **FID (First Input Delay)**: < 100ms
- **CLS (Cumulative Layout Shift)**: < 0.1

### 13.3 Bundle Size Targets

- **Initial JS bundle**: < 200KB (gzipped)
- **Total page weight**: < 1MB (first load)
- **Document list page**: < 150KB JS
- **Query interface page**: < 180KB JS (including SSE logic)

### 13.4 Runtime Performance

- **Document list render**: < 200ms (50 documents)
- **Query input latency**: < 50ms (keystroke to UI update)
- **SSE chunk latency**: < 100ms (backend chunk to DOM update)
- **Page transitions**: < 300ms (navigate between routes)

---

## 14. Deployment Strategy

### 14.1 Vercel Configuration

```js
// vercel.json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api-url-production"
  },
  "build": {
    "env": {
      "NEXT_PUBLIC_API_URL": "@api-url-production"
    }
  }
}
```

### 14.2 Environment Variables

**Local (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Vercel (Production):**
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### 14.3 Deployment Pipeline

```
1. Developer pushes to `main` branch
2. GitHub Actions runs tests (unit + E2E)
3. If tests pass → Vercel deploys to staging (preview URL)
4. Manual QA on staging
5. Merge to `production` branch → Vercel deploys to production
6. Post-deployment smoke tests
7. Monitor Vercel Analytics + Sentry for errors
```

### 14.4 Backend Coordination

**Assumption:** FastAPI backend is deployed separately (not on Vercel).

**CORS Configuration Required:**

FastAPI backend must allow CORS from Next.js domain:

```python
# backend: src/api/server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",          # Local Next.js dev
        "https://yourdomain.vercel.app",  # Vercel preview
        "https://yourdomain.com",         # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 15. Memory Notes (For Workflow-Final Persistence)

**MEMORY_OWNER: lead**

### Key Decisions
- **Framework**: Next.js 15 + React 19 (App Router, RSC, Suspense)
- **Styling**: Tailwind CSS + shadcn/ui (accessible, fast)
- **Data Fetching**: TanStack Query v5 (client caching) + React.cache() (server deduplication)
- **Real-Time**: Server-Sent Events (SSE) for LLM streaming
- **State**: Minimal client state, leverage server state
- **Icons**: lucide-react with direct imports (Pattern 2.1)
- **Deployment**: Vercel (optimal Next.js performance)

### Vercel Patterns Applied
- **Critical Patterns (MUST)**: 1.1, 1.4, 1.5, 2.1, 2.4, 3.4, 4.2, 5.2
- **High-Impact Patterns (SHOULD)**: 3.3, 5.7, 6.3
- **Medium-Impact Patterns (NICE)**: 2.5, 7.11

### Project Structure
- **Server Components**: Layout shells, document list, session list (default)
- **Client Components**: Forms, streaming UI, interactive filters ("use client")
- **RSC Boundary**: Only primitives across server/client boundary
- **API Integration**: Client-side (TanStack Query) + Server-side (React.cache())

### Performance Targets
- Lighthouse: 90+ Performance, 95+ Accessibility
- LCP < 2.5s, FID < 100ms, CLS < 0.1
- Initial bundle < 200KB gzipped
- SSE chunk latency < 100ms

### Testing
- Unit: Vitest (hooks, utilities)
- Component: Testing Library (interactive UI)
- E2E: Playwright (upload → query → answer)
- Coverage: 80%+

### Build Phases
1. Setup & Foundation (Week 1) - COMPLETE
2. Document Management (Week 2) - COMPLETE
3. Chat Interface & Streaming (Week 3) - REVISED to chat-first pattern
4. Multi-Document Chat & Export (Week 4) - REVISED with advanced features
5. Polish & Optimization (Week 5)
6. Testing & Deployment (Week 6)

### PageIndex Cookbook Integration (Week 3-4)
- **Chat-first interface** (not form-based query)
- **Transparent reasoning** (thinking steps visible)
- **Streaming SSE** (real-time chunks)
- **Multi-turn context** (conversation history)
- **Page citations** (clickable references)
- **Flexible output modes** (natural language + JSON)

---

## 16. Router Contract

### 16.1 Plan Status

**Plan File:** `docs/plans/NEXTJS_UI_PLAN.md`
**Status:** READY_FOR_REVIEW
**Blocking Issues:** None
**Backend Dependency:** FastAPI (Phases 1-5 COMPLETE, 439/439 tests)

### 16.2 Plan Update Summary (2026-02-12)

**Update Type:** MAJOR REVISION - Chat-first architecture
**Research Source:** `docs/research/2026-02-12-pageindex-cookbook-patterns.md`
**Updated By:** planner agent (Task #2)

**What Changed:**

1. **Section 5.2 (Core Features)** - REVISED
   - Replaced query form pattern with chat interface
   - Added multi-chunk SSE streaming (thinking, metadata, content, citation)
   - Added PageIndex-inspired UX patterns

2. **Section 6 (Component Architecture)** - EXPANDED
   - New chat component structure
   - Added: ChatClient, ThinkingProcess, PageCitation, DocumentSelector
   - Updated: MessageList, MessageItem with streaming support

3. **Section 8 (Real-Time Streaming)** - ENHANCED
   - Multi-chunk type SSE protocol defined
   - Transparent reasoning display pattern
   - Auto-scroll behavior added

4. **Section 9 (State Management)** - EXPANDED
   - Added conversation context management
   - Multi-turn message history tracking
   - Session hydration for resumed conversations

5. **Section 11 (Build Phases)** - REDESIGNED
   - **Week 3 (REVISED)**: Chat Interface & Streaming (was: Query Form)
     - Chat-first UI with streaming reasoning
     - ThinkingProcess, PageCitation components
     - Multi-chunk SSE implementation
   - **Week 4 (REVISED)**: Multi-Document Chat & Export (was: Session History)
     - Multi-document selector
     - Conversation export (MD/JSON)
     - Session management

**Key Patterns Added:**
- Transparent reasoning display (thinking steps)
- Real-time streaming chunks (not wait-then-show)
- Page citations with click navigation
- Multi-turn context preservation
- Flexible output modes (natural language + JSON)

**Weeks 1-2 Status:**
- Week 1: Foundation - COMPLETE (20 tests passing)
- Week 2: Document Management - COMPLETE (64 tests passing)
- NO CHANGES to Weeks 1-2 (already built and verified)

**Backend API Contract Added:**
- `POST /api/chat/stream` endpoint specification
- Newline-delimited JSON chunk protocol
- Multi-chunk types: thinking, metadata, content, citation, done, error

---

**Plan Status:** ✅ UPDATED
**Task 2:** ✅ COMPLETED
**Status:** READY FOR WEEK 3 IMPLEMENTATION
