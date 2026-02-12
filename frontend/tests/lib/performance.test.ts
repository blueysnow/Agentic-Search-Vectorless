import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { throttle } from '@/lib/performance'

describe('Performance Utilities', () => {
  describe('throttle (H7 + H-REM3-1)', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.restoreAllMocks()
      vi.useRealTimers()
    })

    it('should call function immediately on first invocation', () => {
      const fn = vi.fn()
      const { throttled } = throttle(fn, 100)

      throttled()

      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('should throttle rapid calls', () => {
      const fn = vi.fn()
      const { throttled } = throttle(fn, 100)

      // First call executes immediately
      throttled()
      expect(fn).toHaveBeenCalledTimes(1)

      // Second call within delay - sets timeout
      throttled()
      expect(fn).toHaveBeenCalledTimes(1)

      // Third call within delay - replaces timeout
      throttled()
      expect(fn).toHaveBeenCalledTimes(1)

      // Advance time to trigger the pending timeout
      vi.advanceTimersByTime(100)
      expect(fn).toHaveBeenCalledTimes(2)
    })

    it('should pass arguments correctly', () => {
      const fn = vi.fn()
      const { throttled } = throttle(fn, 100)

      throttled('arg1', 'arg2')

      expect(fn).toHaveBeenCalledWith('arg1', 'arg2')
    })

    it('should handle multiple arguments', () => {
      const fn = vi.fn()
      const { throttled } = throttle(fn, 50)

      throttled(1, 2, 3)

      expect(fn).toHaveBeenCalledWith(1, 2, 3)
    })

    it('should provide cleanup function to clear pending timeout', () => {
      const fn = vi.fn()
      const { throttled, cleanup } = throttle(fn, 100)

      // Call once (immediate), then call again (will schedule timeout)
      throttled()
      throttled()

      expect(fn).toHaveBeenCalledTimes(1)

      // Cleanup should clear the pending timeout
      cleanup()

      // Advance time past the throttle delay
      vi.advanceTimersByTime(150)

      // Function should still only have been called once (timeout was cleared)
      expect(fn).toHaveBeenCalledTimes(1)
    })
  })
})
