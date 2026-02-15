import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDocuments, useDocument, useUploadDocument } from '@/lib/hooks/useDocuments'
import { apiClient } from '@/lib/api/client'
import { createElement, type ReactNode } from 'react'

vi.mock('@/lib/api/client')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe('useDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch documents successfully', async () => {
    const mockDocuments = [
      {
        documentId: 'doc1',
        name: 'Test Doc',
        type: 'pdf' as const,
        totalPages: 10,
        totalNodes: 50,
        totalTokens: 1000,
        ingestion: { status: 'completed' as const, errors: [] },
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ]

    vi.mocked(apiClient.getDocuments).mockResolvedValueOnce(mockDocuments)

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockDocuments)
  })

  it('should handle fetch errors', async () => {
    const error = new Error('Failed to fetch documents: 500 Internal Server Error')
    vi.mocked(apiClient.getDocuments).mockRejectedValueOnce(error)

    const { result } = renderHook(() => useDocuments(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toEqual(error)
  })

  it('should apply filters', async () => {
    const filters = { status: 'completed' as const, domain: 'science' }
    vi.mocked(apiClient.getDocuments).mockResolvedValueOnce([])

    renderHook(() => useDocuments(filters), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalledWith(filters)
    })
  })
})

describe('useDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch single document', async () => {
    const mockDocument = {
      documentId: 'doc1',
      name: 'Test Doc',
      type: 'pdf' as const,
      totalPages: 10,
      totalNodes: 50,
      totalTokens: 1000,
      ingestion: { status: 'completed' as const, errors: [] },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    }

    vi.mocked(apiClient.getDocument).mockResolvedValueOnce(mockDocument)

    const { result } = renderHook(() => useDocument('doc1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockDocument)
  })

  it('should not fetch when documentId is empty', () => {
    const { result } = renderHook(() => useDocument(''), {
      wrapper: createWrapper(),
    })

    expect(result.current.fetchStatus).toBe('idle')
    expect(apiClient.getDocument).not.toHaveBeenCalled()
  })
})

describe('useUploadDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should upload document with progress tracking', async () => {
    const mockResponse = {
      documentId: 'doc1',
      name: 'Test.pdf',
      status: 'processing',
      totalPages: 10,
      totalNodes: 50,
      totalTokens: 1000,
    }

    vi.mocked(apiClient.uploadDocumentWithProgress).mockImplementation(
      (_formData, onProgress) => {
        onProgress(50)
        onProgress(100)
        return Promise.resolve(mockResponse)
      }
    )

    const { result } = renderHook(() => useUploadDocument(), {
      wrapper: createWrapper(),
    })

    const formData = new FormData()
    formData.append('file', new File(['test'], 'test.pdf', { type: 'application/pdf' }))

    result.current.mutate(formData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockResponse)
  })

  it('should handle upload errors', async () => {
    const error = new Error('File too large (413)')
    vi.mocked(apiClient.uploadDocumentWithProgress).mockRejectedValueOnce(error)

    const { result } = renderHook(() => useUploadDocument(), {
      wrapper: createWrapper(),
    })

    const formData = new FormData()
    result.current.mutate(formData)

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toEqual(error)
  })

  it('should expose uploadProgress state', async () => {
    const { result } = renderHook(() => useUploadDocument(), {
      wrapper: createWrapper(),
    })

    // Initially null
    expect(result.current.uploadProgress).toBeNull()
  })
})
