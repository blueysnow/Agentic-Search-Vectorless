'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { ChatClient } from '@/components/chat/ChatClient'

function ChatPageContent() {
  // H-REM3-4: Read sessionId from URL params for resume functionality
  const searchParams = useSearchParams()
  const urlSessionId = searchParams.get('sessionId')

  // Use URL sessionId if present, otherwise generate new one
  const sessionId = urlSessionId || `session-${Date.now()}`

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b px-6 py-4 bg-white">
        <h1 className="text-2xl font-semibold">Chat</h1>
        <p className="text-sm text-gray-600">Ask questions about your documents</p>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatClient key={sessionId} sessionId={sessionId} />
      </div>
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="h-screen flex items-center justify-center">Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  )
}
