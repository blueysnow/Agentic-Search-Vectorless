// Pattern 3.4: Per-request deduplication with React.cache()
import { cache } from 'react'
import { API_CONFIG } from '../config'
import type { Document, DocumentFilters, Session } from './types'

export const fetchDocument = cache(async (documentId: string): Promise<Document> => {
  const res = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.documents}/${documentId}`, {
    next: { revalidate: 60 }, // Cache for 60s
  })

  if (!res.ok) {
    throw new Error(
      `Failed to fetch document ${documentId}: ${res.status} ${res.statusText}`
    )
  }
  return res.json()
})

export const fetchDocuments = cache(
  async (filters?: DocumentFilters): Promise<Document[]> => {
    const params = new URLSearchParams(filters as Record<string, string>)
    const res = await fetch(
      `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.documents}?${params}`,
      {
        next: { revalidate: 30 },
      }
    )

    if (!res.ok) {
      throw new Error(
        `Failed to fetch documents: ${res.status} ${res.statusText}`
      )
    }
    return res.json()
  }
)

export const fetchSession = cache(async (sessionId: string): Promise<Session> => {
  const res = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.sessions}/${sessionId}`, {
    next: { revalidate: 10 }, // Sessions update frequently
  })

  if (!res.ok) {
    throw new Error(
      `Failed to fetch session ${sessionId}: ${res.status} ${res.statusText}`
    )
  }
  return res.json()
})

export const fetchSessions = cache(
  async (params?: { documentId?: string; limit?: number }): Promise<Session[]> => {
    const query = new URLSearchParams(params as Record<string, string>)
    const res = await fetch(
      `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.sessions}?${query}`,
      {
        next: { revalidate: 30 },
      }
    )

    if (!res.ok) {
      throw new Error(
        `Failed to fetch sessions: ${res.status} ${res.statusText}`
      )
    }
    return res.json()
  }
)
