'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSessions } from '@/lib/hooks/use-sessions'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { SessionsSkeleton } from '@/components/skeletons/SessionsSkeleton'
import { toast } from '@/lib/hooks/use-toast'

export default function SessionsPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [documentFilter, setDocumentFilter] = useState<string>('')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  const { data: sessions, isLoading, isError } = useSessions({
    documentId: documentFilter || undefined,
    startDate: startDate || undefined,
    endDate: endDate || undefined,
  })

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
      toast({
        title: 'Conversation deleted',
        description: 'The conversation has been removed.',
      })
    },
    onError: () => {
      toast({
        variant: 'destructive',
        title: 'Delete failed',
        description: 'Could not delete conversation. Please try again.',
      })
    },
  })

  const handleResumeSession = (sessionId: string) => {
    router.push(`/chat?sessionId=${sessionId}`)
  }

  const handleDeleteSession = async (sessionId: string) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      deleteMutation.mutate(sessionId)
    }
  }

  const clearFilters = () => {
    setDocumentFilter('')
    setStartDate('')
    setEndDate('')
  }

  if (isError) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load conversations. Please try again.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Conversation History</h1>
          <p className="text-gray-600 mt-2">View and manage your past conversations</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="document-filter" className="block text-sm font-medium text-gray-700 mb-1">
                Filter by Document
              </label>
              <input
                id="document-filter"
                type="text"
                value={documentFilter}
                onChange={(e) => setDocumentFilter(e.target.value)}
                placeholder="Document ID"
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {(documentFilter || startDate || endDate) && (
            <button
              onClick={clearFilters}
              className="mt-4 text-sm text-blue-600 hover:text-blue-800 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Loading State */}
        {isLoading && <SessionsSkeleton />}

        {/* Empty State */}
        {!isLoading && sessions && sessions.length === 0 && (
          <div className="bg-white rounded-lg border p-8 text-center">
            <p className="text-gray-600">No conversations found</p>
            <button
              onClick={() => router.push('/chat')}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Start a new conversation
            </button>
          </div>
        )}

        {/* Sessions List */}
        {!isLoading && sessions && sessions.length > 0 && (
          <div className="space-y-4">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="bg-white rounded-lg border p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-2">
                      {session.preview}
                    </h3>

                    <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
                      <span>{session.messageCount} messages</span>
                      <span>{session.documentIds.length} documents</span>
                      <span>
                        {new Date(session.createdAt).toLocaleDateString()}
                      </span>
                    </div>

                    {session.documentIds.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {session.documentIds.map((docId) => (
                          <span
                            key={docId}
                            className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                          >
                            {docId}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleResumeSession(session.id)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      Resume
                    </button>
                    <button
                      onClick={() => router.push(`/sessions/${session.id}`)}
                      className="px-4 py-2 border rounded-lg hover:bg-gray-50 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleDeleteSession(session.id)}
                      disabled={deleteMutation.isPending}
                      className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 text-sm disabled:opacity-50 cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
