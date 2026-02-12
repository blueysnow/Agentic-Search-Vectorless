import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatSkeleton } from '@/components/skeletons/ChatSkeleton'

describe('ChatSkeleton', () => {
  it('renders with accessible loading status', () => {
    render(<ChatSkeleton />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Loading messages')).toBeInTheDocument()
  })

  it('renders 3 message skeletons', () => {
    render(<ChatSkeleton />)

    const skeletons = screen.getAllByTestId('message-skeleton')
    expect(skeletons).toHaveLength(3)
  })

  it('includes screen reader text', () => {
    render(<ChatSkeleton />)

    expect(screen.getByText('Loading messages')).toBeInTheDocument()
  })
})
