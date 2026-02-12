/**
 * Performance optimization utilities
 */

/**
 * H7: Throttles function execution to once per specified delay
 * H-REM3-1: Returns cleanup function to prevent timeout leak
 * Used for scroll event handlers to prevent jank
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): { throttled: (...args: Parameters<T>) => void; cleanup: () => void } {
  let lastCall = 0
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const throttled = function(...args: Parameters<T>) {
    const now = Date.now()

    if (now - lastCall >= delay) {
      lastCall = now
      func(...args)
    } else {
      // Clear previous timeout and set new one
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(() => {
        lastCall = Date.now()
        func(...args)
      }, delay - (now - lastCall))
    }
  }

  const cleanup = function() {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  return { throttled, cleanup }
}
