import { describe, it, expect } from 'vitest'
import { sanitizeMarkdown, isValidDocumentId, isValidSessionId } from '@/lib/security'

describe('Security Utilities', () => {
  describe('sanitizeMarkdown (H2/H3)', () => {
    it('should escape HTML entities', () => {
      const input = '<script>alert("XSS")</script>'
      const output = sanitizeMarkdown(input)
      expect(output).toBe('&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')
    })

    it('should escape ampersands', () => {
      expect(sanitizeMarkdown('A & B')).toBe('A &amp; B')
    })

    it('should escape quotes', () => {
      expect(sanitizeMarkdown(`"double" and 'single'`)).toBe('&quot;double&quot; and &#039;single&#039;')
    })

    it('should handle empty string', () => {
      expect(sanitizeMarkdown('')).toBe('')
    })
  })

  describe('isValidDocumentId (H4)', () => {
    it('should accept valid alphanumeric IDs', () => {
      expect(isValidDocumentId('doc123')).toBe(true)
      expect(isValidDocumentId('user-guide')).toBe(true)
      expect(isValidDocumentId('test_file')).toBe(true)
    })

    it('should reject IDs with special characters', () => {
      expect(isValidDocumentId('doc/../etc/passwd')).toBe(false)
      expect(isValidDocumentId('doc<script>')).toBe(false)
      expect(isValidDocumentId('doc@123')).toBe(false)
    })

    it('should reject empty string', () => {
      expect(isValidDocumentId('')).toBe(false)
    })
  })

  describe('isValidSessionId (H5)', () => {
    it('should accept session-timestamp format', () => {
      expect(isValidSessionId('session-1234567890')).toBe(true)
      expect(isValidSessionId('session-1705420800000')).toBe(true)
    })

    it('should accept UUID format', () => {
      expect(isValidSessionId('550e8400-e29b-41d4-a716-446655440000')).toBe(true)
    })

    it('should reject invalid formats', () => {
      expect(isValidSessionId('invalid-session')).toBe(false)
      expect(isValidSessionId('../etc/passwd')).toBe(false)
      expect(isValidSessionId('session-<script>')).toBe(false)
    })

    it('should reject empty string', () => {
      expect(isValidSessionId('')).toBe(false)
    })
  })
})
