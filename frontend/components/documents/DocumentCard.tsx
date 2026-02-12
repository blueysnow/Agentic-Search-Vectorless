'use client'

import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'
import { DOCUMENTS_QUERY_KEY } from '@/lib/hooks/useDocuments'
import type { Document } from '@/lib/api/types'

interface DocumentCardProps {
  document: Document
}

export function DocumentCard({ document }: DocumentCardProps) {
  const queryClient = useQueryClient()

  // Pattern 2.5: Hover preload
  const handleMouseEnter = () => {
    queryClient.prefetchQuery({
      queryKey: [DOCUMENTS_QUERY_KEY, document.documentId],
      queryFn: () => apiClient.getDocument(document.documentId),
      staleTime: 30_000,
    })
  }

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    processing: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    failed: 'bg-red-100 text-red-800 border-red-200',
  }

  const statusColor = statusColors[document.ingestion.status]

  return (
    <Link
      href={`/documents/${document.documentId}`}
      onMouseEnter={handleMouseEnter}
      onFocus={handleMouseEnter}
      className="block p-4 border rounded-lg hover:shadow-md transition-shadow bg-white"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-lg truncate flex-1">{document.name}</h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded border ${statusColor}`}
        >
          {document.ingestion.status}
        </span>
      </div>

      {document.description && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {document.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>{document.type.toUpperCase()}</span>
        <span>•</span>
        <span>{document.totalPages} pages</span>
        <span>•</span>
        <span>{document.totalNodes} nodes</span>
        {document.domain && (
          <>
            <span>•</span>
            <span className="font-medium">{document.domain}</span>
          </>
        )}
      </div>

      {document.ingestion.errors.length > 0 && (
        <div className="mt-2 text-xs text-red-600">
          {document.ingestion.errors.length} error(s)
        </div>
      )}
    </Link>
  )
}
