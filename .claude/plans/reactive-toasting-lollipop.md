# UX Refactor: Vectorless RAG Boilerplate

## Context

The frontend is non-functional for the core user flow. After uploading a document, the user cannot chat about it because:
1. The chat page never fetches documents — DocumentSelector always shows "No documents available" and input is permanently disabled
2. `getDocuments()` doesn't unwrap the backend response wrapper `{ documents: [...], total }`, so even pages that call it get broken data
3. No persistent navigation — user is stranded on each page with no way to move between sections
4. No upload progress or success transition to chat
5. Type mismatches between frontend and backend (field names differ)

The app needs to become a polished, publishable boilerplate for anyone exploring vectorless RAG.

---

## Phase 1: Critical Bug Fixes (Make It Work)

### 1.1 Fix `getDocuments()` response unwrapping

**File:** `frontend/lib/api/client.ts` (line 99-102)

Backend returns `{ documents: Document[], total: number }` but client returns the raw wrapper. Unwrap `.documents`.

Also fix `frontend/lib/api/server.ts` `fetchDocuments()` — same unwrapping needed.

### 1.2 Fix ChatClient to fetch documents internally

**File:** `frontend/components/chat/ChatClient.tsx`

- Remove `availableDocuments` prop (never passed, always `[]`)
- Import and call `useDocuments()` hook internally
- Map backend `Document` fields (`documentId`/`name`/`totalPages`) to DocumentSelector format (`id`/`title`/`pageCount`)
- Read `?documentId=xxx` from URL searchParams for pre-selection
- Pass `isLoading` to DocumentSelector

### 1.3 Add loading state to DocumentSelector

**File:** `frontend/components/chat/DocumentSelector.tsx`

- Add `isLoading?: boolean` prop
- Show "Loading documents..." while fetching, "No documents available" when empty, list when populated

### 1.4 Fix sessions API route URL

**File:** `frontend/app/api/sessions/route.ts`

- Backend mounts at `/sessions` not `/api/sessions` — fix the proxy URL

### 1.5 Add `IngestResponse` type

**File:** `frontend/lib/api/types.ts`

- Add type matching backend response: `{ documentId, name, status, totalPages, totalNodes, totalTokens }`
- Fix `uploadDocument` return type from `Document` to `IngestResponse`

---

## Phase 2: Layout & Navigation (Make It Navigable)

### 2.1 Create Sidebar component

**New file:** `frontend/components/layout/Sidebar.tsx`

- Logo/title linking to `/documents`
- Nav links: Documents, Chat, Sessions — active page highlighted via `usePathname()`
- Mobile hamburger toggle with overlay
- Collapsible on mobile (`lg:` breakpoint)

### 2.2 Create AppShell wrapper

**New file:** `frontend/components/layout/AppShell.tsx`

- Flex container: Sidebar (fixed 256px) + main content (flex-1, overflow-y-auto)

### 2.3 Integrate into root layout

**File:** `frontend/app/layout.tsx`

- Wrap `{children}` in `<AppShell>`

**File:** `frontend/app/page.tsx`

- Replace landing page with `redirect('/documents')` — documents is the natural entry point

### 2.4 Fix page heights for sidebar layout

**Files:** `app/query/page.tsx`, `app/chat/page.tsx`, `app/sessions/page.tsx`, `app/sessions/[id]/page.tsx`

- Change `h-screen` → `h-full`, `min-h-screen` → `min-h-full` (now inside flex child, not root)

### 2.5 Redirect dashboard

**File:** `frontend/app/dashboard/page.tsx`

- Replace with `redirect('/documents')` — sidebar supersedes the dashboard

---

## Phase 3: UX Polish (Make It Delightful)

### 3.1 Upload progress bar

**File:** `frontend/lib/api/client.ts`

- Add `uploadDocumentWithProgress(formData, onProgress)` using `XMLHttpRequest` (fetch API has no upload progress support)

**File:** `frontend/lib/hooks/useDocuments.ts`

- Add `uploadProgress` state to `useUploadDocument`, wire to XHR progress callback

**File:** `frontend/components/documents/UploadForm.tsx`

- Render progress bar (0-100%) during upload with percentage label
- Animated width transition on the bar

### 3.2 Upload success → chat transition

