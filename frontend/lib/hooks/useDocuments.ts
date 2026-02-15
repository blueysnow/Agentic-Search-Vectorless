import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { Document, DocumentFilters, IngestResponse } from '../api/types'

export const DOCUMENTS_QUERY_KEY = 'documents'

export function useDocuments(filters?: DocumentFilters) {
  return useQuery({
    queryKey: [DOCUMENTS_QUERY_KEY, filters],
    queryFn: () => apiClient.getDocuments(filters),
  })
}

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: [DOCUMENTS_QUERY_KEY, documentId],
    queryFn: () => apiClient.getDocument(documentId),
    enabled: !!documentId,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: (formData: FormData) => {
      setUploadProgress(0)
      return apiClient.uploadDocumentWithProgress(formData, (percent) => {
        setUploadProgress(percent)
      })
    },
    onSuccess: () => {
      setUploadProgress(null)
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_QUERY_KEY] })
    },
    onError: () => {
      setUploadProgress(null)
    },
  })

  const resetProgress = useCallback(() => {
    setUploadProgress(null)
  }, [])

  return {
    ...mutation,
    uploadProgress,
    resetProgress,
  }
}
