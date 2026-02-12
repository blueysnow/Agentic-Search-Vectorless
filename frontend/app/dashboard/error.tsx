'use client'

import Link from 'next/link'
import { useEffect } from 'react'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Dashboard error:', error)
  }, [error])

  return (
    <div className="container mx-auto p-8">
      <div className="max-w-md mx-auto text-center">
        <h2 className="text-2xl font-bold mb-4">Dashboard Error</h2>
        <p className="text-muted-foreground mb-8">
          {process.env.NODE_ENV === 'development'
            ? error.message
            : 'Unable to load dashboard. Please try again.'}
        </p>
        <div className="flex gap-4 justify-center">
          <button
            onClick={reset}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
          >
            Try again
          </button>
          <Link
            href="/"
            className="px-6 py-3 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition-opacity"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  )
}
