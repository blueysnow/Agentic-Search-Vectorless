import { API_CONFIG } from '../config'
import type {
  Document,
  DocumentFilters,
  IngestResponse,
  Session,
  QueryRequest,
  QueryResponse,
} from './types'

class APIClient {
  private baseUrl: string
  private readonly DEFAULT_TIMEOUT = 10000 // 10 seconds
  private readonly QUERY_TIMEOUT = 60000 // 60 seconds
  private readonly UPLOAD_TIMEOUT = 300000 // 300 seconds (5 minutes)

  constructor() {
    this.baseUrl = API_CONFIG.baseUrl
  }

  async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // SF-011 Fix: Add timeout with AbortController
    const controller = new AbortController()

    // Determine timeout based on endpoint
    const timeout = endpoint.includes('/query') ? this.QUERY_TIMEOUT : this.DEFAULT_TIMEOUT

    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      const res = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!res.ok) {
        let errorDetail = `HTTP ${res.status} ${res.statusText}`
        try {
          const errorBody = await res.json()
          errorDetail = errorBody.detail || errorDetail
        } catch (parseError) {
          console.error('Failed to parse error response:', parseError)
        }
        throw new Error(`${errorDetail} (${res.status})`)
      }

      return res.json()
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${timeout}ms`)
      }
      throw error
    }
  }

  // Documents
  async uploadDocument(formData: FormData): Promise<IngestResponse> {
    // SF-011 Fix: Add timeout with AbortController for uploads
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.UPLOAD_TIMEOUT)

    try {
      const res = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.ingest}/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        // Let browser set Content-Type for FormData (multipart/form-data boundary)
      })

      clearTimeout(timeoutId)

      if (!res.ok) {
        let errorDetail = `Upload failed: HTTP ${res.status} ${res.statusText}`
        try {
          const errorBody = await res.json()
          errorDetail = errorBody.detail || errorDetail
        } catch (parseError) {
          console.error('Failed to parse upload error response:', parseError)
        }
        throw new Error(`${errorDetail} (${res.status})`)
      }

      return res.json()
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Upload timeout after ${this.UPLOAD_TIMEOUT}ms`)
      }
      throw error
    }
  }

  // Upload with XHR progress tracking (fetch API has no upload progress support)
  uploadDocumentWithProgress(
    formData: FormData,
    onProgress: (percent: number) => void
  ): Promise<IngestResponse> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${this.baseUrl}${API_CONFIG.endpoints.ingest}/upload`)
      xhr.timeout = this.UPLOAD_TIMEOUT

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          // Cap at 99% - the final 100% is reached only when the server responds.
          // This distinguishes "data transfer complete" from "server processing complete".
          const percent = Math.min(99, Math.round((e.loaded / e.total) * 100))
          onProgress(percent)
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText))
          } catch {
            reject(new Error('Failed to parse upload response'))
          }
        } else {
          let errorDetail = `Upload failed: HTTP ${xhr.status} ${xhr.statusText}`
          try {
            const errorBody = JSON.parse(xhr.responseText)
            errorDetail = errorBody.detail || errorDetail
          } catch {
            // Use default error detail
          }
          reject(new Error(`${errorDetail} (${xhr.status})`))
        }
      })

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed: Network error'))
      })

      xhr.addEventListener('timeout', () => {
        reject(new Error(`Upload timeout after ${this.UPLOAD_TIMEOUT}ms`))
      })

      xhr.send(formData)
    })
  }

  async getDocuments(filters?: DocumentFilters): Promise<Document[]> {
    const params = new URLSearchParams(filters as Record<string, string>)
    const response = await this.fetch<{ documents: Document[]; total: number } | Document[]>(
      `${API_CONFIG.endpoints.documents}?${params}`
    )
    // Backend returns { documents: Document[], total: number } - unwrap it
    if (Array.isArray(response)) {
      return response
    }
    return response.documents
  }

  async getDocument(id: string): Promise<Document> {
    return this.fetch(`${API_CONFIG.endpoints.documents}/${id}`)
  }

  // Sessions
  async getSessions(params?: {
    documentId?: string
    limit?: number
  }): Promise<Session[]> {
    const query = new URLSearchParams(params as Record<string, string>)
    return this.fetch(`${API_CONFIG.endpoints.sessions}?${query}`)
  }

  async getSession(id: string): Promise<Session> {
    return this.fetch(`${API_CONFIG.endpoints.sessions}/${id}`)
  }

  // Query
  async query(request: QueryRequest): Promise<QueryResponse> {
    return this.fetch(API_CONFIG.endpoints.query, {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }
}

export const apiClient = new APIClient()
