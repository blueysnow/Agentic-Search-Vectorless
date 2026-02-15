import { NextRequest, NextResponse } from 'next/server'
import { isValidSessionId } from '@/lib/security'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params

    // H5: Validate session ID to prevent injection attacks
    if (!isValidSessionId(sessionId)) {
      return NextResponse.json(
        { error: 'Invalid session ID format' },
        { status: 400 }
      )
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    // M-REM3-2: Add 10-second timeout for GET request
    const abortController = new AbortController()
    const timeoutId = setTimeout(() => abortController.abort(), 10000)

    try {
      const response = await fetch(`${apiUrl}/sessions/${sessionId}`, {
        signal: abortController.signal,
      })

      if (!response.ok) {
        return NextResponse.json(
          { error: 'Session not found' },
          { status: response.status }
        )
      }

      const data = await response.json()
      // Transform backend SessionResponse to frontend Session format
      const session = {
        id: data.sessionId,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
        documentIds: data.documentId ? [data.documentId] : [],
        messages: (data.turns || []).flatMap((t: { query?: string; answer?: string; timestamp?: string }, i: number) => [
          ...(t.query ? [{ id: `turn-${i}-user`, role: 'user' as const, content: t.query, timestamp: t.timestamp }] : []),
          ...(t.answer ? [{ id: `turn-${i}-assistant`, role: 'assistant' as const, content: t.answer, timestamp: t.timestamp }] : []),
        ]),
      }
      return NextResponse.json(session)
    } finally {
      clearTimeout(timeoutId)
    }
  } catch (error) {
    console.error('Error fetching session:', error)

    // Handle AbortError (timeout)
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params

    // H5: Validate session ID to prevent injection attacks
    if (!isValidSessionId(sessionId)) {
      return NextResponse.json(
        { error: 'Invalid session ID format' },
        { status: 400 }
      )
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    // M-REM3-3: Add 10-second timeout for DELETE request
    const abortController = new AbortController()
    const timeoutId = setTimeout(() => abortController.abort(), 10000)

    try {
      const response = await fetch(`${apiUrl}/sessions/${sessionId}`, {
        method: 'DELETE',
        signal: abortController.signal,
      })

      if (!response.ok) {
        return NextResponse.json(
          { error: 'Failed to delete session' },
          { status: response.status }
        )
      }

      return NextResponse.json({ success: true })
    } finally {
      clearTimeout(timeoutId)
    }
  } catch (error) {
    console.error('Error deleting session:', error)

    // Handle AbortError (timeout)
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout' },
        { status: 504 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
