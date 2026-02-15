'use client'

import { useState, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { useChatStream, type ChatMessage } from '@/lib/hooks/use-chat-stream'
import { useDocuments } from '@/lib/hooks/useDocuments'
import { isValidDocumentId } from '@/lib/security'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { DocumentSelector } from './DocumentSelector'

interface ChatClientProps {
  sessionId: string
  initialMessages?: ChatMessage[]
}

export function ChatClient({
  sessionId,
  initialMessages = [],
}: ChatClientProps) {
  const searchParams = useSearchParams()
  const rawDocId = searchParams.get('documentId')
  const preSelectedDocId = rawDocId && isValidDocumentId(rawDocId) ? rawDocId : null

  const { data: documents, isLoading: isLoadingDocs, isError: isDocsError } = useDocuments({ status: 'completed' })

  // Map backend Document fields to DocumentSelector format
  const selectorDocuments = useMemo(() => {
    if (!documents) return []
    return documents.map(doc => ({
      id: doc.documentId,
      title: doc.name,
      pageCount: doc.totalPages,
    }))
  }, [documents])

  // Pre-select document from URL param
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>(
    preSelectedDocId ? [preSelectedDocId] : []
  )

  const { messages, isStreaming, sendMessage } = useChatStream(sessionId, initialMessages)

  const handleSend = (message: string) => {
    // H8: Validate selectedDocumentIds before sending
    if (selectedDocumentIds.length === 0) {
      return // Don't send if no documents selected
    }
    sendMessage(message, selectedDocumentIds)
  }

  // H8: Disable input when no documents selected
  const inputDisabled = isStreaming || selectedDocumentIds.length === 0
  const placeholder = selectedDocumentIds.length === 0
    ? 'Select documents first...'
    : 'Ask a question about the selected documents...'

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-3 border-b bg-white">
        <DocumentSelector
          documents={selectorDocuments}
          selectedIds={selectedDocumentIds}
          onSelect={setSelectedDocumentIds}
          isLoading={isLoadingDocs}
        />
      </div>
      {isDocsError && (
        <div className="px-6 py-2 bg-red-50 border-b border-red-200 text-sm text-red-800">
          Failed to load documents. Please refresh the page.
        </div>
      )}
      <MessageList messages={messages} className="flex-1" />
      <ChatInput onSend={handleSend} disabled={inputDisabled} placeholder={placeholder} />
    </div>
  )
}
