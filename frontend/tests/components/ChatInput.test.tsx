import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '@/components/chat/ChatInput'

describe('ChatInput', () => {
  it('renders input field with placeholder', () => {
    render(
      <ChatInput
        onSend={vi.fn()}
        disabled={false}
        placeholder="Ask a question..."
      />
    )

    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
  })

  it('renders send button', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })

  it('calls onSend with message when send button is clicked', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'What is revenue?')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    expect(onSend).toHaveBeenCalledWith('What is revenue?')
  })

  it('calls onSend when Enter key is pressed', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test message{Enter}')

    expect(onSend).toHaveBeenCalledWith('Test message')
  })

  it('does not call onSend when Shift+Enter is pressed', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2')

    expect(onSend).not.toHaveBeenCalled()
    expect(input).toHaveValue('Line 1\nLine 2')
  })

  it('clears input after sending message', async () => {
    const user = userEvent.setup()

    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test message')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    await waitFor(() => {
      expect(input).toHaveValue('')
    })
  })

  it('does not call onSend if message is empty', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    expect(onSend).not.toHaveBeenCalled()
  })

  it('does not call onSend if message is only whitespace', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, '   ')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    expect(onSend).not.toHaveBeenCalled()
  })

  it('disables input and button when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />)

    const input = screen.getByRole('textbox')
    const sendButton = screen.getByRole('button', { name: /send/i })

    expect(input).toBeDisabled()
    expect(sendButton).toBeDisabled()
  })

  it('shows custom placeholder when provided', () => {
    render(
      <ChatInput
        onSend={vi.fn()}
        disabled={false}
        placeholder="Select a document to start..."
      />
    )

    expect(
      screen.getByPlaceholderText('Select a document to start...')
    ).toBeInTheDocument()
  })

  it('uses default placeholder when not provided', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    expect(screen.getByPlaceholderText('Ask a question...')).toBeInTheDocument()
  })

  it('focuses input on mount', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const input = screen.getByRole('textbox')
    expect(input).toHaveFocus()
  })

  it('trims whitespace from message before sending', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()

    render(<ChatInput onSend={onSend} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, '  Test message  ')

    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)

    expect(onSend).toHaveBeenCalledWith('Test message')
  })

  it('applies cursor-pointer to send button', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toHaveClass('cursor-pointer')
  })

  it('supports multiline input with textarea', () => {
    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const textarea = screen.getByRole('textbox')
    expect(textarea.tagName).toBe('TEXTAREA')
  })

  it('maintains focus after Enter key if Shift is pressed', async () => {
    const user = userEvent.setup()

    render(<ChatInput onSend={vi.fn()} disabled={false} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}')

    expect(input).toHaveFocus()
  })
})
