import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PageCitation } from '@/components/chat/PageCitation'

describe('PageCitation', () => {
  it('renders page number', () => {
    render(<PageCitation page={3} documentId="doc-123" />)

    expect(screen.getByText(/Page 3/i)).toBeInTheDocument()
  })

  it('applies clickable styling with cursor-pointer', () => {
    render(<PageCitation page={5} documentId="doc-123" />)

    const citation = screen.getByText(/Page 5/i).closest('div')
    expect(citation).toHaveClass('cursor-pointer')
  })

  it('calls onClick with page and documentId when clicked', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    render(<PageCitation page={7} documentId="doc-456" onClick={onClick} />)

    const citation = screen.getByText(/Page 7/i)
    await user.click(citation)

    expect(onClick).toHaveBeenCalledWith({ page: 7, documentId: 'doc-456' })
  })

  it('renders without onClick handler (optional)', () => {
    render(<PageCitation page={2} documentId="doc-123" />)

    expect(screen.getByText(/Page 2/i)).toBeInTheDocument()
  })

  it('displays excerpt text when provided', () => {
    render(
      <PageCitation
        page={4}
        documentId="doc-123"
        excerpt="Q4 revenue was $2.5M"
      />
    )

    expect(screen.getByText(/Q4 revenue was \$2\.5M/i)).toBeInTheDocument()
  })

  it('truncates long excerpts with ellipsis', () => {
    const longExcerpt = 'A'.repeat(150)

    const { container } = render(
      <PageCitation page={1} documentId="doc-123" excerpt={longExcerpt} />
    )

    const excerptElement = container.querySelector('.line-clamp-2')
    expect(excerptElement).toBeInTheDocument()
  })

  it('applies badge styling', () => {
    render(<PageCitation page={5} documentId="doc-123" />)

    const badge = screen.getByText(/Page 5/i).closest('div')
    expect(badge).toHaveClass('rounded-md')
  })

  it('uses blue color scheme for badges', () => {
    render(<PageCitation page={3} documentId="doc-123" />)

    const badge = screen.getByText(/Page 3/i).closest('div')
    expect(badge).toHaveClass('bg-blue-100')
    expect(badge).toHaveClass('text-blue-800')
  })

  it('shows hover state styling', () => {
    render(<PageCitation page={2} documentId="doc-123" />)

    const badge = screen.getByText(/Page 2/i).closest('div')
    expect(badge?.className).toMatch(/hover:/)
  })

  it('renders multiple citations independently', () => {
    const { rerender } = render(<PageCitation page={1} documentId="doc-123" />)

    expect(screen.getByText(/Page 1/i)).toBeInTheDocument()

    rerender(<PageCitation page={2} documentId="doc-456" />)

    expect(screen.getByText(/Page 2/i)).toBeInTheDocument()
  })

  it('includes tooltip or title with full context', () => {
    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        excerpt="Full text here"
      />
    )

    const citation = screen.getByText(/Page 5/i).closest('div')
    expect(citation).toHaveAttribute('title', expect.stringContaining('Page 5'))
  })

  it('handles page number 0 (edge case)', () => {
    render(<PageCitation page={0} documentId="doc-123" />)

    expect(screen.getByText(/Page 0/i)).toBeInTheDocument()
  })

  it('handles large page numbers', () => {
    render(<PageCitation page={999} documentId="doc-123" />)

    expect(screen.getByText(/Page 999/i)).toBeInTheDocument()
  })
})
