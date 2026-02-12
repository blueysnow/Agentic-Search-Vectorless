import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageItem } from '@/components/chat/MessageItem'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'

describe('MessageItem', () => {
  const baseUserMessage: ChatMessage = {
    id: 'msg-1',
    role: 'user',
    content: 'What is revenue?',
    timestamp: Date.now(),
  }

  const baseAssistantMessage: ChatMessage = {
    id: 'msg-2',
    role: 'assistant',
    content: 'The revenue is $2.5M.',
    timestamp: Date.now(),
  }

  it('renders user message with correct styling', () => {
    const { container } = render(<MessageItem message={baseUserMessage} />)

    expect(screen.getByText('What is revenue?')).toBeInTheDocument()
    // Check the root message container has the bg class
    const messageContainer = container.querySelector('.bg-gray-50')
    expect(messageContainer).toBeInTheDocument()
  })

  it('renders assistant message without background', () => {
    render(<MessageItem message={baseAssistantMessage} />)

    expect(screen.getByText('The revenue is $2.5M.')).toBeInTheDocument()
    const container = screen.getByText('The revenue is $2.5M.').closest('div')
    expect(container).not.toHaveClass('bg-gray-50')
  })

  it('displays thinking steps when present', () => {
    const messageWithThinking: ChatMessage = {
      ...baseAssistantMessage,
      thinking: ['Let me check document structure...', 'Now looking at pages 3-5...'],
    }

    render(<MessageItem message={messageWithThinking} />)

    // Text includes arrow prefix, use partial match
    expect(screen.getByText(/Let me check document structure/)).toBeInTheDocument()
    expect(screen.getByText(/Now looking at pages 3-5/)).toBeInTheDocument()
  })

  it('does not render thinking section for user messages', () => {
    const userMessageWithThinking: ChatMessage = {
      ...baseUserMessage,
      thinking: ['This should not appear'],
    }

    render(<MessageItem message={userMessageWithThinking} />)

    expect(screen.queryByText('This should not appear')).not.toBeInTheDocument()
  })

  it('displays metadata badges when present', () => {
    const messageWithMetadata: ChatMessage = {
      ...baseAssistantMessage,
      metadata: {
        doc_name: 'report.pdf',
        pages: '3-5',
      },
    }

    render(<MessageItem message={messageWithMetadata} />)

    expect(screen.getByText('report.pdf')).toBeInTheDocument()
    expect(screen.getByText(/Pages: 3-5/i)).toBeInTheDocument()
  })

  it('displays citations when present', () => {
    const messageWithCitations: ChatMessage = {
      ...baseAssistantMessage,
      citations: [
        { page: 3, text: 'Q4 revenue: $2.5M' },
        { page: 5, text: 'Operating expenses' },
      ],
    }

    render(<MessageItem message={messageWithCitations} />)

    expect(screen.getByText(/Page 3/i)).toBeInTheDocument()
    expect(screen.getByText(/Page 5/i)).toBeInTheDocument()
  })

  it('shows placeholder when assistant message has no content', () => {
    const emptyMessage: ChatMessage = {
      ...baseAssistantMessage,
      content: '',
    }

    render(<MessageItem message={emptyMessage} />)

    expect(screen.getByText('Thinking...')).toBeInTheDocument()
  })

  it('does not show placeholder for user messages with no content', () => {
    const emptyUserMessage: ChatMessage = {
      ...baseUserMessage,
      content: '',
    }

    render(<MessageItem message={emptyUserMessage} />)

    expect(screen.queryByText('Thinking...')).not.toBeInTheDocument()
  })

  it('is wrapped in React.memo for performance', () => {
    // This test verifies the component is memoized
    // memo() wraps the component in a special React element type
    expect(MessageItem.$$typeof).toBeDefined()
  })

  it('renders without thinking steps when empty array', () => {
    const messageWithEmptyThinking: ChatMessage = {
      ...baseAssistantMessage,
      thinking: [],
    }

    const { container } = render(<MessageItem message={messageWithEmptyThinking} />)

    // Should not render thinking container at all
    expect(container.querySelector('[data-testid="thinking-process"]')).not.toBeInTheDocument()
  })

  it('renders without metadata when not present', () => {
    render(<MessageItem message={baseAssistantMessage} />)

    expect(screen.queryByText(/report\.pdf/i)).not.toBeInTheDocument()
  })

  it('renders without citations when not present', () => {
    render(<MessageItem message={baseAssistantMessage} />)

    expect(screen.queryByText(/Page \d+/i)).not.toBeInTheDocument()
  })

  it('displays both user and assistant avatars correctly', () => {
    const { rerender } = render(<MessageItem message={baseUserMessage} />)

    // User avatar should be present (check for 'U' text)
    expect(screen.getByText('U')).toBeInTheDocument()

    rerender(<MessageItem message={baseAssistantMessage} />)

    // Assistant avatar should be present (check for 'AI' text)
    expect(screen.getByText('AI')).toBeInTheDocument()
  })

  it('maintains proper flex layout structure', () => {
    const { container } = render(<MessageItem message={baseUserMessage} />)

    const flexContainer = container.querySelector('.flex.gap-3')
    expect(flexContainer).toBeInTheDocument()
  })
})
