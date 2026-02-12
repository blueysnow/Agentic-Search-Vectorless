import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBoundary } from '@/components/ErrorBoundary'

// Component that throws error on demand
function ProblematicComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>Working component</div>
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <ProblematicComponent shouldThrow={false} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Working component')).toBeInTheDocument()
  })

  it('displays error with role="alert" for screen readers', () => {
    // Suppress console.error in tests
    const consoleError = console.error
    console.error = () => {}

    render(
      <ErrorBoundary>
        <ProblematicComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    const errorAlert = screen.getByRole('alert')
    expect(errorAlert).toBeInTheDocument()
    expect(errorAlert).toHaveTextContent('Something went wrong')

    console.error = consoleError
  })

  it('shows error message to user', () => {
    const consoleError = console.error
    console.error = () => {}

    render(
      <ErrorBoundary>
        <ProblematicComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Test error message')).toBeInTheDocument()

    console.error = consoleError
  })

  it('provides retry button', () => {
    const consoleError = console.error
    console.error = () => {}

    render(
      <ErrorBoundary>
        <ProblematicComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    const retryButton = screen.getByRole('button', { name: /try again/i })
    expect(retryButton).toBeInTheDocument()

    console.error = consoleError
  })

  it('retry button is keyboard accessible', async () => {
    const consoleError = console.error
    console.error = () => {}
    const user = userEvent.setup()

    render(
      <ErrorBoundary>
        <ProblematicComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    const retryButton = screen.getByRole('button', { name: /try again/i })

    // Focus button with Tab
    await user.tab()
    expect(retryButton).toHaveFocus()

    console.error = consoleError
  })
})
