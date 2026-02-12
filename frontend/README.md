# Vectorless RAG UI

Next.js 15 + React 19 frontend for the Vectorless RAG system with PageIndex Trees.

## Technology Stack

- **Framework**: Next.js 15 (App Router, React Server Components)
- **React**: React 19
- **Styling**: Tailwind CSS + shadcn/ui
- **Data Fetching**: TanStack Query v5 (client) + React.cache() (server)
- **Forms**: React Hook Form + Zod
- **Icons**: lucide-react (optimized imports)
- **Testing**: Vitest + Testing Library

## Project Structure

```
frontend/
  app/
    dashboard/        # Dashboard home
    documents/        # Document management
    query/            # Query interface
    sessions/         # Session history
    layout.tsx        # Root layout
    page.tsx          # Landing page
    providers.tsx     # TanStack Query provider
    globals.css       # Tailwind styles

  components/
    ui/               # shadcn/ui components (to be added)

  lib/
    api/
      client.ts       # Client-side API wrapper
      server.ts       # Server-side with React.cache()
      types.ts        # TypeScript types for backend
    utils/
      cn.ts           # Class name utility
    config.ts         # API configuration

  tests/              # Vitest tests
```

## Getting Started

### Install Dependencies

```bash
npm install
```

### Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Testing

```bash
# Run tests once
npm test

# Watch mode
npm run test:watch

# UI mode
npm run test:ui
```

### Build

```bash
npm run build
npm start
```

## Vercel Patterns Applied

This project implements performance best practices from Vercel:

### Critical Patterns (MUST)

- **Pattern 2.1**: Direct imports for lucide-react via `optimizePackageImports`
- **Pattern 3.4**: React.cache() for server-side request deduplication
- **Pattern 5.6**: Lazy state initialization for QueryClient

### To Be Implemented (Week 2-6)

- **Pattern 1.4**: Promise.all() for parallel data fetching
- **Pattern 1.5**: Strategic Suspense boundaries
- **Pattern 2.4**: Dynamic imports for heavy components
- **Pattern 5.2**: Memoized components for expensive renders
- **Pattern 5.7**: Transitions for non-urgent updates

## Backend Integration

The UI connects to the FastAPI backend at `http://localhost:8000`:

- `POST /api/documents` - Upload documents
- `GET /api/documents` - List documents
- `GET /api/documents/{id}` - Get document details
- `POST /api/query` - Query with streaming (SSE)
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}` - Get session details

## Week 1 Status

**Deliverables Complete (10/10):**

- [x] Initialize Next.js 15 project with TypeScript
- [x] Install and configure Tailwind CSS
- [x] Set up shadcn/ui design tokens
- [x] Set up TanStack Query with providers
- [x] Configure next.config.js with optimizePackageImports
- [x] Set up API client utilities (client.ts, server.ts)
- [x] Define TypeScript types for backend API
- [x] Create routing structure (dashboard, documents, query, sessions)
- [x] Create placeholder pages
- [x] Vitest setup with passing tests

**Tests:** 6/6 passing
**Build:** Successful (102kB First Load JS)

## Next Steps (Week 2)

- Add shadcn/ui components (Button, Card, Dialog, Input, etc.)
- Implement document upload form
- Implement document list with filters
- Add TanStack Query hooks
- Implement Suspense boundaries
- Add loading skeletons
