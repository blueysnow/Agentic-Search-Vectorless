'use client'

import { useState, useMemo } from 'react'
import type { TreeNode } from '@/lib/api/types'

interface TreeVisualizationProps {
  rootNodeId?: string
  nodes: TreeNode[]
}

interface TreeNodeComponentProps {
  node: TreeNode
  nodes: TreeNode[]
  depth: number
}

function TreeNodeComponent({ node, nodes, depth }: TreeNodeComponentProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2) // Auto-expand first 2 levels

  const childNodes = useMemo(
    () => nodes.filter((n) => node.children.includes(n.nodeId)),
    [nodes, node.children]
  )

  const hasChildren = childNodes.length > 0
  const indentClass = `ml-${Math.min(depth * 4, 16)}`

  return (
    <div className="border-l-2 border-gray-200 pl-4 py-2">
      <div className="flex items-start gap-2">
        {hasChildren && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-1 text-gray-500 hover:text-gray-700 flex-shrink-0"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </button>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-gray-500">{node.nodeId}</span>
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">
              Level {node.level}
            </span>
            {node.metadata.pageNumber && (
              <span className="text-xs text-gray-600">
                Page {node.metadata.pageNumber}
              </span>
            )}
          </div>

          <p className="text-sm text-gray-700 line-clamp-3">{node.content}</p>

          {hasChildren && (
            <p className="text-xs text-gray-500 mt-1">
              {childNodes.length} child node{childNodes.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>
      </div>

      {isExpanded && hasChildren && (
        <div className="mt-2 space-y-2">
          {childNodes.map((childNode) => (
            <TreeNodeComponent
              key={childNode.nodeId}
              node={childNode}
              nodes={nodes}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function TreeVisualization({ rootNodeId, nodes }: TreeVisualizationProps) {
  const rootNode = useMemo(
    () => nodes.find((n) => n.nodeId === rootNodeId),
    [nodes, rootNodeId]
  )

  if (!rootNode) {
    return (
      <div className="p-6 border rounded-lg text-center text-muted-foreground">
        No tree structure available. Tree will be generated during document processing.
      </div>
    )
  }

  return (
    <div className="border rounded-lg p-4 bg-white overflow-x-auto">
      <div className="mb-4">
        <h3 className="font-semibold text-lg mb-1">Document Tree Structure</h3>
        <p className="text-sm text-muted-foreground">
          Hierarchical organization of {nodes.length} nodes
        </p>
      </div>

      <TreeNodeComponent node={rootNode} nodes={nodes} depth={0} />
    </div>
  )
}
