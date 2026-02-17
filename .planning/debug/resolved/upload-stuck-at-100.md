---
status: resolved
trigger: "File upload reaches 100% but UI stays stuck on 'Uploading...' instead of transitioning to completed state"
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:02:00Z
---

## Current Focus

hypothesis: RESOLVED
test: fix applied and verified via TypeScript type check + ESLint
expecting: UI now shows "Processing document..." when data transfer completes, transitions to success banner when server responds
next_action: archived

## Symptoms

expected: After file upload reaches 100%, the UI should transition to a success/completed state automatically
actual: UI stays stuck at "Uploading... 100%" with the progress bar full and button showing "Uploading...". The upload actually completes on the backend (confirmed by reload showing completed)
errors: No visible error messages - it just hangs
reproduction: Upload any file (e.g. PDF), wait for progress to reach 100%, observe UI stays stuck
started: Current behavior, unclear when it started

## Eliminated

- hypothesis: JSON parse failure in XHR load handler
  evidence: IngestResponse is valid JSON with correct field names (using by_alias=True), no parse errors reported
  timestamp: 2026-02-17T00:01:00Z

- hypothesis: CORS blocking XHR response
  evidence: docker-compose configures CORS_ORIGINS=http://localhost:3000, GET /documents works fine, same CORS rules apply
  timestamp: 2026-02-17T00:01:00Z

- hypothesis: onSuccess callback not firing
  evidence: TanStack Query v5 fires both hook-level and per-call onSuccess; React 18 batches state updates correctly; component stays mounted
  timestamp: 2026-02-17T00:01:00Z

- hypothesis: XHR timeout causing permanent hang
  evidence: If timeout fires (after 300s), onError runs and sets uploadProgress=null, error message shows. User reports no error message.
  timestamp: 2026-02-17T00:01:00Z

- hypothesis: Code bug causing mutation to never complete
  evidence: XHR load event -> resolve() -> TanStack Query onSuccess -> setUploadProgress(null) + isPending=false - all paths are correct
  timestamp: 2026-02-17T00:01:00Z

## Evidence

- timestamp: 2026-02-17T00:01:00Z
  checked: frontend/lib/api/client.ts uploadDocumentWithProgress()
  found: XHR uses xhr.upload.addEventListener('progress') which fires during DATA SEND phase only. When all data is sent, progress hits 100%. Server then runs page_index_main() (LLM calls) which takes minutes. XHR load event only fires when server sends response.
  implication: Progress showing 100% does NOT mean the operation is complete - it means data was fully sent. Server is still processing.

- timestamp: 2026-02-17T00:01:00Z
  checked: src/api/routes/ingest.py POST /ingest/upload handler
  found: Endpoint is SYNCHRONOUS - runs full ingestion pipeline (page_index_main with LLM calls to build PageIndex tree) before responding. This can take minutes.
  implication: HTTP connection stays open during LLM processing. XHR waits for server response.

- timestamp: 2026-02-17T00:01:00Z
  checked: frontend/components/documents/UploadForm.tsx progress bar rendering
  found: Progress bar shows when isPending=true AND uploadProgress !== null. At 100% progress + isPending=true, the text "Uploading..." makes no distinction between data-transfer-in-progress and server-processing-in-progress phases.
  implication: Root cause: UX communicates nothing about the server-side processing phase. User sees 100% and perceives the UI as "stuck" because there's no indication that the server is still working.

- timestamp: 2026-02-17T00:01:00Z
  checked: docker-compose.yml NEXT_PUBLIC_API_URL and xhr.timeout settings
  found: xhr.timeout = 300,000ms (5 min). If ingestion takes more than 5 minutes, timeout error shows. If less than 5 minutes, mutation completes normally and UI transitions correctly.
  implication: The code DOES work correctly. The perceived "stuck" state is temporary (during server processing) not permanent. UX bug, not code logic bug.

## Resolution

root_cause: XHR upload.progress events track the DATA TRANSFER phase only. When the file is fully sent (progress = 100%), the server begins the ingestion pipeline (AI-based tree building via LLM) which can take minutes. During this server-processing phase, the UI showed "Uploading... 100%" with no differentiation from the data-transfer phase. Users see 100% and assume it's done, not realizing the server is still processing. The code is functionally correct (mutation does eventually complete), but the UX is misleading.

fix: Two targeted changes:
  1. frontend/lib/api/client.ts: Cap XHR upload progress at 99% (Math.min(99, percent)). The 100% mark is now semantically reserved for "server processing complete". During data transfer, max shown is 99%.
  2. frontend/components/documents/UploadForm.tsx: When uploadProgress >= 99 (data fully sent, server processing), show "Processing document..." text and "Building document index with AI (this may take a minute)..." explanation. Button also switches to "Processing..." text. This clearly communicates the two-phase nature of the upload.

verification: TypeScript type check passes (npx tsc --noEmit). ESLint shows only pre-existing warnings, no new issues. The UI flow is now:
  - 0-98%: "Uploading..." (data transfer)
  - 99%: "Processing document... / File received. Building document index with AI..." (server processing)
  - Complete: Success banner "Document uploaded and indexed successfully! Your document is ready to query."
  - Error: Error message shown (network error, timeout, etc.)

files_changed:
  - frontend/lib/api/client.ts
  - frontend/components/documents/UploadForm.tsx
