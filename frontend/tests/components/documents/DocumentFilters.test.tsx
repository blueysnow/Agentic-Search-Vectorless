import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement } from 'react'
import { DocumentFilters } from '@/components/documents/DocumentFilters'

describe('DocumentFilters', () => {
  it('should render all filter inputs', () => {
    const mockOnChange = vi.fn()

    render(createElement(DocumentFilters, { filters: {}, onChange: mockOnChange }))

    expect(screen.getByLabelText(/status/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/domain/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/search/i)).toBeInTheDocument()
  })

  it('should call onChange when status filter changes', async () => {
    const user = userEvent.setup()
    const mockOnChange = vi.fn()

    render(createElement(DocumentFilters, { filters: {}, onChange: mockOnChange }))

    const statusSelect = screen.getByLabelText(/status/i)
    await user.selectOptions(statusSelect, 'completed')

    expect(mockOnChange).toHaveBeenCalled()
    // Verify it was called with a function (functional setState)
    expect(typeof mockOnChange.mock.calls[0][0]).toBe('function')
    // Test the function returns correct value
    const updateFn = mockOnChange.mock.calls[0][0]
    expect(updateFn({})).toEqual({ status: 'completed' })
  })

  it('should call onChange when domain filter changes', async () => {
    const user = userEvent.setup()
    const mockOnChange = vi.fn()

    render(createElement(DocumentFilters, { filters: {}, onChange: mockOnChange }))

    const domainInput = screen.getByLabelText(/domain/i)
    await user.type(domainInput, 'science')

    expect(mockOnChange).toHaveBeenCalled()
  })

  it('should call onChange when search filter changes', async () => {
    const user = userEvent.setup()
    const mockOnChange = vi.fn()

    render(createElement(DocumentFilters, { filters: {}, onChange: mockOnChange }))

    const searchInput = screen.getByLabelText(/search/i)
    await user.type(searchInput, 'test query')

    expect(mockOnChange).toHaveBeenCalled()
  })

  it('should clear all filters when clear button clicked', async () => {
    const user = userEvent.setup()
    const mockOnChange = vi.fn()

    render(
      createElement(DocumentFilters, {
        filters: { status: 'completed', domain: 'science' },
        onChange: mockOnChange,
      })
    )

    const clearButton = screen.getByText(/clear all/i)
    await user.click(clearButton)

    expect(mockOnChange).toHaveBeenCalledWith({})
  })

  it('should display current filter values', () => {
    const mockOnChange = vi.fn()
    const filters = { status: 'completed' as const, domain: 'science', q: 'test' }

    render(createElement(DocumentFilters, { filters, onChange: mockOnChange }))

    const statusSelect = screen.getByLabelText(/status/i) as HTMLSelectElement
    expect(statusSelect.value).toBe('completed')

    const domainInput = screen.getByLabelText(/domain/i) as HTMLInputElement
    expect(domainInput.value).toBe('science')

    const searchInput = screen.getByLabelText(/search/i) as HTMLInputElement
    expect(searchInput.value).toBe('test')
  })
})
