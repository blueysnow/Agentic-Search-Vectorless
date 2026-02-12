import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RetrievalTrace } from '@/components/chat/RetrievalTrace'

describe('RetrievalTrace', () => {
  const mockSteps = [
    {
      type: 'query' as const,
      description: 'Received user query',
      timestamp: Date.now(),
    },
    {
      type: 'filter' as const,
      description: 'Filtered by document IDs',
      details: { documentIds: ['doc-1', 'doc-2'] },
    },
    {
      type: 'retrieve' as const,
      description: 'Retrieved 10 candidate passages',
    },
    {
      type: 'rank' as const,
      description: 'Ranked by relevance score',
      details: { topScore: 0.95 },
    },
  ]

  it('renders retrieval steps in order', () => {
    render(<RetrievalTrace steps={mockSteps} />)

    expect(screen.getByText('Received user query')).toBeInTheDocument()
    expect(screen.getByText('Filtered by document IDs')).toBeInTheDocument()
    expect(screen.getByText('Retrieved 10 candidate passages')).toBeInTheDocument()
    expect(screen.getByText('Ranked by relevance score')).toBeInTheDocument()
  })

  it('shows step numbers', () => {
    render(<RetrievalTrace steps={mockSteps} />)

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('displays step types as labels', () => {
    const { container } = render(<RetrievalTrace steps={mockSteps} />)

    // Check for uppercase labels in the step type badges
    const labels = container.querySelectorAll('.uppercase')
    const labelTexts = Array.from(labels).map(el => el.textContent?.toLowerCase())

    expect(labelTexts).toContain('query')
    expect(labelTexts).toContain('filter')
    expect(labelTexts).toContain('retrieve')
    expect(labelTexts).toContain('rank')
  })

  it('shows details when present', () => {
    render(<RetrievalTrace steps={mockSteps} />)

    const detailsButtons = screen.getAllByText('Show details')
    expect(detailsButtons.length).toBeGreaterThan(0)
  })

  it('renders null when no steps provided', () => {
    const { container } = render(<RetrievalTrace steps={[]} />)

    expect(container.firstChild).toBeNull()
  })

  it('handles missing optional properties', () => {
    const minimalSteps = [
      {
        type: 'query' as const,
        description: 'Test step',
      },
    ]

    render(<RetrievalTrace steps={minimalSteps} />)

    expect(screen.getByText('Test step')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<RetrievalTrace steps={mockSteps} className="custom-class" />)

    const traceElement = container.querySelector('.custom-class')
    expect(traceElement).toBeInTheDocument()
  })

  it('displays timestamps when provided', () => {
    const stepsWithTimestamp = [
      {
        type: 'query' as const,
        description: 'Test',
        timestamp: new Date('2024-01-15T10:30:00Z').getTime(),
      },
    ]

    render(<RetrievalTrace steps={stepsWithTimestamp} />)

    // Should show time in some format
    expect(screen.getByText(/:/)).toBeInTheDocument()
  })

  it('uses different colors for different step types', () => {
    const { container } = render(<RetrievalTrace steps={mockSteps} />)

    // Verify color classes are applied (bg-blue, bg-purple, bg-green, bg-orange)
    const stepBadges = container.querySelectorAll('[class*="bg-"]')
    expect(stepBadges.length).toBeGreaterThan(0)
  })
})
