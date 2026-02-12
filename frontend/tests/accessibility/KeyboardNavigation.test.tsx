import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Test keyboard navigation on common patterns
describe('Keyboard Navigation', () => {
  it('buttons have visible focus indicators', async () => {
    const user = userEvent.setup()

    render(
      <button className="px-4 py-2 bg-blue-600 text-white rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
        Click me
      </button>
    )

    const button = screen.getByRole('button')

    // Tab to focus
    await user.tab()
    expect(button).toHaveFocus()

    // Check focus ring class exists
    expect(button).toHaveClass('focus:ring-2')
  })

  it('interactive elements are reachable by keyboard', async () => {
    const user = userEvent.setup()

    render(
      <div>
        <button>First</button>
        <button>Second</button>
        <a href="#test">Link</a>
        <input type="text" aria-label="Text input" />
      </div>
    )

    const first = screen.getByRole('button', { name: 'First' })
    const second = screen.getByRole('button', { name: 'Second' })
    const link = screen.getByRole('link')
    const input = screen.getByRole('textbox')

    // Tab through all elements
    await user.tab()
    expect(first).toHaveFocus()

    await user.tab()
    expect(second).toHaveFocus()

    await user.tab()
    expect(link).toHaveFocus()

    await user.tab()
    expect(input).toHaveFocus()
  })

  it('disabled buttons are not focusable', async () => {
    const user = userEvent.setup()

    render(
      <div>
        <button>Enabled</button>
        <button disabled>Disabled</button>
        <button>Another</button>
      </div>
    )

    const enabled = screen.getByRole('button', { name: 'Enabled' })
    const another = screen.getByRole('button', { name: 'Another' })

    // Tab should skip disabled button
    await user.tab()
    expect(enabled).toHaveFocus()

    await user.tab()
    expect(another).toHaveFocus()
  })
})
