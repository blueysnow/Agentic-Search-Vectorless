import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DocumentCard } from '@/components/documents/DocumentCard'
import type { Document } from '@/lib/api/types'

// Mock next/navigation
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
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

const mockDocument: Document = {
  documentId: 'doc1',
  name: 'Test Document.pdf',
  type: 'pdf',
  domain: 'science',
  description: 'A test document for unit testing',
  totalPages: 10,
  totalNodes: 50,
  totalTokens: 1000,
  rootNodeId: 'root1',
  ingestion: {
    status: 'completed',
    model: 'gpt-4',
    startedAt: '2024-01-01T00:00:00Z',
    completedAt: '2024-01-01T00:10:00Z',
    errors: [],
  },
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:10:00Z',
}

describe('DocumentCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render document information', () => {
    render(createElement(DocumentCard, { document: mockDocument }), {
      wrapper: createWrapper(),
    })

    expect(screen.getByText('Test Document.pdf')).toBeInTheDocument()
    expect(screen.getByText('A test document for unit testing')).toBeInTheDocument()
    expect(screen.getByText('10 pages')).toBeInTheDocument()
    expect(screen.getByText('50 nodes')).toBeInTheDocument()
    expect(screen.getByText('science')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
  })

  it('should display correct status badge color', () => {
    const { rerender } = render(
      createElement(DocumentCard, { document: mockDocument }),
      { wrapper: createWrapper() }
    )

    let statusBadge = screen.getByText('completed')
    expect(statusBadge).toHaveClass('bg-green-100')

    const processingDoc = { ...mockDocument, ingestion: { ...mockDocument.ingestion, status: 'processing' as const } }
    rerender(
      createElement(DocumentCard, { document: processingDoc })
    )

    statusBadge = screen.getByText('processing')
    expect(statusBadge).toHaveClass('bg-blue-100')
  })

  it('should show error count when errors exist', () => {
    const docWithErrors = {
      ...mockDocument,
      ingestion: {
        ...mockDocument.ingestion,
        status: 'failed' as const,
        errors: ['Error 1', 'Error 2'],
      },
    }

    render(createElement(DocumentCard, { document: docWithErrors }), {
      wrapper: createWrapper(),
    })

    expect(screen.getByText('2 error(s)')).toBeInTheDocument()
  })

  it('should not show description if not provided', () => {
    const docWithoutDesc = { ...mockDocument, description: undefined }

    render(createElement(DocumentCard, { document: docWithoutDesc }), {
      wrapper: createWrapper(),
    })

    expect(screen.queryByText('A test document for unit testing')).not.toBeInTheDocument()
  })

  it('should link to document detail page', () => {
    render(createElement(DocumentCard, { document: mockDocument }), {
      wrapper: createWrapper(),
    })

    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('href', '/documents/doc1')
  })

  it('should show Chat button for completed documents', () => {
    render(createElement(DocumentCard, { document: mockDocument }), {
      wrapper: createWrapper(),
    })

    const chatButton = screen.getByRole('button', { name: /chat about/i })
    expect(chatButton).toBeInTheDocument()
  })

  it('should not show Chat button for non-completed documents', () => {
    const pendingDoc = {
      ...mockDocument,
      ingestion: { ...mockDocument.ingestion, status: 'processing' as const },
    }

    render(createElement(DocumentCard, { document: pendingDoc }), {
      wrapper: createWrapper(),
    })

    expect(screen.queryByRole('button', { name: /chat about/i })).not.toBeInTheDocument()
  })

  it('should navigate to /query?documentId=xxx when Chat button is clicked', async () => {
    const user = userEvent.setup()
    render(createElement(DocumentCard, { document: mockDocument }), {
      wrapper: createWrapper(),
    })

    const chatButton = screen.getByRole('button', { name: /chat about/i })
    await user.click(chatButton)

    expect(mockPush).toHaveBeenCalledWith('/query?documentId=doc1')
  })
})
