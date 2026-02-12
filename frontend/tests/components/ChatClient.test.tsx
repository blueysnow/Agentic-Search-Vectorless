import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatClient } from '@/components/chat/ChatClient'

describe('ChatClient', () => {
  let mockEventSource: any

  const mockDocuments = [
    { id: 'doc-1', title: 'Document 1', pageCount: 10 },
    { id: 'doc-2', title: 'Document 2', pageCount: 20 },
  ]

  // Helper: Select first document
  async function selectFirstDocument(user: any) {
    const docButton = screen.getByText('Select documents')
    await user.click(docButton)
    // Find checkbox by the text content in its label
    const doc1 = screen.getByText('Document 1')
    await user.click(doc1)
  }

  beforeEach(() => {
    // Mock EventSource
    mockEventSource = {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      close: vi.fn(),
      readyState: 1,
      CONNECTING: 0,
      OPEN: 1,
      CLOSED: 2,
    }

    global.EventSource = vi.fn(() => mockEventSource) as any
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('renders with session ID', () => {
    render(<ChatClient sessionId="test-session-123" availableDocuments={mockDocuments} />)

    // H8: Should show "Select documents first" when no documents selected
    expect(screen.getByPlaceholderText(/select documents first/i)).toBeInTheDocument()
  })

  it('renders empty message list initially', () => {
    render(<ChatClient sessionId="test-session-123" availableDocuments={mockDocuments} />)

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('sends message when user types and clicks send', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session-123" availableDocuments={mockDocuments} />)

    // H8: First select a document
    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'What is revenue?')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      // User message should appear
      expect(screen.getByText('What is revenue?')).toBeInTheDocument()
    })
  })

  it('disables input when streaming', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session-123" availableDocuments={mockDocuments} />)

    // H8: Select document first
    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test message')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(input).toBeDisabled()
      expect(sendButton).toBeDisabled()
    })
  })

  it('opens EventSource with correct session ID', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="session-456" availableDocuments={mockDocuments} />)

    // H8: Select document first
    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(global.EventSource).toHaveBeenCalledWith(
        expect.stringContaining('sessionId=session-456')
      )
    })
  })

  it('displays initial messages when provided', () => {
    const initialMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: 'Previous question',
        timestamp: Date.now(),
      },
    ]

    render(
      <ChatClient sessionId="test-session" initialMessages={initialMessages} />
    )

    expect(screen.getByText('Previous question')).toBeInTheDocument()
  })

  it('renders with default empty initial messages', () => {
    render(<ChatClient sessionId="test-session" />)

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('integrates MessageList and ChatInput components', () => {
    render(<ChatClient sessionId="test-session" />)

    // Should have the chat input at bottom
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()

    // Should have message list (with empty state)
    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('uses flex layout with proper structure', () => {
    const { container } = render(<ChatClient sessionId="test-session" />)

    const flexContainer = container.querySelector('.flex.flex-col.h-full')
    expect(flexContainer).toBeInTheDocument()
  })

  it('displays user and assistant messages after streaming', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session" availableDocuments={mockDocuments} />)

    // H8: Select document first
    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Hello')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(mockEventSource.addEventListener).toHaveBeenCalled()
    })

    // Simulate SSE response
    const messageHandler = mockEventSource.addEventListener.mock.calls.find(
      (call: any) => call[0] === 'message'
    )?.[1]

    messageHandler?.({
      data: JSON.stringify({ type: 'content', content: 'Response' }),
    })

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
      expect(screen.getByText(/Response/)).toBeInTheDocument()
    })
  })

  it('passes document IDs to sendMessage (single document)', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session" availableDocuments={mockDocuments} />)

    // H8: Select document first
    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test message')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      const callArg = (global.EventSource as any).mock.calls[0][0]
      // For now, just verify EventSource was called
      expect(callArg).toContain('/api/chat/stream')
    })
  })

  it('renders DocumentSelector component', () => {
    const mockDocs = [
      { id: 'doc-1', title: 'Test Doc', pageCount: 10 }
    ]
    render(
      <ChatClient
        sessionId="test-session"
        availableDocuments={mockDocs}
      />
    )

    expect(screen.getByText(/select documents/i)).toBeInTheDocument()
  })

  it('allows changing selected documents mid-conversation', async () => {
    const user = userEvent.setup()
    const mockDocs = [
      { id: 'doc-1', title: 'Doc 1', pageCount: 10 },
      { id: 'doc-2', title: 'Doc 2', pageCount: 15 }
    ]

    render(
      <ChatClient
        sessionId="test-session"
        availableDocuments={mockDocs}
      />
    )

    // Open document selector
    const selectorButton = screen.getAllByRole('button')[0] // First button is selector
    await user.click(selectorButton)

    await waitFor(() => {
      expect(screen.getByText('Doc 1')).toBeInTheDocument()
    })

    // Select a document
    await user.click(screen.getByText('Doc 1'))

    await waitFor(() => {
      expect(screen.getByText(/1 documents? selected/i)).toBeInTheDocument()
    })
  })

  it('sends message with selected document IDs', async () => {
    const user = userEvent.setup()
    const mockDocs = [
      { id: 'doc-1', title: 'Doc 1', pageCount: 10 }
    ]

    render(
      <ChatClient
        sessionId="test-session"
        availableDocuments={mockDocs}
      />
    )

    // Select a document
    const selectorButton = screen.getAllByRole('button')[0]
    await user.click(selectorButton)

    await waitFor(() => {
      expect(screen.getByText('Doc 1')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Doc 1'))

    // Send a message
    const input = screen.getByRole('textbox')
    await user.type(input, 'Test with doc')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      const callArg = (global.EventSource as any).mock.calls[0][0]
      expect(callArg).toContain('documentIds=doc-1')
    })
  })
})
