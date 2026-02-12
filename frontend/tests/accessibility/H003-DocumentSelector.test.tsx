import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DocumentSelector } from '@/components/chat/DocumentSelector'

describe('H-003: DocumentSelector ARIA Pattern', () => {
  const mockDocuments = [
    { id: 'doc-1', title: 'Document 1', pageCount: 10 },
    { id: 'doc-2', title: 'Document 2', pageCount: 20 },
    { id: 'doc-3', title: 'Document 3', pageCount: 15 },
  ]

  const mockOnSelect = vi.fn()

  it('dropdown has role="listbox" when open', async () => {
    const user = userEvent.setup()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={[]}
        onSelect={mockOnSelect}
      />
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    // Check for listbox role
    const listbox = screen.getByRole('listbox')
    expect(listbox).toBeInTheDocument()
  })

  it('listbox has aria-multiselectable="true"', async () => {
    const user = userEvent.setup()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={[]}
        onSelect={mockOnSelect}
      />
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    const listbox = screen.getByRole('listbox')
    expect(listbox).toHaveAttribute('aria-multiselectable', 'true')
  })

  it('each document option has role="option"', async () => {
    const user = userEvent.setup()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={[]}
        onSelect={mockOnSelect}
      />
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)
  })

  it('selected items have aria-selected="true"', async () => {
    const user = userEvent.setup()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1', 'doc-3']}
        onSelect={mockOnSelect}
      />
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('aria-selected', 'true')
    expect(options[1]).toHaveAttribute('aria-selected', 'false')
    expect(options[2]).toHaveAttribute('aria-selected', 'true')
  })

  it('unselected items have aria-selected="false"', async () => {
    const user = userEvent.setup()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1']}
        onSelect={mockOnSelect}
      />
    )

    // Open dropdown
    const button = screen.getByRole('button')
    await user.click(button)

    const options = screen.getAllByRole('option')
    expect(options[1]).toHaveAttribute('aria-selected', 'false')
    expect(options[2]).toHaveAttribute('aria-selected', 'false')
  })
})
