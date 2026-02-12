/**
 * REM-FIX-3: Regression tests for 8 blocking issues from re-review challenge round
 */

import { describe, it, expect } from 'vitest'

describe('REM-FIX-3: Critical and High Priority Fixes', () => {
  describe('C-REM3-1: Unhandled promise rejection in sessions/[id]/page.tsx', () => {
    it('should include .catch() handler for params.then() chain', () => {
      // Read the source code to verify .catch() is present
      const fs = require('fs')
      const path = require('path')
      const filePath = path.join(process.cwd(), 'app/sessions/[id]/page.tsx')
      const content = fs.readFileSync(filePath, 'utf-8')

      // Line 18 should have params.then(...).catch(...)
      // This test will FAIL if .catch() is missing
      const hasParamsThen = content.includes('params.then')
      // Match across newlines with dotall flag (use .+? for non-greedy)
      const hasCatch = /params\.then\(.+?\)\.catch/s.test(content)

      expect(hasParamsThen).toBe(true)
      expect(hasCatch).toBe(true)
    })
  })

  describe('H-REM3-1: Throttle timeout leak in lib/performance.ts', () => {
    it('should return cleanup function from throttle', () => {
      const fs = require('fs')
      const path = require('path')
      const filePath = path.join(process.cwd(), 'lib/performance.ts')
      const content = fs.readFileSync(filePath, 'utf-8')

      // Throttle function should return object with cleanup function
      // Pattern: return { throttled, cleanup }
      const hasThrottledReturn = /return \{ throttled, cleanup \}/.test(content)
      const hasCleanupFunction = /const cleanup = function\(\)/.test(content)
      const hasClearTimeoutInCleanup = /cleanup = function\(\)[^}]*clearTimeout/s.test(content)

      expect(hasThrottledReturn).toBe(true)
      expect(hasCleanupFunction).toBe(true)
      expect(hasClearTimeoutInCleanup).toBe(true)
    })
  })

  describe('H-REM3-2: XSS in thinking steps export', () => {
    it('should sanitize thinking step text in exportToMarkdown', () => {
      const fs = require('fs')
      const path = require('path')
      const filePath = path.join(process.cwd(), 'lib/export-conversation.ts')
      const content = fs.readFileSync(filePath, 'utf-8')

      // Should map thinking array and sanitize each step
      const hasThinkingMap = /message\.thinking\.map/.test(content)
      const hasSanitizeInMap = /thinking\.map\(step => sanitizeMarkdown\(step\)\)/.test(content)

      expect(hasThinkingMap).toBe(true)
      expect(hasSanitizeInMap).toBe(true)
    })
  })

  describe('H-REM3-3: XSS in metadata fields export', () => {
    it('should sanitize metadata.doc_name in exportToMarkdown', () => {
      const fs = require('fs')
      const path = require('path')
      const filePath = path.join(process.cwd(), 'lib/export-conversation.ts')
      const content = fs.readFileSync(filePath, 'utf-8')

      // Should call sanitizeMarkdown on metadata.doc_name
      const hasSanitizeDocName = /sanitizeMarkdown\(message\.metadata\.doc_name\)/.test(content)

      expect(hasSanitizeDocName).toBe(true)
    })

    it('should sanitize export metadata fields (sessionId, documentIds, exportedAt)', () => {
      const fs = require('fs')
      const path = require('path')
      const filePath = path.join(process.cwd(), 'lib/export-conversation.ts')
      const content = fs.readFileSync(filePath, 'utf-8')

      // Should sanitize sessionId, documentIds, and exportedAt in export metadata
      const hasSanitizeSessionId = /sanitizeMarkdown\(metadata\.sessionId\)/.test(content)
      const hasSanitizeDocIds = /metadata\.documentIds\.map\([^)]*sanitizeMarkdown/.test(content)
      const hasSanitizeExportedAt = /sanitizeMarkdown\(metadata\.exportedAt\)/.test(content)

      expect(hasSanitizeSessionId).toBe(true)
      expect(hasSanitizeDocIds).toBe(true)
      expect(hasSanitizeExportedAt).toBe(true)
    })
  })
})
