'use client'

import { useState } from 'react'
import { downloadConversation } from '@/lib/export-conversation'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'

interface ExportButtonProps {
  messages: ChatMessage[]
  sessionId?: string
  documentIds?: string[]
}

export function ExportButton({ messages, sessionId, documentIds }: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  const handleExport = (format: 'markdown' | 'json') => {
    const metadata = {
      sessionId,
      documentIds,
      exportedAt: new Date().toISOString(),
    }

    downloadConversation(messages, format, undefined, metadata)
    setIsOpen(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // H-004: Close dropdown with Escape key
    if (e.key === 'Escape' && isOpen) {
      setIsOpen(false)
    }
  }

  const disabled = messages.length === 0

  return (
    <div className="relative" onKeyDown={handleKeyDown}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        aria-label="Export conversation"
        aria-expanded={isOpen}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Export
      </button>

      {isOpen && !disabled && (
        <div className="absolute right-0 z-10 mt-2 w-48 bg-white border rounded-lg shadow-lg">
          <button
            type="button"
            onClick={() => handleExport('markdown')}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 focus:bg-gray-100 rounded-t-lg focus:outline-none"
          >
            Export as Markdown
          </button>
          <button
            type="button"
            onClick={() => handleExport('json')}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 focus:bg-gray-100 rounded-b-lg focus:outline-none"
          >
            Export as JSON
          </button>
        </div>
      )}
    </div>
  )
}
