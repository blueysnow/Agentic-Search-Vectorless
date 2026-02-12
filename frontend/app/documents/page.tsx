import { Suspense } from 'react'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { UploadForm } from '@/components/documents/UploadForm'
import { DocumentsClient } from './DocumentsClient'
import { DocumentsSkeleton } from '@/components/skeletons/DocumentsSkeleton'

// Pattern 1.5: Server Component with Suspense boundary
export default function DocumentsPage() {
  return (
    <div className="container mx-auto p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Documents</h1>
        <p className="text-muted-foreground">
          Upload and manage your documents for vectorless RAG processing
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <h2 className="text-xl font-semibold mb-4">Upload New Document</h2>
          <UploadForm />
        </div>

        <div className="lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Your Documents</h2>
          <ErrorBoundary>
            <Suspense fallback={<DocumentsSkeleton />}>
              <DocumentsClient />
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    </div>
  )
}
