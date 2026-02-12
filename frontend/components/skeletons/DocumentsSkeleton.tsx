import { Skeleton } from '@/components/ui/skeleton'

/**
 * Loading skeleton for documents list page
 * Matches DocumentCard layout dimensions
 */
export function DocumentsSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading documents">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="border rounded-lg p-6 space-y-3"
          data-testid="document-skeleton"
        >
          {/* Title */}
          <Skeleton className="h-6 w-3/4" />

          {/* Metadata row */}
          <div className="flex items-center gap-4">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>

          {/* Tree stats */}
          <div className="flex items-center gap-4">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <Skeleton className="h-9 w-20" />
            <Skeleton className="h-9 w-20" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading documents</span>
    </div>
  )
}
