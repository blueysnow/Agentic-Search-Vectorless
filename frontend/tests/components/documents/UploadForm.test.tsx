import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement, type ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UploadForm } from '@/components/documents/UploadForm'
import { apiClient } from '@/lib/api/client'

vi.mock('@/lib/api/client')

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

describe('UploadForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render form fields', () => {
    render(createElement(UploadForm), { wrapper: createWrapper() })

    expect(screen.getByLabelText(/document file/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/domain/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument()
  })

  it('should show file size and type requirements', () => {
    render(createElement(UploadForm), { wrapper: createWrapper() })

    expect(screen.getByText(/max: 50mb/i)).toBeInTheDocument()
    expect(screen.getByText(/pdf, markdown/i)).toBeInTheDocument()
  })

  it('should disable submit button when no file selected', () => {
    render(createElement(UploadForm), { wrapper: createWrapper() })

    const submitButton = screen.getByRole('button', { name: /upload/i })
    expect(submitButton).toBeDisabled()
  })

  it('should display selected file information', async () => {
    const user = userEvent.setup()
    render(createElement(UploadForm), { wrapper: createWrapper() })

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByLabelText(/document file/i)

    await user.upload(input, file)

    await waitFor(() => {
      expect(screen.getByText(/selected:/i)).toBeInTheDocument()
      expect(screen.getByText(/test\.pdf/)).toBeInTheDocument()
      expect(screen.getByText(/size:/i)).toBeInTheDocument()
    })
  })

  // SF-009: Silent validation failure test
  it('should display validation error when file is too large', async () => {
    const user = userEvent.setup()
    render(createElement(UploadForm), { wrapper: createWrapper() })

    // Create a mock file larger than 50MB
    const largeFile = new File(['x'.repeat(51 * 1024 * 1024)], 'large.pdf', {
      type: 'application/pdf',
    })
    const input = screen.getByLabelText(/document file/i)

    await user.upload(input, largeFile)

    const submitButton = screen.getByRole('button', { name: /upload/i })
    await user.click(submitButton)

    // Should show validation error to user
    await waitFor(() => {
      expect(screen.getByText(/file size must be less than 50mb/i)).toBeInTheDocument()
    })

    // Upload should NOT be called
    expect(apiClient.uploadDocument).not.toHaveBeenCalled()
  })

  // SF-009: Invalid file type test
  it('should reject invalid file types via validation schema', async () => {
    // Due to jsdom limitations with file input accept attribute,
    // we test the validation schema directly to ensure invalid types are caught
    const { documentUploadSchema } = await import('@/lib/validation/document')

    const invalidFile = new File(['content'], 'document.txt', { type: 'text/plain' })
    const validationResult = documentUploadSchema.safeParse({
      file: invalidFile,
      domain: 'test',
      description: 'test'
    })

    // Validation should fail for .txt files
    expect(validationResult.success).toBe(false)
    if (!validationResult.success) {
      expect(validationResult.error.errors[0].message).toMatch(/file must be pdf or markdown/i)
    }

    // Verify the validation error is user-friendly
    expect(validationResult.success).toBe(false)
  })
})
