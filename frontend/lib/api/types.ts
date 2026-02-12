export interface Document {
  documentId: string
  name: string
  type: 'pdf' | 'markdown'
  domain?: string
  description?: string
  totalPages: number
  totalNodes: number
  totalTokens: number
  rootNodeId?: string
  ingestion: {
    status: 'pending' | 'processing' | 'completed' | 'failed'
    model?: string
    startedAt?: string
    completedAt?: string
    errors: string[]
  }
  createdAt: string
  updatedAt: string
}

export interface Session {
  sessionId: string
  documentId?: string
  userId?: string
  turns: Turn[]
  createdAt: string
  updatedAt: string
}

export interface Turn {
  turnNumber: number
  query: string
  retrievalTrace: {
    atlasSearchHits: Array<{ nodeId: string; score: number }>
    treeNavigationPath: string[]
    nodesRead: string[]
    totalNodesVisited: number
    reasoningDepth: number
  }
  answer?: string
  model?: string
  latencyMs: number
  timestamp: string
}

export interface DocumentFilters {
  status?: 'pending' | 'processing' | 'completed' | 'failed'
  domain?: string
  q?: string
}

export interface QueryRequest {
  query: string
  documentId: string
  sessionId?: string
}

export interface QueryResponse {
  sessionId: string
  turnNumber: number
  answer: string
  retrievalTrace: Turn['retrievalTrace']
}

export interface TreeNode {
  nodeId: string
  parentId?: string
  level: number
  content: string
  metadata: {
    pageNumber?: number
    section?: string
  }
  children: string[]
}
