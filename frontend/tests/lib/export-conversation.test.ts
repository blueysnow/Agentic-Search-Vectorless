import { describe, it, expect } from 'vitest'
import { exportToMarkdown, exportToJSON } from '@/lib/export-conversation'
import type { ChatMessage } from '@/lib/hooks/use-chat-stream'

describe('exportToMarkdown', () => {
  it('exports simple conversation to markdown', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'What is the revenue?',
        timestamp: Date.now(),
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'The revenue is $1M.',
        timestamp: Date.now(),
      },
    ]

    const markdown = exportToMarkdown(messages)

    expect(markdown).toContain('# Conversation Export')
    expect(markdown).toContain('## User')
    expect(markdown).toContain('What is the revenue?')
    expect(markdown).toContain('## Assistant')
    expect(markdown).toContain('The revenue is $1M.')
  })

  it('includes thinking steps in markdown export', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Question',
        timestamp: Date.now(),
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'Answer',
        thinking: ['First I analyzed...', 'Then I concluded...'],
        timestamp: Date.now(),
      },
    ]

    const markdown = exportToMarkdown(messages)

    expect(markdown).toContain('### Thinking')
    expect(markdown).toContain('First I analyzed')
    expect(markdown).toContain('Then I concluded')
  })

  it('includes citations in markdown export', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Based on the document...',
        citations: [
          {
            page: 5,
            text: 'Revenue was $1M',
          },
        ],
        timestamp: Date.now(),
      },
    ]

    const markdown = exportToMarkdown(messages)

    expect(markdown).toContain('### Citations')
    expect(markdown).toContain('Page 5')
    expect(markdown).toContain('Revenue was $1M')
  })

  it('formats timestamps in markdown', () => {
    const timestamp = new Date('2024-01-15T10:30:00Z').getTime()
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp,
      },
    ]

    const markdown = exportToMarkdown(messages)

    // Should contain some form of the timestamp
    expect(markdown).toMatch(/2024/)
  })

  it('handles empty conversation', () => {
    const markdown = exportToMarkdown([])

    expect(markdown).toContain('# Conversation Export')
    expect(markdown).toContain('No messages')
  })

  it('exports conversation with metadata', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp: Date.now(),
      },
    ]

    const metadata = {
      sessionId: 'session-123',
      documentIds: ['doc-1', 'doc-2'],
      exportedAt: new Date().toISOString(),
    }

    const markdown = exportToMarkdown(messages, metadata)

    expect(markdown).toContain('session-123')
    expect(markdown).toContain('doc-1')
    expect(markdown).toContain('doc-2')
  })
})

describe('exportToJSON', () => {
  it('exports conversation to valid JSON', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Question',
        timestamp: Date.now(),
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: 'Answer',
        timestamp: Date.now(),
      },
    ]

    const json = exportToJSON(messages)
    const parsed = JSON.parse(json)

    expect(parsed.messages).toHaveLength(2)
    expect(parsed.messages[0].content).toBe('Question')
    expect(parsed.messages[1].content).toBe('Answer')
  })

  it('includes thinking steps in JSON export', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Answer',
        thinking: ['Thought process'],
        timestamp: Date.now(),
      },
    ]

    const json = exportToJSON(messages)
    const parsed = JSON.parse(json)

    expect(parsed.messages[0].thinking).toEqual(['Thought process'])
  })

  it('includes citations in JSON export', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Answer',
        citations: [
          {
            page: 3,
            text: 'Source text',
          },
        ],
        timestamp: Date.now(),
      },
    ]

    const json = exportToJSON(messages)
    const parsed = JSON.parse(json)

    expect(parsed.messages[0].citations).toHaveLength(1)
    expect(parsed.messages[0].citations[0].page).toBe(3)
    expect(parsed.messages[0].citations[0].text).toBe('Source text')
  })

  it('includes metadata in JSON export', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp: Date.now(),
      },
    ]

    const metadata = {
      sessionId: 'session-456',
      documentIds: ['doc-1'],
      exportedAt: new Date().toISOString(),
    }

    const json = exportToJSON(messages, metadata)
    const parsed = JSON.parse(json)

    expect(parsed.metadata.sessionId).toBe('session-456')
    expect(parsed.metadata.documentIds).toEqual(['doc-1'])
    expect(parsed.metadata.exportedAt).toBeDefined()
  })

  it('handles empty conversation in JSON', () => {
    const json = exportToJSON([])
    const parsed = JSON.parse(json)

    expect(parsed.messages).toEqual([])
  })

  it('preserves all message properties in JSON', () => {
    const messages: ChatMessage[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Content',
        thinking: ['Thinking'],
        citations: [
          {
            page: 1,
            text: 'Citation',
          },
        ],
        timestamp: 1234567890,
      },
    ]

    const json = exportToJSON(messages)
    const parsed = JSON.parse(json)

    expect(parsed.messages[0]).toEqual(messages[0])
  })
})
