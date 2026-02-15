import { describe, it, expect } from 'vitest'
import {
  documentUploadSchema,
  sanitizeFilename,
  validateFileType,
  validateFileSize,
  FILE_VALIDATION,
} from '@/lib/validation/document'

describe('documentUploadSchema', () => {
  it('should validate valid PDF file', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(true)
  })

  it('should validate valid Markdown file', () => {
    const file = new File(['content'], 'test.md', { type: 'text/markdown' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(true)
  })

  it('should reject file larger than 50MB', () => {
    const largeContent = new Array(51 * 1024 * 1024).fill('x').join('')
    const file = new File([largeContent], 'large.pdf', { type: 'application/pdf' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.errors[0].message).toContain('50MB')
    }
  })

  it('should validate valid Text file', () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(true)
  })

  it('should reject invalid file type', () => {
    const file = new File(['content'], 'test.exe', { type: 'application/octet-stream' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.errors[0].message).toContain('PDF, Markdown, or Text')
    }
  })

  it('should accept file with valid extension even if MIME type is missing', () => {
    const file = new File(['content'], 'test.pdf', { type: '' })
    const result = documentUploadSchema.safeParse({ file })
    expect(result.success).toBe(true)
  })

  it('should accept optional domain and description', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    const result = documentUploadSchema.safeParse({
      file,
      domain: 'science',
      description: 'A scientific paper',
    })
    expect(result.success).toBe(true)
  })
})

describe('sanitizeFilename', () => {
  it('should remove path traversal attempts', () => {
    expect(sanitizeFilename('../../../etc/passwd')).toBe('___etc_passwd')
  })

  it('should replace dangerous characters', () => {
    expect(sanitizeFilename('test<>:"/\\|?*.pdf')).toBe('test_________.pdf')
  })

  it('should limit filename length to 255 characters', () => {
    const longName = 'a'.repeat(300) + '.pdf'
    const sanitized = sanitizeFilename(longName)
    expect(sanitized.length).toBeLessThanOrEqual(255)
    expect(sanitized.endsWith('.pdf')).toBe(true)
  })

  it('should preserve valid filenames', () => {
    expect(sanitizeFilename('valid-filename_123.pdf')).toBe('valid-filename_123.pdf')
  })
})

describe('validateFileType', () => {
  it('should validate PDF by MIME type', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    expect(validateFileType(file)).toBe(true)
  })

  it('should validate Markdown by MIME type', () => {
    const file = new File(['content'], 'test.md', { type: 'text/markdown' })
    expect(validateFileType(file)).toBe(true)
  })

  it('should validate by extension if MIME type is missing', () => {
    const file = new File(['content'], 'test.pdf', { type: '' })
    expect(validateFileType(file)).toBe(true)
  })

  it('should validate Text by MIME type', () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    expect(validateFileType(file)).toBe(true)
  })

  it('should reject invalid file type', () => {
    const file = new File(['content'], 'test.exe', { type: 'application/octet-stream' })
    expect(validateFileType(file)).toBe(false)
  })
})

describe('validateFileSize', () => {
  it('should accept file under 50MB', () => {
    const file = new File(['small content'], 'test.pdf', { type: 'application/pdf' })
    expect(validateFileSize(file)).toBe(true)
  })

  it('should reject file over 50MB', () => {
    const largeContent = new Array(51 * 1024 * 1024).fill('x').join('')
    const file = new File([largeContent], 'large.pdf', { type: 'application/pdf' })
    expect(validateFileSize(file)).toBe(false)
  })

  it('should accept file exactly 50MB', () => {
    const content = new Array(FILE_VALIDATION.MAX_FILE_SIZE).fill('x').join('')
    const file = new File([content], 'exactly.pdf', { type: 'application/pdf' })
    expect(validateFileSize(file)).toBe(true)
  })
})
