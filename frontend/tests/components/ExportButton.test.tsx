import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExportButton } from '@/components/chat/ExportButton'

// Mock the download function
vi.mock('@/lib/export-conversation', () => ({
  downloadConversation: vi.fn(),
}))

import { downloadConversation } from '@/lib/export-conversation'

describe('ExportButton', () => {
  const mockMessages = [
    {
      id: 'msg-1',
      role: 'user' as const,
      content: 'Test question',
      timestamp: Date.now(),
    },
    {
      id: 'msg-2',
      role: 'assistant' as const,
      content: 'Test answer',
      timestamp: Date.now(),
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders export button', () => {
    render(<ExportButton messages={mockMessages} />)

    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
  })

  it('shows dropdown menu when clicked', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    expect(screen.getByText(/markdown/i)).toBeInTheDocument()
    expect(screen.getByText(/json/i)).toBeInTheDocument()
  })

  it('triggers markdown download when markdown option clicked', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    const markdownOption = screen.getByText(/markdown/i)
    await user.click(markdownOption)

    expect(downloadConversation).toHaveBeenCalledWith(
      mockMessages,
      'markdown',
      undefined,
      expect.objectContaining({ exportedAt: expect.any(String) })
    )
  })

  it('triggers JSON download when JSON option clicked', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    const jsonOption = screen.getByText(/json/i)
    await user.click(jsonOption)

    expect(downloadConversation).toHaveBeenCalledWith(
      mockMessages,
      'json',
      undefined,
      expect.objectContaining({ exportedAt: expect.any(String) })
    )
  })

  it('is disabled when no messages', () => {
    render(<ExportButton messages={[]} />)

    const button = screen.getByRole('button', { name: /export/i })
    expect(button).toBeDisabled()
  })

  it('closes dropdown after selection', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    expect(screen.getByText(/markdown/i)).toBeInTheDocument()

    const markdownOption = screen.getByText(/markdown/i)
    await user.click(markdownOption)

    // Dropdown should close (markdown option no longer visible)
    expect(screen.queryByText(/markdown/i)).not.toBeInTheDocument()
  })

  it('passes sessionId to download metadata', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} sessionId="session-123" />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    const markdownOption = screen.getByText(/markdown/i)
    await user.click(markdownOption)

    expect(downloadConversation).toHaveBeenCalledWith(
      mockMessages,
      'markdown',
      undefined,
      expect.objectContaining({ sessionId: 'session-123' })
    )
  })

  it('passes documentIds to download metadata', async () => {
    const user = userEvent.setup()

    render(
      <ExportButton
        messages={mockMessages}
        documentIds={['doc-1', 'doc-2']}
      />
    )

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    const markdownOption = screen.getByText(/markdown/i)
    await user.click(markdownOption)

    expect(downloadConversation).toHaveBeenCalledWith(
      mockMessages,
      'markdown',
      undefined,
      expect.objectContaining({ documentIds: ['doc-1', 'doc-2'] })
    )
  })
})
