import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchDocument,
  fetchDocuments,
  fetchSession,
  fetchSessions,
} from '@/lib/api/server'

// Mock fetch globally
global.fetch = vi.fn()

describe('Server API error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchDocument', () => {
    it('should throw detailed error on 404', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      const error = fetchDocument('doc-404')
      await expect(error).rejects.toThrow(/404/)
      await expect(error).rejects.toThrow(/doc-404/)
    })

    it('should throw detailed error on 500', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response)

      await expect(fetchDocument('doc123')).rejects.toThrow(/500/)
    })
  })

  describe('fetchDocuments', () => {
    it('should throw detailed error with status code', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
      } as Response)

      await expect(fetchDocuments()).rejects.toThrow(/503/)
    })
  })

  describe('fetchSession', () => {
    it('should throw detailed error on 404 with session ID', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      } as Response)

      const error = fetchSession('session-404')
      await expect(error).rejects.toThrow(/404/)
      await expect(error).rejects.toThrow(/session-404/)
    })
  })

  describe('fetchSessions', () => {
    it('should throw detailed error with context', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
      } as Response)

      await expect(fetchSessions({ limit: 10 })).rejects.toThrow(/400/)
    })
  })
})
