import { useState, useEffect, useRef } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string[]
  metadata?: {
    doc_name?: string
    pages?: number | string
    [key: string]: unknown
  }
  citations?: Array<{ page: number; text: string }>
  timestamp: number
}

interface StreamChunk {
  type: 'thinking' | 'metadata' | 'content' | 'citation' | 'done' | 'error'
  content?: string
  data?: {
    page?: number
    text?: string
    [key: string]: unknown
  }
}

export function useChatStream(sessionId: string, initialMessages: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [parseErrors, setParseErrors] = useState(0)
  const eventSourceRef = useRef<EventSource | null>(null)
  const currentMessageRef = useRef<ChatMessage | null>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  const sendMessage = (message: string, documentIds: string[]) => {
    // Clear previous errors and counters
    setError(null)
    setParseErrors(0)

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, userMessage])

    setIsStreaming(true)

    // Close existing stream and timeout
    eventSourceRef.current?.close()
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }

    // Initialize assistant message
    currentMessageRef.current = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      thinking: [],
      citations: [],
      timestamp: Date.now(),
    }
    setMessages((prev) => [...prev, currentMessageRef.current!])

    // Open new SSE stream
    const params = new URLSearchParams({
      sessionId,
      message,
      documentIds: documentIds.join(','),
    })
    const url = `/api/chat/stream?${params.toString()}`
    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    // SF-W3-003 Fix: Set 30-second timeout for stream
    timeoutRef.current = setTimeout(() => {
      const current = currentMessageRef.current!
      current.content += '\n\n[Stream timeout - connection may be slow. Reconnecting...]'
      setMessages((prev) => [...prev.slice(0, -1), { ...current }])
      setIsStreaming(false)
      eventSource.close()
    }, 30000)

    eventSource.addEventListener('message', (event) => {
      try {
        const chunk: StreamChunk = JSON.parse(event.data)
        const current = currentMessageRef.current!

        switch (chunk.type) {
          case 'thinking':
            // Add thinking step
            current.thinking = [...(current.thinking || []), chunk.content!]
            break

          case 'metadata':
            // Store metadata
            if (chunk.data) {
              current.metadata = { ...current.metadata, ...chunk.data }
            }
            break

          case 'content':
            // Append content chunk
            current.content += chunk.content
            break

          case 'citation':
            // Add page citation
            if (chunk.data && typeof chunk.data.page === 'number' && typeof chunk.data.text === 'string') {
              current.citations = [...(current.citations || []), { page: chunk.data.page, text: chunk.data.text }]
            }
            break

          case 'done':
            setIsStreaming(false)
            eventSource.close()
            if (timeoutRef.current) {
              clearTimeout(timeoutRef.current)
              timeoutRef.current = null
            }
            return

          case 'error':
            console.error('Stream error:', chunk.content)
            current.content += '\n\n[Error: ' + chunk.content + ']'
            setIsStreaming(false)
            eventSource.close()
            if (timeoutRef.current) {
              clearTimeout(timeoutRef.current)
              timeoutRef.current = null
            }
            return
        }

        // Trigger re-render with updated message
        setMessages((prev) => [...prev.slice(0, -1), { ...current }])
      } catch (error) {
        // SF-W3-002 Fix: Track parse errors and warn user
        console.error('Failed to parse SSE chunk:', error)
        setParseErrors((prev) => {
          const newCount = prev + 1
          if (newCount >= 2) {
            console.warn(`${newCount} parse errors detected - stream may be corrupted`)
          }
          return newCount
        })
      }
    })

    eventSource.addEventListener('error', () => {
      // SF-W3-001 Fix: Display error to user
      const current = currentMessageRef.current!
      current.content += '\n\n[Connection error - stream interrupted]'
      setMessages((prev) => [...prev.slice(0, -1), { ...current }])
      setError('Connection error occurred during streaming')
      setIsStreaming(false)
      eventSource.close()
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    })
  }

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close()
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return { messages, isStreaming, sendMessage, error, parseErrors }
}
