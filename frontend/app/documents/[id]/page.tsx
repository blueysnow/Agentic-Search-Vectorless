import { Suspense } from 'react'
import Link from 'next/link'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { DocumentDetailClient } from './DocumentDetailClient'

// Pattern 1.5: Server Component with Suspense
export default async function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params

  return (
    <div className="container mx-auto p-8 space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/documents"
          className="text-blue-600 hover:underline flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
          Back to Documents
        </Link>
      </div>

      <ErrorBoundary>
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading document details...</p>
              </div>
            </div>
          }
        >
          <DocumentDetailClient documentId={id} />
        </Suspense>
      </ErrorBoundary>
    </div>
  )
}
