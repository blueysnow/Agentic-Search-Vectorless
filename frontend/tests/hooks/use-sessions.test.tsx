import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSessions, useSession } from '@/lib/hooks/use-sessions'

// Mock fetch
global.fetch = vi.fn()

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useSessions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches sessions list successfully', async () => {
    const mockSessions = [
      {
        id: 'session-1',
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T10:30:00Z',
        documentIds: ['doc-1'],
        messageCount: 5,
        preview: 'What is revenue?',
      },
      {
        id: 'session-2',
        createdAt: '2024-01-14T09:00:00Z',
        updatedAt: '2024-01-14T09:15:00Z',
        documentIds: ['doc-2'],
        messageCount: 3,
        preview: 'Show me the chart',
      },
    ]

    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sessions: mockSessions }),
    })

    const { result } = renderHook(() => useSessions(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockSessions)
    // H6: Pagination params are now always included
    expect(global.fetch).toHaveBeenCalledWith('/api/sessions?limit=50&offset=0')
  })

  it('handles empty sessions list', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sessions: [] }),
    })

    const { result } = renderHook(() => useSessions(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual([])
  })

  it('handles fetch error', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { result } = renderHook(() => useSessions(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toBeDefined()
  })

  it('shows loading state initially', () => {
    ;(global.fetch as any).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    const { result } = renderHook(() => useSessions(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('filters sessions by document ID', async () => {
    const mockSessions = [
      {
        id: 'session-1',
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T10:30:00Z',
        documentIds: ['doc-1'],
        messageCount: 5,
        preview: 'Test 1',
      },
      {
        id: 'session-2',
        createdAt: '2024-01-14T09:00:00Z',
        updatedAt: '2024-01-14T09:15:00Z',
        documentIds: ['doc-2'],
        messageCount: 3,
        preview: 'Test 2',
      },
    ]

    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sessions: mockSessions }),
    })

    const { result } = renderHook(() => useSessions({ documentId: 'doc-1' }), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    // H6: Pagination params are now always included
    expect(global.fetch).toHaveBeenCalledWith('/api/sessions?documentId=doc-1&limit=50&offset=0')
  })

  it('supports custom pagination parameters', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sessions: [] }),
    })

    const { result } = renderHook(
      () => useSessions({ limit: 10, offset: 20 }),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/sessions?limit=10&offset=20'
    )
  })
})

describe('useSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches single session successfully', async () => {
    const mockSession = {
      id: 'session-1',
      createdAt: '2024-01-15T10:00:00Z',
      updatedAt: '2024-01-15T10:30:00Z',
      documentIds: ['doc-1'],
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'What is revenue?',
          timestamp: Date.now(),
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Revenue is $1M',
          timestamp: Date.now(),
        },
      ],
    }

    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSession,
    })

    const { result } = renderHook(() => useSession('session-1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(mockSession)
    expect(global.fetch).toHaveBeenCalledWith('/api/sessions/session-1')
  })

  it('handles session not found', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
    })

    const { result } = renderHook(() => useSession('nonexistent'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })
  })

  it('shows loading state initially', () => {
    ;(global.fetch as any).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    const { result } = renderHook(() => useSession('session-1'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('does not fetch if sessionId is undefined', () => {
    const { result } = renderHook(() => useSession(undefined), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toBeUndefined()
    expect(global.fetch).not.toHaveBeenCalled()
  })
})
