import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const documentId = searchParams.get('documentId')
    const limit = searchParams.get('limit')
    const offset = searchParams.get('offset')

    // Build query parameters for backend
    const params = new URLSearchParams()
    if (documentId) params.append('document_id', documentId)
    if (limit) params.append('limit', limit)
    if (offset) params.append('offset', offset)

    const apiUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002'
    const url = params.toString()
      ? `${apiUrl}/sessions/?${params.toString()}`
      : `${apiUrl}/sessions/`

    // H1: Add 10-second timeout for session list fetch
    const abortController = new AbortController()
    const timeoutId = setTimeout(() => abortController.abort(), 10000)

    try {
      const response = await fetch(url, {
        signal: abortController.signal,
      })

      if (!response.ok) {
        return NextResponse.json(
          { error: 'Failed to fetch sessions' },
          { status: response.status }
        )
      }

      const data = await response.json()
      // Transform backend session format to frontend SessionSummary format
      interface BackendSession {
        sessionId: string
        createdAt: string
        updatedAt: string
        documentId?: string
        totalTurns?: number
        firstQuery?: string
      }
      const sessions = (data.sessions || []).map((s: BackendSession) => ({
        id: s.sessionId,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        documentIds: s.documentId ? [s.documentId] : [],
        messageCount: s.totalTurns || 0,
        preview: s.firstQuery || `Session with ${s.totalTurns || 0} turns`,
      }))
      return NextResponse.json({ sessions })
    } finally {
      clearTimeout(timeoutId)
    }
  } catch (error) {
    console.error('Error fetching sessions:', error)

    // M-REM3-1: Handle AbortError specifically (timeout)
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        { error: 'Request timeout - server took too long to respond' },
        { status: 504 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
