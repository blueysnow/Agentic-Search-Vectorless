import { useQuery } from '@tanstack/react-query'
import type { ChatMessage } from './use-chat-stream'

export interface SessionSummary {
  id: string
  createdAt: string
  updatedAt: string
  documentIds: string[]
  messageCount: number
  preview: string
}

export interface Session {
  id: string
  createdAt: string
  updatedAt: string
  documentIds: string[]
  messages: ChatMessage[]
}

interface UseSessionsOptions {
  documentId?: string
  startDate?: string
  endDate?: string
  limit?: number  // H6: Add pagination support
  offset?: number
}

/**
 * Fetches list of conversation sessions with optional filters
 * Uses TanStack Query for caching and request deduplication
 * H6: Added pagination support (default limit=50)
 */
export function useSessions(options: UseSessionsOptions = {}) {
  const { documentId, startDate, endDate, limit = 50, offset = 0 } = options

  return useQuery({
    queryKey: ['sessions', { documentId, startDate, endDate, limit, offset }],
    queryFn: async () => {
      const params = new URLSearchParams()

      if (documentId) {
        params.append('documentId', documentId)
      }
      if (startDate) {
        params.append('startDate', startDate)
      }
      if (endDate) {
        params.append('endDate', endDate)
      }

      // H6: Add pagination parameters
      params.append('limit', String(limit))
      params.append('offset', String(offset))

      const url = `/api/sessions?${params.toString()}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`)
      }

      const data = await response.json()
      return data.sessions as SessionSummary[]
    },
  })
}

/**
 * Fetches a single session with full message history
 * Uses TanStack Query for caching and request deduplication
 */
export function useSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: async () => {
      if (!sessionId) {
        throw new Error('Session ID is required')
      }

      const response = await fetch(`/api/sessions/${sessionId}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch session: ${response.status}`)
      }

      return await response.json() as Session
    },
    enabled: !!sessionId, // Only run query if sessionId is provided
  })
}
