/**
 * Security utilities for sanitization and validation
 */

/**
 * H2/H3: Sanitizes markdown content to prevent XSS attacks
 * Escapes HTML entities in user-generated content
 */
export function sanitizeMarkdown(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

/**
 * H4: Validates document ID format
 * Only allows alphanumeric characters, hyphens, and underscores
 */
export function isValidDocumentId(id: string): boolean {
  return /^[a-zA-Z0-9_-]+$/.test(id)
}

/**
 * H5: Validates session ID format
 * Matches pattern: session-{timestamp} or UUID format
 */
export function isValidSessionId(id: string): boolean {
  // Matches: session-1234567890 or UUID format
  return /^(session-\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i.test(id)
}
