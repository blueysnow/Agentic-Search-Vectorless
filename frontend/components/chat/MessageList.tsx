'use client'

import { useEffect, useRef, useMemo } from 'react'
import { MessageItem } from './MessageItem'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'
import { throttle } from '@/lib/performance'

interface MessageListProps {
  messages: ChatMessage[]
  className?: string
}

export function MessageList({ messages, className = '' }: MessageListProps) {
  const scrollAnchorRef = useRef<HTMLDivElement>(null)

  // H7: Throttle scroll to 1x per 100ms to prevent jank
  // H-REM3-1: Use cleanup function to prevent timeout leak
  const { throttled: throttledScroll, cleanup } = useMemo(
    () =>
      throttle(() => {
        scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' })
      }, 100),
    []
  )

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    throttledScroll()
    // Cleanup timeout on unmount
    return cleanup
  }, [messages, throttledScroll, cleanup])

  if (messages.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center h-full text-gray-500 ${className}`}>
        <p className="text-lg font-medium">No messages yet</p>
        <p className="text-sm">Start a conversation by typing a message below</p>
      </div>
    )
  }

  return (
    <div className={`flex flex-col overflow-y-auto ${className}`}>
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      <div ref={scrollAnchorRef} data-scroll-anchor />
    </div>
  )
}
