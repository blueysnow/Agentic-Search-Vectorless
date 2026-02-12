'use client'

import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div
          className="p-6 border border-red-200 rounded-lg bg-red-50"
          role="alert"
          aria-live="assertive"
        >
          <h3 className="font-semibold text-red-900 mb-2">Something went wrong</h3>
          <p className="text-sm text-red-700">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: undefined })}
            className="mt-4 px-4 py-2 text-sm bg-red-100 hover:bg-red-200 text-red-900 rounded cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-500"
            aria-label="Try again"
          >
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
