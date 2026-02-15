'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { ChatClient } from '@/components/chat/ChatClient'

function QueryPageContent() {
  const searchParams = useSearchParams()
  const urlSessionId = searchParams.get('sessionId')
  const sessionId = urlSessionId || `session-${Date.now()}`

  return (
    <div className="h-full flex flex-col">
      <div className="border-b px-6 py-4 bg-white">
        <h1 className="text-2xl font-semibold">Query</h1>
        <p className="text-sm text-gray-600">Ask questions about your documents</p>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatClient key={sessionId} sessionId={sessionId} />
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
