import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { GET } from '@/app/api/chat/stream/route'
import { NextRequest } from 'next/server'

describe('GET /api/chat/stream', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    global.fetch = mockFetch
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns 400 if message parameter is missing', async () => {
    const request = new NextRequest('http://localhost:3000/api/chat/stream?documentIds=doc-1')

    const response = await GET(request)

    expect(response.status).toBe(400)
    const text = await response.text()
    expect(text).toContain('Missing parameters')
  })

  it('returns 400 if documentIds parameter is missing', async () => {
    const request = new NextRequest('http://localhost:3000/api/chat/stream?message=test')

    const response = await GET(request)

    expect(response.status).toBe(400)
    const text = await response.text()
    expect(text).toContain('Missing parameters')
  })

  it('returns 400 if documentIds array is empty', async () => {
    const request = new NextRequest('http://localhost:3000/api/chat/stream?message=test&documentIds=')

    const response = await GET(request)

    expect(response.status).toBe(400)
    const text = await response.text()
    expect(text).toContain('Missing parameters')
  })

  it('calls FastAPI backend with correct request body', async () => {
    const mockReadableStream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('{"type":"content","content":"test"}\n')
        )
        controller.close()
      },
    })

    mockFetch.mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    })

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1,doc-2&sessionId=session-123'
    )

    await GET(request)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    )

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(callBody).toEqual({
      message: 'test',
      document_ids: ['doc-1', 'doc-2'],
      session_id: 'session-123',
    })
  })

  it('streams SSE chunks from FastAPI backend to client', async () => {
    const mockReadableStream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode('{"type":"thinking","content":"Checking..."}\n')
        )
        controller.enqueue(
          new TextEncoder().encode('{"type":"content","content":"Answer"}\n')
        )
        controller.enqueue(new TextEncoder().encode('{"type":"done"}\n'))
        controller.close()
      },
    })

    mockFetch.mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    })

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1'
    )

    const response = await GET(request)

    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('text/event-stream')
    expect(response.headers.get('Cache-Control')).toBe('no-cache')
    expect(response.headers.get('Connection')).toBe('keep-alive')

    // Read stream
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const chunks: string[] = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(decoder.decode(value))
    }

    const fullText = chunks.join('')
    expect(fullText).toContain('data: {"type":"thinking","content":"Checking..."}')
    expect(fullText).toContain('data: {"type":"content","content":"Answer"}')
    expect(fullText).toContain('data: {"type":"done"}')
  })

  it('returns error stream if FastAPI request fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    })

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1'
    )

    const response = await GET(request)

    expect(response.status).toBe(200) // SSE always returns 200
    expect(response.headers.get('Content-Type')).toBe('text/event-stream')

    // Read stream
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const chunks: string[] = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(decoder.decode(value))
    }

    const fullText = chunks.join('')
    expect(fullText).toContain('type":"error"')
    expect(fullText).toContain('Chat request failed')
  })

  it('returns error stream if FastAPI response has no body', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      body: null,
    })

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1'
    )

    const response = await GET(request)

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const chunks: string[] = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(decoder.decode(value))
    }

    const fullText = chunks.join('')
    expect(fullText).toContain('type":"error"')
    expect(fullText).toContain('No response body')
  })

  it('handles fetch exception and returns error stream', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1'
    )

    const response = await GET(request)

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const chunks: string[] = []

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      chunks.push(decoder.decode(value))
    }

    const fullText = chunks.join('')
    expect(fullText).toContain('type":"error"')
    expect(fullText).toContain('Network error')
  })

  it('omits session_id from backend request if not provided', async () => {
    const mockReadableStream = new ReadableStream({
      start(controller) {
        controller.close()
      },
    })

    mockFetch.mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    })

    const request = new NextRequest(
      'http://localhost:3000/api/chat/stream?message=test&documentIds=doc-1'
    )

    await GET(request)

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(callBody).toEqual({
      message: 'test',
      document_ids: ['doc-1'],
      // session_id should not be present
    })
    expect('session_id' in callBody).toBe(false)
  })
})
