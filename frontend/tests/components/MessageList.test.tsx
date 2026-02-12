import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from '@/components/chat/MessageList'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'

describe('MessageList', () => {
  const mockMessages: ChatMessage[] = [
    {
      id: 'msg-1',
      role: 'user',
      content: 'First message',
      timestamp: Date.now() - 2000,
    },
    {
      id: 'msg-2',
      role: 'assistant',
      content: 'First response',
      timestamp: Date.now() - 1000,
    },
    {
      id: 'msg-3',
      role: 'user',
      content: 'Second message',
      timestamp: Date.now(),
    },
  ]

  beforeEach(() => {
    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('renders all messages in order', () => {
    render(<MessageList messages={mockMessages} />)

    expect(screen.getByText('First message')).toBeInTheDocument()
    expect(screen.getByText('First response')).toBeInTheDocument()
    expect(screen.getByText('Second message')).toBeInTheDocument()
  })

  it('renders messages in chronological order', () => {
    const { container } = render(<MessageList messages={mockMessages} />)

    const messageContents = Array.from(
      container.querySelectorAll('.prose')
    ).map((el) => el.textContent)

    expect(messageContents).toEqual(['First message', 'First response', 'Second message'])
  })

  it('renders empty state when no messages', () => {
    render(<MessageList messages={[]} />)

    expect(screen.getByText(/No messages yet/i)).toBeInTheDocument()
    expect(screen.getByText(/Start a conversation/i)).toBeInTheDocument()
  })

  it('applies overflow-y-auto for scrolling', () => {
    const { container } = render(<MessageList messages={mockMessages} />)

    const scrollContainer = container.querySelector('.overflow-y-auto')
    expect(scrollContainer).toBeInTheDocument()
  })

  it('includes scroll anchor element at bottom', () => {
    const { container } = render(<MessageList messages={mockMessages} />)

    const scrollAnchor = container.querySelector('[data-scroll-anchor]')
    expect(scrollAnchor).toBeInTheDocument()
  })

  it('calls scrollIntoView on scroll anchor when messages update', () => {
    const { rerender } = render(<MessageList messages={mockMessages} />)

    const scrollIntoViewMock = Element.prototype.scrollIntoView as any

    // Add a new message
    const newMessages: ChatMessage[] = [
      ...mockMessages,
      {
        id: 'msg-4',
        role: 'assistant' as const,
        content: 'New response',
        timestamp: Date.now(),
      },
    ]

    rerender(<MessageList messages={newMessages} />)

    // scrollIntoView should have been called
    expect(scrollIntoViewMock).toHaveBeenCalled()
  })

  it('uses smooth scrolling behavior', () => {
    render(<MessageList messages={mockMessages} />)

    const scrollIntoViewMock = Element.prototype.scrollIntoView as any

    // Check that smooth behavior was used
    expect(scrollIntoViewMock).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    )
  })

  it('renders with proper flex layout', () => {
    const { container } = render(<MessageList messages={mockMessages} />)

    const flexContainer = container.querySelector('.flex.flex-col')
    expect(flexContainer).toBeInTheDocument()
  })

  it('applies className prop when provided', () => {
    const { container } = render(
      <MessageList messages={mockMessages} className="custom-class" />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('handles single message', () => {
    const singleMessage = [mockMessages[0]]

    render(<MessageList messages={singleMessage} />)

    expect(screen.getByText('First message')).toBeInTheDocument()
    expect(screen.queryByText('First response')).not.toBeInTheDocument()
  })

  it('renders MessageItem components for each message', () => {
    const { container } = render(<MessageList messages={mockMessages} />)

    // Each message should have the message item structure
    const messageItems = container.querySelectorAll('.flex.gap-3.p-4')
    expect(messageItems).toHaveLength(mockMessages.length)
  })
})
