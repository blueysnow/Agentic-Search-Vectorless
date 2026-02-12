# Next.js 15 UI for Vectorless RAG System

**Date:** February 12, 2026
**Status:** PLANNING
**Backend:** FastAPI (Phase 1-5 COMPLETE, 439/439 tests passing)
**Frontend:** Next.js 15 + React 19 + shadcn/ui

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Vercel Patterns Integration](#3-vercel-patterns-integration)
4. [Project Structure](#4-project-structure)
5. [Core Features](#5-core-features)
6. [Component Architecture](#6-component-architecture)
7. [Backend Integration Strategy](#7-backend-integration-strategy)
8. [Real-Time Streaming](#8-real-time-streaming)
9. [State Management](#9-state-management)
10. [Testing Strategy](#10-testing-strategy)
11. [Build Phases](#11-build-phases)
12. [Performance Targets](#12-performance-targets)
13. [Deployment Strategy](#13-deployment-strategy)
14. [Memory Notes (For Workflow-Final Persistence)](#14-memory-notes-for-workflow-final-persistence)
15. [Router Contract](#15-router-contract)

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

## 2. Technology Stack

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

### 2.2 Backend API Base URL

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

## 3. Vercel Patterns Integration

This section maps **45 Vercel best practices** to our UI implementation. Each component/feature references the specific pattern(s) it follows.

### 3.1 Critical Patterns (MUST IMPLEMENT)

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

### 3.2 High-Impact Patterns (SHOULD IMPLEMENT)

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

### 3.3 Medium-Impact Patterns (NICE TO HAVE)

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

## 4. Project Structure

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

      query/
        page.tsx                   # Query interface
        [sessionId]/
          page.tsx                 # Session detail

      sessions/
        page.tsx                   # Session list
        [id]/
          page.tsx                 # Session detail

    api/
      stream-query/
        route.ts                   # SSE streaming endpoint for queries

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

    query/
      query-input.tsx              # Client: form handling
      message-list.tsx             # Client: streaming updates
      message-item.tsx             # Client: memoized (Pattern 5.2)
      streaming-message.tsx        # Client: SSE consumer

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
    use-query-stream.ts            # SSE streaming hook
    use-sessions.ts                # TanStack Query: sessions
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

### 4.1 File Naming Conventions

- **Server Components**: `component-name.tsx` (default)
- **Client Components**: `component-name.tsx` with `"use client"` directive
- **Hooks**: `use-feature-name.ts`
- **Utils**: `kebab-case.ts`
- **Types**: `types.ts` or `schema.ts`

---

## 5. Core Features

### 5.1 Feature: Document Upload

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

### 5.2 Feature: Query/Chat Interface

**User Story:** As a user, I can ask questions about uploaded documents and receive streaming responses.

**Components:**
- `query/query-input.tsx` (Client)
- `query/message-list.tsx` (Client)
- `query/streaming-message.tsx` (Client)

**Vercel Patterns Applied:**
- **Pattern 4.1**: Deduplicate scroll event listeners
- **Pattern 5.2**: Memoize message items
- **Pattern 5.7**: Use transitions for input debouncing

**Flow:**
```
1. User types query, selects document
2. POST /api/query with documentId + query
3. Backend streams response via SSE
4. Client appends chunks to message content
5. Display retrieval trace (nodes visited, reasoning path)
```

**Implementation:**

```tsx
// hooks/use-query-stream.ts
'use client'

import { useState, useEffect, useRef } from 'react'

export function useQueryStream(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const sendQuery = async (query: string, documentId: string) => {
    setIsStreaming(true)

    // Close existing stream
    eventSourceRef.current?.close()

    // Open new SSE stream
    const url = `/api/stream-query?sessionId=${sessionId}&documentId=${documentId}&query=${encodeURIComponent(query)}`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    let currentMessage = { id: Date.now(), role: 'assistant', content: '' }
    setMessages(prev => [...prev, currentMessage])

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'chunk') {
        currentMessage.content += data.content
        setMessages(prev => [...prev.slice(0, -1), { ...currentMessage }])
      } else if (data.type === 'done') {
        setIsStreaming(false)
        eventSource.close()
      }
    }

    eventSource.onerror = () => {
      setIsStreaming(false)
      eventSource.close()
    }
  }

  useEffect(() => {
    return () => eventSourceRef.current?.close()
  }, [])

  return { messages, isStreaming, sendQuery }
}
```

```tsx
// app/api/stream-query/route.ts
import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const query = searchParams.get('query')
  const documentId = searchParams.get('documentId')
  const sessionId = searchParams.get('sessionId')

  if (!query || !documentId) {
    return new Response('Missing parameters', { status: 400 })
  }

  // Create SSE stream
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Call FastAPI backend
        const res = await fetch(`${process.env.API_URL}/api/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, documentId, sessionId }),
        })

        if (!res.ok) throw new Error('Query failed')
        if (!res.body) throw new Error('No response body')

        const reader = res.body.getReader()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          // Forward chunk to client
          const chunk = new TextDecoder().decode(value)
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: 'chunk', content: chunk })}\n\n`)
          )
        }

        // Signal completion
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`)
        )
        controller.close()
      } catch (error) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'error', message: error.message })}\n\n`)
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

### 5.3 Feature: Session History

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

### 5.4 Feature: Document Library

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

## 6. Component Architecture

### 6.1 shadcn/ui Components

Install shadcn/ui CLI:

```bash
npx shadcn@latest init
```

Components to install:

```bash
npx shadcn@latest add button card dialog input textarea
npx shadcn@latest add dropdown-menu toast tooltip accordion
npx shadcn@latest add skeleton badge separator progress
```

### 6.2 Custom Component Patterns

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

### 6.3 Error Boundaries

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

## 7. Backend Integration Strategy

### 7.1 API Client (Client-Side)

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

### 7.2 API Server Functions (Server-Side with React.cache)

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

### 7.3 Type Definitions

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

## 8. Real-Time Streaming

### 8.1 SSE vs WebSocket Decision

**Choice:** Server-Sent Events (SSE)

**Rationale:**
- Unidirectional (server → client) fits LLM streaming
- Browser-native, no library needed
- Simpler than WebSocket for this use case
- Automatic reconnection handling
- Works over HTTP (no upgrade protocol)

### 8.2 SSE Implementation

**Pattern 1.5 Applied:** Stream response chunks to client while maintaining UI responsiveness.

```tsx
// hooks/use-query-stream.ts (detailed in Feature 5.2 above)
```

### 8.3 Fallback for SSE Unavailable

```tsx
// hooks/use-query-stream.ts
export function useQueryStream(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  const sendQuery = async (query: string, documentId: string) => {
    // Check if SSE is supported
    if (typeof EventSource === 'undefined') {
      // Fallback: polling
      return sendQueryWithPolling(query, documentId)
    }

    // Standard SSE implementation
    // ...
  }

  const sendQueryWithPolling = async (query: string, documentId: string) => {
    // POST query, get sessionId, poll GET /api/sessions/{id} every 1s
    // ...
  }

  return { messages, isStreaming, sendQuery }
}
```

---

## 9. State Management

### 9.1 State Architecture

**Philosophy:** Minimize client state, leverage server state.

```
Server State (TanStack Query):
  - Documents list
  - Document details
  - Sessions list
  - Session details

