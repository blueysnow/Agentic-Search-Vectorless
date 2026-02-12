'use client'

import { useState } from 'react'
import { useDocuments } from '@/lib/hooks/useDocuments'
import { DocumentCard } from '@/components/documents/DocumentCard'
import { DocumentFilters } from '@/components/documents/DocumentFilters'
import type { DocumentFilters as Filters } from '@/lib/api/types'

export function DocumentsClient() {
  // Pattern 5.6: Lazy state initialization
  const [filters, setFilters] = useState<Filters>(() => ({}))
  const { data: documents, isLoading, isError, error } = useDocuments(filters)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading documents...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 border border-red-200 rounded-lg bg-red-50">
        <h3 className="font-semibold text-red-900 mb-2">Error loading documents</h3>
        <p className="text-sm text-red-700">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <DocumentFilters filters={filters} onChange={setFilters} />

      {documents && documents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <DocumentCard key={doc.documentId} document={doc} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 border rounded-lg">
          <p className="text-muted-foreground mb-2">No documents found</p>
          <p className="text-sm text-muted-foreground">
            {Object.keys(filters).length > 0
              ? 'Try adjusting your filters'
              : 'Upload your first document to get started'}
          </p>
        </div>
      )}

      {documents && documents.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {documents.length} document{documents.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}
