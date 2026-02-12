import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TreeVisualization } from '@/components/documents/TreeVisualization'
import type { TreeNode } from '@/lib/api/types'

describe('H-002: TreeVisualization aria-expanded', () => {
  const mockNodes: TreeNode[] = [
    {
      nodeId: 'root',
      content: 'Root node',
      level: 0,
      children: ['child-1'],
      metadata: { pageNumber: 1 },
    },
    {
      nodeId: 'child-1',
      content: 'Child node 1',
      level: 1,
      children: ['child-2'],
      metadata: { pageNumber: 2 },
    },
    {
      nodeId: 'child-2',
      content: 'Child node 2',
      level: 2,
      children: [],
      metadata: { pageNumber: 3 },
    },
  ]

  it('expandable nodes have aria-expanded="true" when expanded', () => {
    render(<TreeVisualization rootNodeId="root" nodes={mockNodes} />)

    // Root node is expanded by default (depth < 2)
    const expandButtons = screen.getAllByLabelText('Collapse')
    expect(expandButtons[0]).toHaveAttribute('aria-expanded', 'true')
  })

  it('expandable nodes have aria-expanded="false" when collapsed', async () => {
    const user = userEvent.setup()

    render(<TreeVisualization rootNodeId="root" nodes={mockNodes} />)

    // Click to collapse root node
    const collapseButtons = screen.getAllByLabelText('Collapse')
    await user.click(collapseButtons[0])

    // Now root should be collapsed
    const expandButtons = screen.getAllByLabelText('Expand')
    expect(expandButtons[0]).toHaveAttribute('aria-expanded', 'false')
  })

  it('aria-expanded toggles when button is clicked', async () => {
    const user = userEvent.setup()

    render(<TreeVisualization rootNodeId="root" nodes={mockNodes} />)

    let buttons = screen.getAllByLabelText('Collapse')
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'true')

    // Collapse root
    await user.click(buttons[0])
    buttons = screen.getAllByLabelText('Expand')
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'false')

    // Expand again
    await user.click(buttons[0])
    buttons = screen.getAllByLabelText('Collapse')
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'true')
  })

  it('nodes without children do not have expand/collapse button', () => {
    const leafNodes: TreeNode[] = [
      {
        nodeId: 'leaf',
        content: 'Leaf node',
        level: 0,
        children: [],
        metadata: { pageNumber: 1 },
      },
    ]

    render(<TreeVisualization rootNodeId="leaf" nodes={leafNodes} />)

    // No expand/collapse button should be present
    expect(screen.queryByLabelText('Expand')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Collapse')).not.toBeInTheDocument()
  })
})
