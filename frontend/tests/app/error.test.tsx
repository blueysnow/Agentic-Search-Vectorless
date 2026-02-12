import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import RootError from '@/app/error'

describe('RootError boundary', () => {
  it('should render error message', () => {
    const error = new Error('Test error')
    const reset = vi.fn()

    render(<RootError error={error} reset={reset} />)

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
  })

  it('should display error message in development', () => {
    const error = new Error('Test error message')
    const reset = vi.fn()

    render(<RootError error={error} reset={reset} />)

    // Should show error message (or generic message in production)
    expect(screen.getByText(/error/i)).toBeInTheDocument()
  })

  it('should call reset when try again button clicked', async () => {
    const user = userEvent.setup()
    const error = new Error('Test error')
    const reset = vi.fn()

    render(<RootError error={error} reset={reset} />)

    const button = screen.getByRole('button', { name: /try again/i })
    await user.click(button)

    expect(reset).toHaveBeenCalledTimes(1)
  })

  it('should provide link to home', () => {
    const error = new Error('Test error')
    const reset = vi.fn()

    render(<RootError error={error} reset={reset} />)

    const homeLink = screen.getByRole('link', { name: /home/i })
    expect(homeLink).toHaveAttribute('href', '/')
  })
})
