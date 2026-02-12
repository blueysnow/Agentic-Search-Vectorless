import { Skeleton } from '@/components/ui/skeleton'

/**
 * Loading skeleton for chat messages
 * Matches MessageList layout
 */
export function ChatSkeleton() {
  return (
    <div className="space-y-6 p-6" role="status" aria-label="Loading messages">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="space-y-3" data-testid="message-skeleton">
          {/* User message */}
          <div className="flex justify-end">
            <div className="max-w-[80%] space-y-2">
              <Skeleton className="h-4 w-24 ml-auto" />
              <Skeleton className="h-16 w-full rounded-lg" />
            </div>
          </div>

          {/* Assistant response */}
          <div className="flex justify-start">
            <div className="max-w-[80%] space-y-2">
              <Skeleton className="h-4 w-28" />
              {/* Thinking process */}
              <Skeleton className="h-12 w-full rounded-lg" />
              {/* Response content */}
              <Skeleton className="h-24 w-full rounded-lg" />
              {/* Citations */}
              <div className="flex gap-2">
                <Skeleton className="h-6 w-20" />
                <Skeleton className="h-6 w-24" />
              </div>
            </div>
          </div>
        </div>
      ))}
      <span className="sr-only">Loading messages</span>
    </div>
  )
}
