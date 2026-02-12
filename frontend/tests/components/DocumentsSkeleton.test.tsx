import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DocumentsSkeleton } from '@/components/skeletons/DocumentsSkeleton'

describe('DocumentsSkeleton', () => {
  it('renders with accessible loading status', () => {
    render(<DocumentsSkeleton />)

    // Should have role="status" for screen readers
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading documents')).toBeInTheDocument()
  })

  it('renders 3 skeleton cards', () => {
    render(<DocumentsSkeleton />)

    const skeletons = screen.getAllByTestId('document-skeleton')
    expect(skeletons).toHaveLength(3)
  })

  it('includes screen reader text', () => {
    render(<DocumentsSkeleton />)

    // sr-only text for screen readers
    expect(screen.getByText('Loading documents')).toBeInTheDocument()
  })
})
