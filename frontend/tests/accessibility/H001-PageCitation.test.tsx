import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PageCitation } from '@/components/chat/PageCitation'

describe('H-001: PageCitation Keyboard Accessibility', () => {
  const mockOnClick = vi.fn()

  it('is keyboard focusable with tabIndex=0', () => {
    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        onClick={mockOnClick}
      />
    )

    const citation = screen.getByText('Page 5').parentElement
    expect(citation).toHaveAttribute('tabIndex', '0')
  })

  it('can be activated with Enter key', async () => {
    const user = userEvent.setup()

    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        onClick={mockOnClick}
      />
    )

    const citation = screen.getByText('Page 5').parentElement!

    // Focus and press Enter
    citation.focus()
    await user.keyboard('{Enter}')

    expect(mockOnClick).toHaveBeenCalledWith({
      page: 5,
      documentId: 'doc-123',
    })
  })

  it('can be activated with Space key', async () => {
    const user = userEvent.setup()

    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        onClick={mockOnClick}
      />
    )

    const citation = screen.getByText('Page 5').parentElement!

    // Focus and press Space
    citation.focus()
    await user.keyboard(' ')

    expect(mockOnClick).toHaveBeenCalledWith({
      page: 5,
      documentId: 'doc-123',
    })
  })

  it('has visible focus ring', () => {
    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        onClick={mockOnClick}
      />
    )

    const citation = screen.getByText('Page 5').parentElement
    expect(citation).toHaveClass('focus:ring-2')
  })

  it('has role="button" for screen readers', () => {
    render(
      <PageCitation
        page={5}
        documentId="doc-123"
        onClick={mockOnClick}
      />
    )

    const citation = screen.getByRole('button', { name: /Page 5/i })
    expect(citation).toBeInTheDocument()
  })

  it('should sanitize malicious excerpt in ARIA label (H-REM4-1: XSS)', () => {
    const maliciousExcerpt = '"><script>alert("XSS")</script><span foo="'

    render(
      <PageCitation
        page={1}
        documentId="doc1"
        excerpt={maliciousExcerpt}
      />
    )

    const citation = screen.getByRole('button')
    const ariaLabel = citation.getAttribute('aria-label')

    // Should NOT contain unescaped script tag
    expect(ariaLabel).not.toContain('<script>')
    expect(ariaLabel).not.toContain('</script>')
    // Should escape dangerous characters
    expect(ariaLabel).toContain('&lt;')
    expect(ariaLabel).toContain('&gt;')
    expect(ariaLabel).toContain('&quot;')
  })
})
