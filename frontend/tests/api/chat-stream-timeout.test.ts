import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GET } from '@/app/api/chat/stream/route'
import { NextRequest } from 'next/server'

describe('Chat Stream API - Timeout Protection', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('should pass AbortSignal to fetch request', async () => {
    let capturedSignal: AbortSignal | undefined

    // Mock fetch to capture the signal
    const mockFetch = vi.fn((_url: string, options?: any) => {
      capturedSignal = options?.signal

      // Return a successful response
      return Promise.resolve({
        ok: true,
        body: new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('{"type":"done"}\n'))
            controller.close()
          },
        }),
      })
    })

    global.fetch = mockFetch as any

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc1&sessionId=session1'
    )

    const response = await GET(request)

    // Verify signal was passed
    expect(mockFetch).toHaveBeenCalled()
    expect(capturedSignal).toBeDefined()
    expect(capturedSignal).toBeInstanceOf(AbortSignal)

    // Cleanup
    await response.text()
  })
})
