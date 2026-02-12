import { Skeleton } from '@/components/ui/skeleton'

/**
 * Loading skeleton for sessions list page
 * Matches session card layout dimensions
 */
export function SessionsSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading conversations">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="bg-white rounded-lg border p-6"
          data-testid="session-skeleton"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 space-y-3">
              {/* Session title/preview */}
              <Skeleton className="h-6 w-2/3" />

              {/* Metadata row */}
              <div className="flex gap-4">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-28" />
              </div>

              {/* Document tags */}
              <div className="flex gap-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-20" />
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 ml-4">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="h-9 w-16" />
              <Skeleton className="h-9 w-20" />
            </div>
          </div>
        </div>
      ))}
      <span className="sr-only">Loading conversations</span>
    </div>
  )
}
