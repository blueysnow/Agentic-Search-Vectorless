import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '@/lib/api/client'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('Client API error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('fetch', () => {
    it('should preserve HTTP status code in error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Resource not found' }),
      })

      await expect(apiClient.getDocument('test')).rejects.toThrow(/404/)
    })

    it('should log parse errors and include status when JSON parsing fails', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })

      await expect(apiClient.getDocument('test')).rejects.toThrow(/500/)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('should include error type in structured error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ detail: 'Invalid input' }),
      })

      try {
        await apiClient.getDocument('test')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toContain('400')
        expect((error as Error).message).toContain('Invalid input')
      }
    })
  })

  describe('uploadDocument', () => {
    it('should log parse errors and preserve status', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 413,
        statusText: 'Payload Too Large',
        json: async () => {
          throw new Error('Invalid JSON')
        },
      })

      const formData = new FormData()
      await expect(apiClient.uploadDocument(formData)).rejects.toThrow(/413/)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('should include request context in error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 415,
        statusText: 'Unsupported Media Type',
        json: async () => ({ detail: 'Only PDF and Markdown supported' }),
      })

      const formData = new FormData()
      try {
        await apiClient.uploadDocument(formData)
        expect.fail('Should have thrown')
      } catch (error) {
        expect((error as Error).message).toContain('415')
        expect((error as Error).message).toContain('PDF')
      }
    })

    // SF-011: Timeout test for upload
    it('should have timeout configured for uploads', () => {
      // Test that APIClient has upload timeout constant
      const client = apiClient as unknown as { UPLOAD_TIMEOUT: number }
      expect(client['UPLOAD_TIMEOUT']).toBe(300000) // 300 seconds
    })
  })

  // SF-011: Timeout test for regular fetch
  describe('fetch timeouts', () => {
    it('should have default timeout configured', () => {
      // Test that APIClient has default timeout constant
      const client = apiClient as unknown as { DEFAULT_TIMEOUT: number }
      expect(client['DEFAULT_TIMEOUT']).toBe(10000) // 10 seconds
    })

    it('should have query timeout configured', () => {
      // Test that APIClient has query timeout constant
      const client = apiClient as unknown as { QUERY_TIMEOUT: number }
      expect(client['QUERY_TIMEOUT']).toBe(60000) // 60 seconds
    })
  })
})
