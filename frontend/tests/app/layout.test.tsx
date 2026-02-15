import { describe, it, expect } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'

describe('RootLayout', () => {
  it('should have suppressHydrationWarning to prevent browser extension style injection warnings', () => {
    // Read layout.tsx and verify suppressHydrationWarning exists on html element
    const layoutPath = path.join(
      process.cwd(),
      'app',
      'layout.tsx'
    )
    const layoutContent = fs.readFileSync(layoutPath, 'utf-8')

    // Check for suppressHydrationWarning attribute on html element
    const htmlTagRegex = /<html[^>]*suppressHydrationWarning[^>]*>/
    expect(layoutContent).toMatch(htmlTagRegex)
  })
})
