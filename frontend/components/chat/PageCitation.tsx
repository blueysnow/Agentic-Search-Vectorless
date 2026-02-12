'use client'

import { sanitizeMarkdown } from '@/lib/security'

interface PageCitationProps {
  page: number
  documentId: string
  excerpt?: string
  onClick?: (data: { page: number; documentId: string }) => void
}

export function PageCitation({ page, documentId, excerpt, onClick }: PageCitationProps) {
  // H-REM4-1: Sanitize excerpt to prevent XSS in ARIA labels and display
  const safeExcerpt = excerpt ? sanitizeMarkdown(excerpt) : ''

  const handleClick = () => {
    onClick?.({ page, documentId })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // H-001: Support Enter and Space keys for keyboard accessibility
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      className="inline-flex flex-col gap-1 px-2 py-1 rounded-md bg-blue-100 text-blue-800 text-xs font-medium hover:bg-blue-200 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label={`Page ${page}${safeExcerpt ? `: ${safeExcerpt}` : ''}`}
      title={`Page ${page}${safeExcerpt ? `: ${safeExcerpt}` : ''}`}
    >
      <span>Page {page}</span>
      {safeExcerpt && (
        <span className="text-blue-700 text-xs line-clamp-2 max-w-xs">
          {safeExcerpt}
        </span>
      )}
    </div>
  )
}
