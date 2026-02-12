'use client'

interface ThinkingProcessProps {
  steps: string[]
}

export function ThinkingProcess({ steps }: ThinkingProcessProps) {
  if (!steps || steps.length === 0) return null

  return (
    <div className="text-sm text-gray-500 space-y-1" data-testid="thinking-process">
      {steps.map((step, idx) => (
        <div key={idx} className="italic">
          → {step}
        </div>
      ))}
    </div>
  )
}
