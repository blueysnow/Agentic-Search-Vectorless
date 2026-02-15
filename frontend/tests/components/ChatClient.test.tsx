import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatClient } from '@/components/chat/ChatClient'
import { apiClient } from '@/lib/api/client'

// Mock the API client
vi.mock('@/lib/api/client')

// Mock useSearchParams
const mockSearchParams = new URLSearchParams()
vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

const mockBackendDocuments = [
  {
    documentId: 'doc-1',
    name: 'Document 1',
    type: 'pdf' as const,
    totalPages: 10,
    totalNodes: 50,
    totalTokens: 1000,
    ingestion: { status: 'completed' as const, errors: [] },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    documentId: 'doc-2',
    name: 'Document 2',
    type: 'pdf' as const,
    totalPages: 20,
    totalNodes: 100,
    totalTokens: 2000,
    ingestion: { status: 'completed' as const, errors: [] },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
]

describe('ChatClient', () => {
  let mockEventSource: any

  // Helper: Select first document
  async function selectFirstDocument(user: any) {
    const docButton = screen.getByText('Select documents')
    await user.click(docButton)
    const doc1 = screen.getByText('Document 1')
    await user.click(doc1)
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Default: return documents from API
    vi.mocked(apiClient.getDocuments).mockResolvedValue(mockBackendDocuments)

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

  it('renders with session ID', async () => {
    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    // H8: Should show "Select documents first" when no documents selected
    expect(screen.getByPlaceholderText(/select documents first/i)).toBeInTheDocument()
  })

  it('renders empty message list initially', async () => {
    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('fetches documents internally and displays them', async () => {
    const user = userEvent.setup()
    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    // Wait for documents to load
    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

    // Open selector to see loaded documents
    const docButton = screen.getByText('Select documents')
    await user.click(docButton)

    await waitFor(() => {
      expect(screen.getByText('Document 1')).toBeInTheDocument()
      expect(screen.getByText('Document 2')).toBeInTheDocument()
    })
  })

  it('shows loading state while fetching documents', async () => {
    // Make getDocuments hang (never resolve)
    vi.mocked(apiClient.getDocuments).mockReturnValue(new Promise(() => {}))

    const user = userEvent.setup()
    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    const docButton = screen.getByText('Select documents')
    await user.click(docButton)

    expect(screen.getByText('Loading documents...')).toBeInTheDocument()
  })

  it('sends message when user types and clicks send', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    // Wait for docs to load then select
    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

    await selectFirstDocument(user)

    const input = screen.getByRole('textbox')
    await user.type(input, 'What is revenue?')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('What is revenue?')).toBeInTheDocument()
    })
  })

  it('disables input when streaming', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

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

    render(<ChatClient sessionId="session-456" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

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

  it('displays initial messages when provided', async () => {
    const initialMessages = [
      {
        id: 'msg-1',
        role: 'user' as const,
        content: 'Previous question',
        timestamp: Date.now(),
      },
    ]

    render(
      <ChatClient sessionId="test-session" initialMessages={initialMessages} />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText('Previous question')).toBeInTheDocument()
  })

  it('renders with default empty initial messages', () => {
    render(<ChatClient sessionId="test-session" />, { wrapper: createWrapper() })

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('integrates MessageList and ChatInput components', () => {
    render(<ChatClient sessionId="test-session" />, { wrapper: createWrapper() })

    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()

    expect(screen.getByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('uses flex layout with proper structure', () => {
    const { container } = render(<ChatClient sessionId="test-session" />, { wrapper: createWrapper() })

    const flexContainer = container.querySelector('.flex.flex-col.h-full')
    expect(flexContainer).toBeInTheDocument()
  })

  it('displays user and assistant messages after streaming', async () => {
    const user = userEvent.setup()

    render(<ChatClient sessionId="test-session" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

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

  it('renders DocumentSelector component', async () => {
    render(
      <ChatClient sessionId="test-session" />,
      { wrapper: createWrapper() }
    )

    expect(screen.getByText(/select documents/i)).toBeInTheDocument()
  })

  it('allows changing selected documents mid-conversation', async () => {
    const user = userEvent.setup()

    render(
      <ChatClient sessionId="test-session" />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

    // Open document selector
    const selectorButton = screen.getAllByRole('button')[0]
    await user.click(selectorButton)

    await waitFor(() => {
      expect(screen.getByText('Document 1')).toBeInTheDocument()
    })

    // Select a document
    await user.click(screen.getByText('Document 1'))

    await waitFor(() => {
      expect(screen.getByText(/1 documents? selected/i)).toBeInTheDocument()
    })
  })

  it('sends message with selected document IDs', async () => {
    const user = userEvent.setup()

    render(
      <ChatClient sessionId="test-session" />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalled()
    })

    // Select a document
    const selectorButton = screen.getAllByRole('button')[0]
    await user.click(selectorButton)

    await waitFor(() => {
      expect(screen.getByText('Document 1')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Document 1'))

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
