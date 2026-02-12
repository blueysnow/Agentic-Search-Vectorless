import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import type { Document, DocumentFilters } from '../api/types'

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

  return useMutation({
    mutationFn: (formData: FormData) => apiClient.uploadDocument(formData),
    onSuccess: () => {
      // Invalidate documents list to refetch
      queryClient.invalidateQueries({ queryKey: [DOCUMENTS_QUERY_KEY] })
    },
  })
}
