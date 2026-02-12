'use client'

import { useRouter } from 'next/navigation'
import { useSession } from '@/lib/hooks/use-sessions'
import { ExportButton } from '@/components/chat/ExportButton'
import { MessageList } from '@/components/chat/MessageList'

interface SessionDetailPageProps {
  params: Promise<{ id: string }>
}

export default function SessionDetailPage({ params }: SessionDetailPageProps) {
  const router = useRouter()
  const [sessionId, setSessionId] = React.useState<string | null>(null)

  // Unwrap params Promise for Next.js 15
  React.useEffect(() => {
    params.then(p => setSessionId(p.id)).catch(err => {
      console.error('Failed to resolve params:', err)
      // Set null to trigger error UI
      setSessionId(null)
    })
  }, [params])

  const { data: session, isLoading, isError } = useSession(sessionId || undefined)

  if (!sessionId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">Failed to load conversation. It may have been deleted.</p>
            <button
              onClick={() => router.push('/sessions')}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Back to sessions
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading conversation...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <button
              onClick={() => router.push('/sessions')}
              className="text-sm text-blue-600 hover:text-blue-800 mb-2"
            >
              ← Back to sessions
            </button>
            <h1 className="text-3xl font-bold text-gray-900">Conversation Details</h1>
            <div className="flex gap-4 text-sm text-gray-600 mt-2">
              <span>{session.messages.length} messages</span>
              <span>{session.documentIds.length} documents</span>
              <span>{new Date(session.createdAt).toLocaleDateString()}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <ExportButton
              messages={session.messages}
              sessionId={session.id}
              documentIds={session.documentIds}
            />
            <button
              onClick={() => router.push(`/chat?sessionId=${session.id}`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              Resume
            </button>
          </div>
        </div>

        {/* Document badges */}
        {session.documentIds.length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-medium text-gray-700 mb-2">Documents Used</h2>
            <div className="flex flex-wrap gap-2">
              {session.documentIds.map((docId) => (
                <span
                  key={docId}
                  className="px-3 py-1 bg-white border rounded-full text-sm text-gray-700"
                >
                  {docId}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Full Conversation */}
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-900">Full Conversation</h2>
          </div>
          <div className="h-[600px] overflow-y-auto">
            <MessageList messages={session.messages} />
          </div>
        </div>
      </div>
    </div>
  )
}

// Need to import React for hooks
import React from 'react'
