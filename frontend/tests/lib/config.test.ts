import { describe, it, expect } from 'vitest'
import { API_CONFIG } from '@/lib/config'

describe('API_CONFIG', () => {
  it('should have baseUrl configured', () => {
    expect(API_CONFIG.baseUrl).toBeDefined()
    expect(typeof API_CONFIG.baseUrl).toBe('string')
  })

  it('should have all endpoints defined without /api prefix (backend routes are /documents, /ingest, /query, /sessions)', () => {
    expect(API_CONFIG.endpoints.documents).toBe('/documents')
    expect(API_CONFIG.endpoints.ingest).toBe('/ingest')
    expect(API_CONFIG.endpoints.query).toBe('/query')
    expect(API_CONFIG.endpoints.sessions).toBe('/sessions')
  })

  it('should have timeout configurations', () => {
    expect(API_CONFIG.timeouts.upload).toBe(300000)
    expect(API_CONFIG.timeouts.query).toBe(60000)
    expect(API_CONFIG.timeouts.default).toBe(10000)
  })
})
