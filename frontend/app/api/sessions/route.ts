import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const documentId = searchParams.get('documentId')
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')

    // Build query parameters for backend
    const params = new URLSearchParams()
    if (documentId) params.append('document_id', documentId)
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const url = params.toString()
      ? `${apiUrl}/api/sessions?${params.toString()}`
      : `${apiUrl}/api/sessions`

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
      return NextResponse.json({ sessions: data.sessions })
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
