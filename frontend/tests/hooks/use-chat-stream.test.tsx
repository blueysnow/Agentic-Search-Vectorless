import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useChatStream } from '@/lib/hooks/use-chat-stream'

describe('useChatStream', () => {
  let mockEventSource: {
    addEventListener: ReturnType<typeof vi.fn>
    removeEventListener: ReturnType<typeof vi.fn>
    close: ReturnType<typeof vi.fn>
    readyState: number
    CONNECTING: number
    OPEN: number
    CLOSED: number
  }

  beforeEach(() => {
    // Mock EventSource
    mockEventSource = {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      close: vi.fn(),
      readyState: 1, // OPEN
      CONNECTING: 0,
      OPEN: 1,
      CLOSED: 2,
    }

    global.EventSource = vi.fn(() => mockEventSource) as any
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with empty messages and not streaming', () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    expect(result.current.messages).toEqual([])
    expect(result.current.isStreaming).toBe(false)
  })

  it('adds user message immediately when sendMessage is called', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('What is revenue?', ['doc-1'])
    })

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2) // user + assistant placeholder
      expect(result.current.messages[0]).toMatchObject({
        role: 'user',
        content: 'What is revenue?',
      })
      expect(result.current.messages[1]).toMatchObject({
        role: 'assistant',
        content: '',
      })
    })
  })

  it('sets isStreaming to true when sendMessage is called', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true)
    })
  })

  it('opens EventSource with correct URL and parameters', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1', 'doc-2'])
    })

    await waitFor(() => {
      const callArg = (global.EventSource as any).mock.calls[0][0]
      expect(callArg).toContain('/api/chat/stream')
      expect(callArg).toContain('sessionId=session-123')
      expect(callArg).toMatch(/message=Test(\+|%20)query/)
      expect(callArg).toContain('documentIds=doc-1%2Cdoc-2')
    })
  })

  it('handles "thinking" chunk type by adding to thinking array', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    // Simulate SSE message event
    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'thinking',
          content: 'Let me check document structure...',
        }),
      })
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.thinking).toContain('Let me check document structure...')
    })
  })

  it('handles "metadata" chunk type by updating metadata object', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'metadata',
          data: { doc_name: 'report.pdf', pages: '3-5' },
        }),
      })
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.metadata).toEqual({
        doc_name: 'report.pdf',
        pages: '3-5',
      })
    })
  })

  it('handles "content" chunk type by appending to message content', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'content',
          content: 'The revenue ',
        }),
      })
    })

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'content',
          content: 'is $2.5M.',
        }),
      })
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toBe('The revenue is $2.5M.')
    })
  })

  it('handles "citation" chunk type by adding to citations array', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'citation',
          data: { page: 3, text: 'Q4 revenue: $2.5M' },
        }),
      })
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.citations).toContainEqual({
        page: 3,
        text: 'Q4 revenue: $2.5M',
      })
    })
  })

  it('handles "done" chunk type by setting isStreaming to false and closing EventSource', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({ type: 'done' }),
      })
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false)
      expect(mockEventSource.close).toHaveBeenCalled()
    })
  })

  it('handles "error" chunk type by appending error to content and closing EventSource', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: JSON.stringify({
          type: 'error',
          content: 'Session not found',
        }),
      })
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toContain('[Error: Session not found]')
      expect(result.current.isStreaming).toBe(false)
      expect(mockEventSource.close).toHaveBeenCalled()
      expect(consoleErrorSpy).toHaveBeenCalledWith('Stream error:', 'Session not found')
    })

    consoleErrorSpy.mockRestore()
  })

  it('closes existing EventSource before opening new one when sendMessage is called multiple times', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('First query', ['doc-1'])
    })

    await waitFor(() => {
      expect(global.EventSource).toHaveBeenCalledTimes(1)
    })

    const firstClose = mockEventSource.close

    act(() => {
      result.current.sendMessage('Second query', ['doc-1'])
    })

    await waitFor(() => {
      expect(firstClose).toHaveBeenCalled()
      expect(global.EventSource).toHaveBeenCalledTimes(2)
    })
  })

  it('cleans up EventSource on unmount', async () => {
    const { result, unmount } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    unmount()

    expect(mockEventSource.close).toHaveBeenCalled()
  })

  it('handles malformed JSON in SSE chunks gracefully', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    act(() => {
      messageHandler?.({
        data: 'INVALID JSON{',
      })
    })

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to parse SSE chunk:',
        expect.any(Error)
      )
    })

    consoleErrorSpy.mockRestore()
  })

  it('handles EventSource error event by setting isStreaming to false', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const errorHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'error'
    )?.[1]

    act(() => {
      errorHandler?.({})
    })

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false)
      expect(mockEventSource.close).toHaveBeenCalled()
    })
  })

  it('initializes with provided initial messages', () => {
    const initialMessages = [
      {
        id: '1',
        role: 'user' as const,
        content: 'Previous question',
        timestamp: Date.now(),
      },
    ]

    const { result } = renderHook(() =>
      useChatStream('session-123', initialMessages)
    )

    expect(result.current.messages).toEqual(initialMessages)
  })

  // REM-FIX: SF-W3-001 - EventSource error handler must show user feedback
  it('SF-W3-001: displays error message to user when EventSource error occurs', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const errorHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'error'
    )?.[1]

    act(() => {
      errorHandler?.({})
    })

    await waitFor(() => {
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toContain('Connection error')
      expect(result.current.error).toBeTruthy()
      expect(result.current.error?.toLowerCase()).toContain('connection')
    })
  })

  // REM-FIX: SF-W3-002 - Chunk parse failures must show warning
  it('SF-W3-002: displays warning when chunks fail to parse', async () => {
    const { result } = renderHook(() => useChatStream('session-123'))
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    act(() => {
      result.current.sendMessage('Test query', ['doc-1'])
    })

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call) => call[0] === 'message'
    )?.[1]

    // Send multiple malformed chunks
    act(() => {
      messageHandler?.({ data: 'INVALID1{' })
    })

    act(() => {
      messageHandler?.({ data: 'INVALID2{' })
    })

    act(() => {
      messageHandler?.({ data: JSON.stringify({ type: 'content', content: 'valid' }) })
    })

    await waitFor(() => {
      expect(result.current.parseErrors).toBe(2)
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('parse errors detected')
      )
    })

    consoleWarnSpy.mockRestore()
  })

  // REM-FIX: SF-W3-003 - Stream must timeout after 30 seconds
  it('SF-W3-003: times out stream after 30 seconds without completion', async () => {
    vi.useFakeTimers()

    try {
      const { result } = renderHook(() => useChatStream('session-123'))

      act(() => {
        result.current.sendMessage('Test query', ['doc-1'])
      })

      // Fast-forward 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000)
      })

      // Check timeout occurred
      const assistantMessage = result.current.messages.find((m) => m.role === 'assistant')
      expect(assistantMessage?.content).toContain('timeout')
      expect(result.current.isStreaming).toBe(false)
      expect(mockEventSource.close).toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })
})
