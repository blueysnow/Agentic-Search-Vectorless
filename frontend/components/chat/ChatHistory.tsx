'use client'

import { useRouter } from 'next/navigation'
import { useSessions } from '@/lib/hooks/use-sessions'
import { useMutation, useQueryClient } from '@tanstack/react-query'

interface ChatHistoryProps {
  currentSessionId: string
}

export function ChatHistory({ currentSessionId }: ChatHistoryProps) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { data: sessions, isLoading } = useSessions({ limit: 30 })

  const deleteMutation = useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete session')
      return sessionId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const handleNewChat = () => {
    router.push('/query')
  }

  const handleSelectSession = (sessionId: string) => {
    router.push(`/query?sessionId=${sessionId}`)
  }

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirm('Delete this conversation?')) {
      deleteMutation.mutate(sessionId)
    }
  }

  return (
    <div className="w-64 border-r bg-gray-50 flex flex-col h-full flex-shrink-0">
      <div className="p-3 border-b">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium cursor-pointer transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="px-3 py-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/2" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && sessions && sessions.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-gray-400">No conversations yet</p>
          </div>
        )}

        {sessions?.map((session) => {
          const isActive = session.id === currentSessionId
          return (
            <button
              key={session.id}
              onClick={() => handleSelectSession(session.id)}
              className={`group w-full text-left px-3 py-3 border-b border-gray-100 hover:bg-gray-100 transition-colors cursor-pointer ${
                isActive ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
              }`}
            >
              <p className="text-sm font-medium text-gray-900 truncate pr-6">
                {session.preview}
              </p>
              <div className="flex items-center justify-between mt-1">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span>{session.messageCount} msgs</span>
                  <span>&middot;</span>
                  <span>{formatDate(session.createdAt)}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, session.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity cursor-pointer"
                  title="Delete conversation"
                >
                  <TrashIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  )
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
    </svg>
  )
}