Client State (React Context):
  - Current session ID
  - UI preferences (theme, sidebar collapsed)
  - Toast notifications

Ephemeral State (useState):
  - Form inputs
  - Modal open/close
  - Streaming message buffer
```

### 9.2 TanStack Query Setup

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

### 9.3 Context for UI State

```tsx
// lib/context/session-context.tsx
'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

interface SessionContextValue {
  currentSessionId: string | null
  setCurrentSessionId: (id: string | null) => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  return (
    <SessionContext.Provider value={{ currentSessionId, setCurrentSessionId }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be within SessionProvider')
  return context
}
```

---

## 10. Testing Strategy

### 10.1 Test Coverage Goals

- **Unit tests**: 80%+ coverage for hooks, utilities
- **Component tests**: All interactive client components
- **Integration tests**: Key user flows (upload → query → view)
- **E2E tests**: Critical paths (full upload-to-answer flow)

### 10.2 Vitest for Unit/Component Tests

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

### 10.3 Playwright for E2E Tests

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

### 10.4 Testing Checklist

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

## 11. Build Phases

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

### Phase 3: Query Interface & Streaming (Week 3)

**Goal:** Build real-time query interface with SSE streaming.

**Deliverables:**
- [ ] Query input form with document selector
- [ ] SSE streaming hook (`use-query-stream.ts`)
- [ ] Message list with streaming updates
- [ ] Memoized message items (Pattern 5.2)
- [ ] Retrieval trace visualization
- [ ] Session persistence (create new session, continue existing)
- [ ] Error handling for streaming failures
- [ ] Fallback to polling if SSE unavailable

**Acceptance Criteria:**
- Select document, enter query, submit
- See streaming response chunks in real-time
- View retrieval trace (nodes visited, reasoning depth)
- Messages persist in session
- Can resume session from history

**Vercel Patterns Applied:**
- **1.5**: Streaming with Suspense
- **4.1**: Deduplicate scroll event listeners
- **5.2**: Memoize message items
- **5.7**: Transitions for input debouncing

### Phase 4: Session History (Week 4)

**Goal:** View and explore past conversations.

**Deliverables:**
- [ ] Session list page (Server Component)
- [ ] Session detail page with turn timeline
- [ ] Turn-by-turn retrieval trace viewer
- [ ] Session filters (by document, date range)
- [ ] Export session as JSON/Markdown
- [ ] Delete session functionality
- [ ] TanStack Query hooks: `useSessions`, `useSession`

**Acceptance Criteria:**
- View list of past sessions
- Click session → see full conversation
- Expand turn → see retrieval trace
- Filter sessions by document
- Export session data

**Vercel Patterns Applied:**
- **1.4**: Promise.all() for parallel session fetching
- **3.4**: React.cache() for session deduplication
- **6.2**: content-visibility for long turn lists

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

## 12. Performance Targets

### 12.1 Lighthouse Scores (Mobile)

- **Performance**: 90+
- **Accessibility**: 95+
- **Best Practices**: 100
- **SEO**: 90+

### 12.2 Core Web Vitals

- **LCP (Largest Contentful Paint)**: < 2.5s
- **FID (First Input Delay)**: < 100ms
- **CLS (Cumulative Layout Shift)**: < 0.1

### 12.3 Bundle Size Targets

- **Initial JS bundle**: < 200KB (gzipped)
- **Total page weight**: < 1MB (first load)
- **Document list page**: < 150KB JS
- **Query interface page**: < 180KB JS (including SSE logic)

### 12.4 Runtime Performance

- **Document list render**: < 200ms (50 documents)
- **Query input latency**: < 50ms (keystroke to UI update)
- **SSE chunk latency**: < 100ms (backend chunk to DOM update)
- **Page transitions**: < 300ms (navigate between routes)

---

## 13. Deployment Strategy

### 13.1 Vercel Configuration

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

### 13.2 Environment Variables

**Local (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Vercel (Production):**
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### 13.3 Deployment Pipeline

```
1. Developer pushes to `main` branch
2. GitHub Actions runs tests (unit + E2E)
3. If tests pass → Vercel deploys to staging (preview URL)
4. Manual QA on staging
5. Merge to `production` branch → Vercel deploys to production
6. Post-deployment smoke tests
7. Monitor Vercel Analytics + Sentry for errors
```

### 13.4 Backend Coordination

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

## 14. Memory Notes (For Workflow-Final Persistence)

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
1. Setup & Foundation (Week 1)
2. Document Management (Week 2)
3. Query Interface & Streaming (Week 3)
4. Session History (Week 4)
5. Polish & Optimization (Week 5)
6. Testing & Deployment (Week 6)

---

## 15. Router Contract

### 15.1 Plan Status

**Plan File:** `docs/plans/NEXTJS_UI_PLAN.md`
**Status:** READY_FOR_REVIEW
**Blocking Issues:** None
**Backend Dependency:** FastAPI (Phases 1-5 COMPLETE, 439/439 tests)

### 15.2 Plan Approval Request

**To:** team-lead
**From:** planner (UI)
**Subject:** Next.js UI Plan Ready for Review

**Plan Summary:**
- Next.js 15 + React 19 UI for vectorless RAG system
- 45 Vercel patterns referenced throughout plan
- RSC-first architecture with strategic client components
- SSE streaming for real-time LLM responses
- TanStack Query + React.cache() for data fetching
- 6-week build plan with clear phases and acceptance criteria

**Key Highlights:**
- **Pattern Integration**: All critical Vercel patterns (1.1, 1.4, 1.5, 2.1, 2.4, 3.4, 4.2, 5.2) explicitly referenced
- **Performance First**: Bundle size < 200KB, LCP < 2.5s, Lighthouse 90+
- **Backend Integration**: Comprehensive strategy for FastAPI integration (REST + SSE)
- **Testing Strategy**: 80%+ coverage with Vitest + Playwright
- **Deployment**: Vercel-optimized with edge runtime

**Approval Needed:**
- [ ] Architecture approved (RSC vs client component boundaries)
- [ ] Vercel patterns sufficiently integrated
- [ ] Backend integration strategy validated
- [ ] Build phases realistic (6 weeks)
- [ ] Performance targets achievable

**Next Steps After Approval:**
1. Spawn builder agent with Week 1 tasks
2. Update memory (activeContext.md) with UI phase start
3. Begin Phase 1: Project Setup & Foundation

---

**Plan Status:** ✅ COMPLETE
**Task 2:** ✅ COMPLETED
**Awaiting:** Plan approval from team-lead
