export const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  endpoints: {
    documents: '/documents',
    ingest: '/ingest',
    query: '/query',
    sessions: '/sessions',
  },
  timeouts: {
    upload: 300000, // 5 min for large PDF uploads
    query: 60000, // 1 min for streaming queries
    default: 10000, // 10s for standard requests
  },
} as const
