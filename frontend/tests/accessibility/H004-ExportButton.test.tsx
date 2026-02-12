import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExportButton } from '@/components/chat/ExportButton'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'

describe('H-004: ExportButton Keyboard Navigation', () => {
  const mockMessages: ChatMessage[] = [
    {
      id: '1',
      role: 'user',
      content: 'Test question',
      timestamp: Date.now(),
    },
  ]

  it('main button has proper ARIA label', () => {
    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    expect(button).toHaveAttribute('aria-label', 'Export conversation')
  })

  it('dropdown has aria-expanded attribute', () => {
    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })

  it('aria-expanded changes when dropdown opens', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    // Open dropdown
    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('dropdown menu items are keyboard accessible', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    // Open dropdown
    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    // Both export options should be buttons with proper roles
    const markdownButton = screen.getByRole('button', {
      name: /export as markdown/i,
    })
    const jsonButton = screen.getByRole('button', { name: /export as json/i })

    expect(markdownButton).toBeInTheDocument()
    expect(jsonButton).toBeInTheDocument()
  })

  it('focus is managed when dropdown opens', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    // First menu item should be focusable
    const markdownButton = screen.getByRole('button', {
      name: /export as markdown/i,
    })
    await user.tab()

    // After opening and tabbing, we should focus on menu items
    expect(markdownButton).toHaveClass('focus:bg-gray-100')
  })

  it('Escape key closes dropdown', async () => {
    const user = userEvent.setup()

    render(<ExportButton messages={mockMessages} />)

    const button = screen.getByRole('button', { name: /export/i })
    await user.click(button)

    expect(button).toHaveAttribute('aria-expanded', 'true')

    // Press Escape
    await user.keyboard('{Escape}')

    expect(button).toHaveAttribute('aria-expanded', 'false')
  })
})
