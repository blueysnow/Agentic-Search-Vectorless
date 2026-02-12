'use client'

import { format } from 'date-fns'
import { useDocument } from '@/lib/hooks/useDocuments'
import { TreeVisualization } from '@/components/documents/TreeVisualization'

interface DocumentDetailClientProps {
  documentId: string
}

export function DocumentDetailClient({ documentId }: DocumentDetailClientProps) {
  const { data: document, isLoading, isError, error } = useDocument(documentId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading document...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 border border-red-200 rounded-lg bg-red-50">
        <h3 className="font-semibold text-red-900 mb-2">Error loading document</h3>
        <p className="text-sm text-red-700">{error.message}</p>
      </div>
    )
  }

  if (!document) {
    return (
      <div className="p-6 border rounded-lg text-center">
        <p className="text-muted-foreground">Document not found</p>
      </div>
    )
  }

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    processing: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    failed: 'bg-red-100 text-red-800 border-red-200',
  }

  return (
    <div className="space-y-6">
      <div className="border rounded-lg p-6 bg-white">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-2">{document.name}</h1>
            {document.description && (
              <p className="text-muted-foreground">{document.description}</p>
            )}
          </div>
          <span
            className={`px-3 py-1.5 text-sm font-medium rounded border ${
              statusColors[document.ingestion.status]
            }`}
          >
            {document.ingestion.status}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4 border-t">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Type</p>
            <p className="font-medium">{document.type.toUpperCase()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Pages</p>
            <p className="font-medium">{document.totalPages}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Nodes</p>
            <p className="font-medium">{document.totalNodes}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Tokens</p>
            <p className="font-medium">{document.totalTokens.toLocaleString()}</p>
          </div>
        </div>

        {document.domain && (
          <div className="py-4 border-t">
            <p className="text-xs text-muted-foreground mb-1">Domain</p>
            <p className="font-medium">{document.domain}</p>
          </div>
        )}

        <div className="py-4 border-t grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Created</p>
            <p className="text-sm">
              {format(new Date(document.createdAt), 'PPpp')}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Last Updated</p>
            <p className="text-sm">
              {format(new Date(document.updatedAt), 'PPpp')}
            </p>
          </div>
        </div>

        {document.ingestion.status === 'completed' && document.ingestion.completedAt && (
          <div className="py-4 border-t">
            <p className="text-xs text-muted-foreground mb-1">Processing Completed</p>
            <p className="text-sm">
              {format(new Date(document.ingestion.completedAt), 'PPpp')}
            </p>
            {document.ingestion.model && (
              <p className="text-xs text-muted-foreground mt-1">
                Model: {document.ingestion.model}
              </p>
            )}
          </div>
        )}

        {document.ingestion.errors.length > 0 && (
          <div className="py-4 border-t">
            <p className="text-sm font-medium text-red-900 mb-2">
              Errors ({document.ingestion.errors.length})
            </p>
            <ul className="space-y-1">
              {document.ingestion.errors.map((error, index) => (
                <li key={index} className="text-sm text-red-700">
                  • {error}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {document.ingestion.status === 'completed' && (
        <TreeVisualization rootNodeId={document.rootNodeId} nodes={[]} />
      )}
    </div>
  )
}
