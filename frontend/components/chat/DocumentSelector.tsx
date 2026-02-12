'use client'

import { useState, useMemo } from 'react'
import { isValidDocumentId } from '@/lib/security'

interface Document {
  id: string
  title: string
  pageCount: number
}

interface DocumentSelectorProps {
  documents: Document[]
  selectedIds: string[]
  onSelect: (ids: string[]) => void
}

export function DocumentSelector({ documents, selectedIds, onSelect }: DocumentSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  // Vercel Pattern 7.11: Use Set for O(1) document ID lookups
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  const handleToggle = (docId: string) => {
    // H4: Validate document ID to prevent path traversal
    if (!isValidDocumentId(docId)) {
      console.warn('Invalid document ID rejected:', docId)
      return
    }

    const isSelected = selectedSet.has(docId)

    if (isSelected) {
      // Remove from selection - convert Set to array
      const newSelectedIds = selectedIds.filter(id => id !== docId)
      onSelect(newSelectedIds)
    } else {
      // Add to selection
      onSelect([...selectedIds, docId])
    }
  }

  const selectedCount = selectedIds.length
  const displayText = selectedCount === 0
    ? 'Select documents'
    : `${selectedCount} documents selected`

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-4 py-2 text-sm border rounded-lg bg-white hover:bg-gray-50"
      >
        <span>{displayText}</span>
        <svg
          className="w-4 h-4 ml-2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-multiselectable="true"
          className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto"
        >
          {documents.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500">
              No documents available
            </div>
          ) : (
            documents.map(doc => {
              const isSelected = selectedSet.has(doc.id)

              return (
                <div
                  key={doc.id}
                  role="option"
                  aria-selected={isSelected ? 'true' : 'false'}
                  className="flex items-center px-4 py-3 hover:bg-gray-50 cursor-pointer"
                  onClick={(e) => {
                    e.preventDefault()
                    handleToggle(doc.id)
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggle(doc.id)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    tabIndex={-1}
                  />
                  <div className="ml-3 flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      {doc.title}
                    </div>
                    <div className="text-xs text-gray-500">
                      {doc.pageCount} pages
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
