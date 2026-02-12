'use client'

import { useState } from 'react'
import { useChatStream, type ChatMessage } from '@/lib/hooks/use-chat-stream'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { DocumentSelector } from './DocumentSelector'

interface ChatClientProps {
  sessionId: string
  initialMessages?: ChatMessage[]
  availableDocuments?: Array<{ id: string; title: string; pageCount: number }>
}

export function ChatClient({
  sessionId,
  initialMessages = [],
  availableDocuments = []
}: ChatClientProps) {
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([])
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
          documents={availableDocuments}
          selectedIds={selectedDocumentIds}
          onSelect={setSelectedDocumentIds}
        />
      </div>
      <MessageList messages={messages} className="flex-1" />
      <ChatInput onSend={handleSend} disabled={inputDisabled} placeholder={placeholder} />
    </div>
  )
}
