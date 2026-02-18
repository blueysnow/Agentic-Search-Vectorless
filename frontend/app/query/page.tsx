'use client'

import { Suspense, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { ChatClient } from '@/components/chat/ChatClient'
import { ChatHistory } from '@/components/chat/ChatHistory'
import { useSession } from '@/lib/hooks/use-sessions'

function QueryPageContent() {
  const searchParams = useSearchParams()
  const urlSessionId = searchParams.get('sessionId')

  // Stable sessionId: use URL param or generate new one (memoized to avoid regeneration)
  const sessionId = useMemo(
    () => urlSessionId || `session-${Date.now()}`,
    [urlSessionId]
  )

  // Load existing session messages when resuming a previous session
  const { data: existingSession, isLoading: isLoadingSession } = useSession(
    urlSessionId || undefined
  )

  const initialMessages = existingSession?.messages || []

  return (
    <div className="h-full flex flex-col">
      <div className="border-b px-6 py-4 bg-white">
        <h1 className="text-2xl font-semibold">Query</h1>
        <p className="text-sm text-gray-600">Ask questions about your documents</p>
      </div>
      <div className="flex-1 overflow-hidden flex">
        <ChatHistory currentSessionId={sessionId} />
        <div className="flex-1 overflow-hidden">
          {urlSessionId && isLoadingSession ? (
            <div className="flex-1 h-full flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3" />
                <p className="text-sm text-gray-500">Loading conversation...</p>
              </div>
            </div>
          ) : (
            <ChatClient
              key={sessionId}
              sessionId={sessionId}
              initialMessages={initialMessages}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default function QueryPage() {
  return (
    <Suspense fallback={<div className="h-full flex items-center justify-center">Loading...</div>}>
      <QueryPageContent />
    </Suspense>
  )
}