**File:** `frontend/components/documents/UploadForm.tsx`

- Store `lastUploadedDocId` from `IngestResponse` on success
- Show green success banner with **"Chat about this document →"** link to `/query?documentId=xxx`
- Fire toast notification via existing `useToast` hook

### 3.3 "Chat" button on document cards

**File:** `frontend/components/documents/DocumentCard.tsx`

- Add small "Chat" button on completed documents linking to `/query?documentId=xxx`
- `e.stopPropagation()` to prevent card's own link from firing

### 3.4 Consolidate /chat and /query

**File:** `frontend/app/chat/page.tsx` → redirect to `/query`

**Files:** `app/sessions/page.tsx`, `app/sessions/[id]/page.tsx` → update all `/chat` links to `/query`

### 3.5 Click-outside close for DocumentSelector

**File:** `frontend/components/chat/DocumentSelector.tsx`

- Add `useRef` + `mousedown` listener to close dropdown on outside click
- Add `Escape` key handler

---

## Files Changed

| File | Phase | What |
|------|-------|------|
| `frontend/lib/api/client.ts` | 1.1, 3.1 | Unwrap getDocuments; add XHR upload with progress |
| `frontend/lib/api/server.ts` | 1.1 | Unwrap fetchDocuments |
| `frontend/lib/api/types.ts` | 1.5 | Add IngestResponse type |
| `frontend/components/chat/ChatClient.tsx` | 1.2 | Self-fetch documents, URL param pre-selection |
| `frontend/components/chat/DocumentSelector.tsx` | 1.3, 3.5 | Loading state, click-outside, keyboard |
| `frontend/app/layout.tsx` | 2.3 | Add AppShell wrapper |
| `frontend/app/page.tsx` | 2.3 | Redirect to /documents |
| `frontend/app/query/page.tsx` | 2.4 | h-screen → h-full |
| `frontend/app/chat/page.tsx` | 2.4, 3.4 | h-screen → h-full, then redirect |
| `frontend/app/dashboard/page.tsx` | 2.5 | Redirect to /documents |
| `frontend/app/sessions/page.tsx` | 2.4, 3.4 | Fix heights, /chat → /query |
| `frontend/app/sessions/[id]/page.tsx` | 2.4, 3.4 | Fix heights, /chat → /query |
| `frontend/components/documents/UploadForm.tsx` | 3.1, 3.2 | Progress bar, success CTA |
| `frontend/lib/hooks/useDocuments.ts` | 3.1 | uploadProgress state |
| `frontend/components/documents/DocumentCard.tsx` | 3.3 | Chat button |
| `frontend/app/api/sessions/route.ts` | 1.4 | Fix proxy URL |
| **NEW** `frontend/components/layout/Sidebar.tsx` | 2.1 | Sidebar navigation |
| **NEW** `frontend/components/layout/AppShell.tsx` | 2.2 | Layout shell |

## Files NOT Changed (Already Working)
- `ChatInput.tsx`, `MessageList.tsx`, `MessageItem.tsx`, `ThinkingProcess.tsx`, `PageCitation.tsx`
- `use-chat-stream.ts` (streaming hook works)
- `app/api/chat/stream/route.ts` (SSE proxy works)
- All backend files — no backend changes needed

---

## Verification

**After Phase 1:**
- [ ] `/documents` loads and shows document cards
- [ ] `/query` loads DocumentSelector with actual documents from backend
- [ ] Selecting a document enables chat input
- [ ] Sending a message starts streaming response
- [ ] `/query?documentId=xxx` pre-selects the document

**After Phase 2:**
- [ ] Sidebar visible on every page with active link highlighted
- [ ] Mobile: hamburger toggle opens/closes sidebar
- [ ] No double scrollbar; content scrolls independently
- [ ] `/` redirects to `/documents`

**After Phase 3:**
- [ ] Upload shows progress bar 0→100%
- [ ] Success shows "Chat about this document →" link
- [ ] Clicking link goes to `/query?documentId=xxx` with document pre-selected
- [ ] Document cards have "Chat" button for completed docs
- [ ] Dropdown closes on outside click and Escape key

**Final:** `docker compose build frontend && docker compose up -d frontend` — verify all above in Docker
