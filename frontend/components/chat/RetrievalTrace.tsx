'use client'

interface RetrievalStep {
  type: 'query' | 'filter' | 'retrieve' | 'rank'
  description: string
  details?: Record<string, unknown>
  timestamp?: number
}

interface RetrievalTraceProps {
  steps: RetrievalStep[]
  className?: string
}

/**
 * Visualizes the retrieval process as a tree navigation path
 * Shows how the system navigated through documents during retrieval
 */
export function RetrievalTrace({ steps, className = '' }: RetrievalTraceProps) {
  if (!steps || steps.length === 0) {
    return null
  }

  return (
    <div className={`bg-gray-50 rounded-lg border p-4 ${className}`}>
      <h4 className="text-sm font-semibold text-gray-700 mb-3">Retrieval Trace</h4>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={index} className="flex gap-3">
            {/* Tree connector */}
            <div className="flex flex-col items-center">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${getStepColor(step.type)}`}>
                {index + 1}
              </div>
              {index < steps.length - 1 && (
                <div className="w-0.5 h-full bg-gray-300 mt-1"></div>
              )}
            </div>

            {/* Step content */}
            <div className="flex-1 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-gray-500 uppercase">
                  {step.type}
                </span>
                {step.timestamp && (
                  <span className="text-xs text-gray-400">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-900">{step.description}</p>

              {/* Show details if present */}
              {step.details && Object.keys(step.details).length > 0 && (
                <details className="mt-2">
                  <summary className="text-xs text-blue-600 cursor-pointer hover:text-blue-800">
                    Show details
                  </summary>
                  <pre className="mt-2 p-2 bg-white rounded border text-xs overflow-x-auto">
                    {JSON.stringify(step.details, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getStepColor(type: RetrievalStep['type']): string {
  switch (type) {
    case 'query':
      return 'bg-blue-100 text-blue-700'
    case 'filter':
      return 'bg-purple-100 text-purple-700'
    case 'retrieve':
      return 'bg-green-100 text-green-700'
    case 'rank':
      return 'bg-orange-100 text-orange-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}
