import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const message = searchParams.get('message')
  const documentIds = searchParams.get('documentIds')?.split(',').filter(Boolean) || []
  const sessionId = searchParams.get('sessionId')

  // Validate parameters
  if (!message || documentIds.length === 0) {
    return new Response('Missing parameters', { status: 400 })
  }

  // Create SSE stream
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      // H1 Fix: Add 60-second timeout for backend requests
      const abortController = new AbortController()
      const timeoutId = setTimeout(() => abortController.abort(), 60000)

      try {
        // Prepare request body for FastAPI backend
        const requestBody: {
          message: string
          document_ids: string[]
          session_id?: string
        } = {
          message,
          document_ids: documentIds,
        }

        // Only include session_id if provided
        if (sessionId) {
          requestBody.session_id = sessionId
        }

        // Call FastAPI backend chat endpoint
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const res = await fetch(`${apiUrl}/query/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: abortController.signal,
        })

        if (!res.ok) {
          throw new Error('Chat request failed')
        }

        if (!res.body) {
          throw new Error('No response body')
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          // Backend sends SSE format: "data: {json}\n\n"
          const lines = decoder.decode(value).split('\n')

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed) continue

            try {
              // Strip SSE "data: " prefix if present (backend sends SSE format)
              const jsonStr = trimmed.startsWith('data: ')
                ? trimmed.slice(6)
                : trimmed
              const chunk = JSON.parse(jsonStr)

              // Forward chunk to client in SSE format
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`)
              )
            } catch {
              // Forward parse failures as error events so the client knows
              controller.enqueue(
                encoder.encode(
                  `data: ${JSON.stringify({ type: 'error', content: 'Failed to parse backend response' })}\n\n`
                )
              )
            }
          }
        }

        // Backend sends its own "done" event; only add one if stream ended without it
        controller.close()
      } catch (error) {
        // Send error to client
        const errorMessage =
          error instanceof Error ? error.message : 'Unknown error'
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ type: 'error', content: errorMessage })}\n\n`
          )
        )
        controller.close()
      } finally {
        clearTimeout(timeoutId)
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
