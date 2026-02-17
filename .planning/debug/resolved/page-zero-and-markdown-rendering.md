---
status: resolved
trigger: "Page numbers display as Page 0 and markdown in AI responses is not rendered"
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:05:00Z
---

## Current Focus

hypothesis: RESOLVED
test: N/A
expecting: N/A
next_action: N/A

## Symptoms

expected: |
  1. Reference cards should show page numbers starting from 1 (Page 1, Page 2, etc.)
  2. AI response text containing markdown (like **bold**, bullet points) should be rendered as formatted HTML

actual: |
  1. Reference cards show "Page 0" for all referenced sections
  2. Markdown syntax like **소개**:, **시스템 요구사항**: appears as raw plain text

errors: No error messages - just incorrect display behavior

reproduction: |
  1. Upload a document, then query it. The reference cards at the bottom show "Page 0"
  2. The AI response contains markdown formatting but it's displayed as plain text

started: Current behavior in the app

## Eliminated

(none - root causes found on first investigation)

## Evidence

- timestamp: 2026-02-17T00:01:00Z
  checked: src/api/routes/stream.py line 182
  found: "page": 0 is hardcoded - comment says "Page info would come from node metadata" but was never implemented
  implication: All citations always show Page 0 regardless of actual page number

- timestamp: 2026-02-17T00:01:00Z
  checked: frontend/components/chat/MessageItem.tsx line 41
  found: message.content rendered as plain text {message.content} inside div, no markdown parser
  implication: All markdown syntax appears as raw text instead of HTML

- timestamp: 2026-02-17T00:01:00Z
  checked: src/models/node.py
  found: Node model has startPage field (1-indexed per comment) stored in MongoDB as "startPage"
  implication: Can batch-query MongoDB nodes collection by node_id to get actual page numbers

- timestamp: 2026-02-17T00:01:00Z
  checked: src/db/collections.py
  found: nodes_col() function already exported, same pattern as documents_col()
  implication: Can import nodes_col in stream.py to query node pages

- timestamp: 2026-02-17T00:01:30Z
  checked: frontend/package.json
  found: No markdown library installed; react-markdown and @tailwindcss/typography both missing
  implication: Need to install both; typography plugin required for prose CSS classes to work

- timestamp: 2026-02-17T00:04:00Z
  checked: TypeScript compilation after changes
  found: npx tsc --noEmit returned 0 errors
  implication: MessageItem.tsx changes compile cleanly

- timestamp: 2026-02-17T00:04:30Z
  checked: Pre-existing test failures
  found: Tests failed with identical errors before our changes (Node 18 / jsdom 28 ESM incompatibility)
  implication: Test failures are pre-existing, not caused by our fixes

## Resolution

root_cause: |
  Issue 1 (Page 0): In src/api/routes/stream.py line 182, "page" was hardcoded to 0.
  The developer left placeholder "Page info would come from node metadata" but never implemented
  the MongoDB lookup. Nodes store their page range as startPage/endPage in the nodes collection.

  Issue 2 (Markdown): In frontend/components/chat/MessageItem.tsx, message.content was rendered
  as raw text {message.content}. The div had prose/prose-sm CSS classes (from Tailwind Typography)
  indicating markdown rendering was intended, but react-markdown was never installed or used.
  Additionally, @tailwindcss/typography plugin was not in tailwind.config.ts so prose classes
  had no effect anyway.

fix: |
  Issue 1: Added nodes_col import to stream.py, batch-query MongoDB for all nodes_read node IDs
  to get their startPage and title, then emit real page numbers and section titles in citations.
  Added deduplication to avoid emitting multiple citations for the same node.

  Issue 2: Installed react-markdown and @tailwindcss/typography. Updated MessageItem.tsx to wrap
  assistant message content with <ReactMarkdown>. User messages still render as plain text
  (markdown formatting is only needed for AI responses). Registered typography plugin in tailwind.config.ts.

verification: |
  - TypeScript compilation: npx tsc --noEmit returned 0 errors
  - git diff shows minimal, targeted changes
  - Pre-existing test failures confirmed to be unrelated (Node 18 / jsdom incompatibility)
  - Logic verified: nodes have 1-indexed startPage; batch query avoids N+1; dedup prevents duplicate citations

files_changed:
  - src/api/routes/stream.py
  - frontend/components/chat/MessageItem.tsx
  - frontend/package.json (react-markdown, @tailwindcss/typography added)
  - frontend/package-lock.json (auto-updated)
  - frontend/tailwind.config.ts (@tailwindcss/typography plugin registered)
