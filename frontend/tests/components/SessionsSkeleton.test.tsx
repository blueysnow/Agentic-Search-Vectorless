import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SessionsSkeleton } from '@/components/skeletons/SessionsSkeleton'

describe('SessionsSkeleton', () => {
  it('renders with accessible loading status', () => {
    render(<SessionsSkeleton />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading conversations')).toBeInTheDocument()
  })

  it('renders 4 skeleton cards', () => {
    render(<SessionsSkeleton />)

    const skeletons = screen.getAllByTestId('session-skeleton')
    expect(skeletons).toHaveLength(4)
  })

  it('includes screen reader text', () => {
    render(<SessionsSkeleton />)

    expect(screen.getByText('Loading conversations')).toBeInTheDocument()
  })
})
