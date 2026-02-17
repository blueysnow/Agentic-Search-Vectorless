'use client'

import { memo } from 'react'
import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'
import { ThinkingProcess } from './ThinkingProcess'
import { PageCitation } from './PageCitation'

// Pattern 6.3: Hoist static JSX elements
const USER_AVATAR = (
  <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
    <span className="text-white text-sm font-medium">U</span>
  </div>
)

const ASSISTANT_AVATAR = (
  <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0">
    <span className="text-white text-sm font-medium">AI</span>
  </div>
)

interface MessageItemProps {
  message: ChatMessage
}

// Pattern 5.2: Memoize MessageItem to prevent re-renders during streaming
export const MessageItem = memo(function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 p-4 ${isUser ? 'bg-gray-50' : ''}`}>
      {isUser ? USER_AVATAR : ASSISTANT_AVATAR}

      <div className="flex-1 space-y-2 min-w-0">
        {/* Thinking steps (assistant only) */}
        {!isUser && message.thinking && message.thinking.length > 0 && (
          <ThinkingProcess steps={message.thinking} />
        )}

        {/* Main content */}
        <div className="prose prose-sm max-w-none">
          {message.content ? (
            isUser ? (
              message.content
            ) : (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            )
          ) : (
            !isUser && <span className="text-gray-400">Thinking...</span>
          )}
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.citations.map((citation, idx) => {
              // H9: Use documentId from citation or fallback to message metadata
              const citationWithDoc = citation as { page: number; text: string; documentId?: string }
              const docIdFromCitation = citationWithDoc.documentId
              const docIdFromMetadata = typeof message.metadata?.doc_id === 'string'
                ? message.metadata.doc_id
                : typeof message.metadata?.doc_name === 'string'
                ? message.metadata.doc_name
                : 'unknown'
              const documentId = docIdFromCitation || docIdFromMetadata

              return (
                <PageCitation
                  key={idx}
                  page={citation.page}
                  documentId={documentId}
                  excerpt={citation.text}
                />
              )
            })}
          </div>
        )}

        {/* Metadata badges */}
        {message.metadata && (
          <div className="flex gap-2 text-xs text-gray-500">
            {message.metadata.doc_name && (
              <span className="px-2 py-1 bg-gray-100 rounded">{message.metadata.doc_name}</span>
            )}
            {message.metadata.pages && (
              <span className="px-2 py-1 bg-gray-100 rounded">Pages: {message.metadata.pages}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
})
