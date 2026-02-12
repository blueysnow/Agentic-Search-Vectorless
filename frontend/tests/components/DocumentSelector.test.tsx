import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DocumentSelector } from '@/components/chat/DocumentSelector'

describe('DocumentSelector', () => {
  const mockDocuments = [
    { id: 'doc-1', title: 'Q4 Report', pageCount: 10 },
    { id: 'doc-2', title: 'Strategy Doc', pageCount: 25 },
    { id: 'doc-3', title: 'Team Notes', pageCount: 5 },
  ]

  it('renders with empty selection initially', () => {
    const onSelect = vi.fn()
    render(<DocumentSelector documents={mockDocuments} selectedIds={[]} onSelect={onSelect} />)

    expect(screen.getByText(/select documents/i)).toBeInTheDocument()
  })

  it('displays document count when multiple selected', () => {
    const onSelect = vi.fn()
    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1', 'doc-2']}
        onSelect={onSelect}
      />
    )

    expect(screen.getByText(/2 documents selected/i)).toBeInTheDocument()
  })

  it('shows dropdown with all documents when clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<DocumentSelector documents={mockDocuments} selectedIds={[]} onSelect={onSelect} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Q4 Report')).toBeInTheDocument()
      expect(screen.getByText('Strategy Doc')).toBeInTheDocument()
      expect(screen.getByText('Team Notes')).toBeInTheDocument()
    })
  })

  it('shows checkboxes for each document', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<DocumentSelector documents={mockDocuments} selectedIds={[]} onSelect={onSelect} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(3)
    })
  })

  it('marks selected documents with checked checkboxes', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1']}
        onSelect={onSelect}
      />
    )

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[0]).toBeChecked()
      expect(checkboxes[1]).not.toBeChecked()
      expect(checkboxes[2]).not.toBeChecked()
    })
  })

  it('calls onSelect when document is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<DocumentSelector documents={mockDocuments} selectedIds={[]} onSelect={onSelect} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Q4 Report')).toBeInTheDocument()
    })

    const docOption = screen.getByText('Q4 Report')
    await user.click(docOption)

    expect(onSelect).toHaveBeenCalledWith(['doc-1'])
  })

  it('adds document to selection when unchecked document is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1']}
        onSelect={onSelect}
      />
    )

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Strategy Doc')).toBeInTheDocument()
    })

    const docOption = screen.getByText('Strategy Doc')
    await user.click(docOption)

    expect(onSelect).toHaveBeenCalledWith(['doc-1', 'doc-2'])
  })

  it('removes document from selection when checked document is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1', 'doc-2']}
        onSelect={onSelect}
      />
    )

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Q4 Report')).toBeInTheDocument()
    })

    const docOption = screen.getByText('Q4 Report')
    await user.click(docOption)

    expect(onSelect).toHaveBeenCalledWith(['doc-2'])
  })

  it('displays visual indicators for selected documents', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <DocumentSelector
        documents={mockDocuments}
        selectedIds={['doc-1']}
        onSelect={onSelect}
      />
    )

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[0]).toBeChecked()
    })
  })

  it('shows page count for each document', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<DocumentSelector documents={mockDocuments} selectedIds={[]} onSelect={onSelect} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      const pageCounts = screen.getAllByText(/\d+ pages?/i)
      expect(pageCounts).toHaveLength(3)
      expect(screen.getByText(/10 pages/i)).toBeInTheDocument()
      expect(screen.getByText(/25 pages/i)).toBeInTheDocument()
    })
  })

  it('handles empty document list', () => {
    const onSelect = vi.fn()
    render(<DocumentSelector documents={[]} selectedIds={[]} onSelect={onSelect} />)

    expect(screen.getByText(/select documents/i)).toBeInTheDocument()
  })

  it('shows empty state when no documents available', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<DocumentSelector documents={[]} selectedIds={[]} onSelect={onSelect} />)

    const trigger = screen.getByRole('button')
    await user.click(trigger)

    await waitFor(() => {
      expect(screen.getByText(/no documents available/i)).toBeInTheDocument()
    })
  })
})
