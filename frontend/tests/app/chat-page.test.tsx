import { describe, it, expect, vi } from 'vitest'

// Mock Next.js navigation
const mockRedirect = vi.fn()
vi.mock('next/navigation', () => ({
  redirect: mockRedirect,
}))

describe('ChatPage', () => {
  it('should redirect to /query', async () => {
    // ChatPage is now a redirect page -- import it to trigger the redirect call
    const { default: ChatPage } = await import('@/app/chat/page')

    // The redirect function should be called with '/query'
    // In Next.js, redirect() throws a NEXT_REDIRECT error, but in tests we just verify it's called
    try {
      ChatPage()
    } catch {
      // redirect() throws in Next.js -- expected
    }
    expect(mockRedirect).toHaveBeenCalledWith('/query')
  })
})
