import type { ChatMessage } from './hooks/use-chat-stream'
import { sanitizeMarkdown } from './security'

interface ExportMetadata {
  sessionId?: string
  documentIds?: string[]
  exportedAt?: string
}

/**
 * Exports conversation messages to Markdown format
 */
export function exportToMarkdown(
  messages: ChatMessage[],
  metadata?: ExportMetadata
): string {
  let markdown = '# Conversation Export\n\n'

  // Add metadata if provided - H-REM3-3: Sanitize all metadata fields
  if (metadata) {
    markdown += '## Metadata\n\n'
    if (metadata.sessionId) {
      markdown += `- **Session ID**: ${sanitizeMarkdown(metadata.sessionId)}\n`
    }
    if (metadata.documentIds && metadata.documentIds.length > 0) {
      const sanitizedDocIds = metadata.documentIds.map(id => sanitizeMarkdown(id))
      markdown += `- **Documents**: ${sanitizedDocIds.join(', ')}\n`
    }
    if (metadata.exportedAt) {
      markdown += `- **Exported**: ${sanitizeMarkdown(metadata.exportedAt)}\n`
    }
    markdown += '\n'
  }

  // Handle empty conversation
  if (messages.length === 0) {
    markdown += '*No messages in this conversation.*\n'
    return markdown
  }

  // Add each message
  markdown += '## Messages\n\n'
  messages.forEach((message, index) => {
    // Message header
    const role = message.role === 'user' ? 'User' : 'Assistant'
    const timestamp = new Date(message.timestamp).toISOString()
    markdown += `### ${role}\n\n`
    markdown += `*${timestamp}*\n\n`

    // Thinking steps (if present) - H-REM3-2: Sanitize thinking text
    if (message.thinking && message.thinking.length > 0) {
      markdown += '#### Thinking\n\n'
      const sanitizedThinking = message.thinking.map(step => sanitizeMarkdown(step))
      markdown += `${sanitizedThinking.join('\n')}\n\n`
    }

    // Main content (H2: Sanitize to prevent XSS)
    markdown += `${sanitizeMarkdown(message.content)}\n\n`

    // Citations (if present)
    if (message.citations && message.citations.length > 0) {
      markdown += '#### Citations\n\n'
      message.citations.forEach((citation, citationIndex) => {
        markdown += `${citationIndex + 1}. Page ${citation.page}\n`
        // H3: Sanitize citation text to prevent XSS
        markdown += `   > ${sanitizeMarkdown(citation.text)}\n\n`
      })
    }

    // Metadata (if present) - H-REM3-3: Sanitize metadata fields
    if (message.metadata) {
      markdown += '#### Metadata\n\n'
      if (message.metadata.doc_name) {
        markdown += `- **Document**: ${sanitizeMarkdown(message.metadata.doc_name)}\n`
      }
      if (message.metadata.pages) {
        markdown += `- **Pages**: ${message.metadata.pages}\n`
      }
      markdown += '\n'
    }

    // Add separator between messages (except for last)
    if (index < messages.length - 1) {
      markdown += '---\n\n'
    }
  })

  return markdown
}

/**
 * Exports conversation messages to JSON format
 */
export function exportToJSON(
  messages: ChatMessage[],
  metadata?: ExportMetadata
): string {
  const data = {
    version: '1.0',
    exportedAt: new Date().toISOString(),
    metadata: metadata || {},
    messages: messages,
  }

  return JSON.stringify(data, null, 2)
}

/**
 * Triggers a download of the conversation in the specified format
 */
export function downloadConversation(
  messages: ChatMessage[],
  format: 'markdown' | 'json',
  filename?: string,
  metadata?: ExportMetadata
): void {
  try {
    const content = format === 'markdown'
      ? exportToMarkdown(messages, metadata)
      : exportToJSON(messages, metadata)

    const mimeType = format === 'markdown' ? 'text/markdown' : 'application/json'
    const extension = format === 'markdown' ? 'md' : 'json'
    const defaultFilename = `conversation-${Date.now()}.${extension}`

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)

    try {
      const link = document.createElement('a')
      link.href = url
      link.download = filename || defaultFilename
      link.click()
    } finally {
      // Always clean up the object URL
      URL.revokeObjectURL(url)
    }
  } catch (error) {
    console.error('Failed to download conversation:', error)
    throw new Error('Failed to download conversation')
  }
}
