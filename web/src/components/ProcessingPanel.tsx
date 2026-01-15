import { Loader2, CheckCircle, XCircle, FileText, Sparkles, Code, CheckCheck } from 'lucide-react'
import { WorkflowStatus } from '../api/client'
import clsx from 'clsx'

interface ProcessingPanelProps {
  status: WorkflowStatus
}

const STEPS = [
  { id: 'extract_text', label: 'Extract Text', icon: FileText },
  { id: 'consolidate', label: 'Consolidate', icon: Sparkles },
  { id: 'generate_dsl', label: 'Generate DSL', icon: Code },
  { id: 'validate_dsl', label: 'Validate', icon: CheckCheck },
]

export default function ProcessingPanel({ status }: ProcessingPanelProps) {
  const currentStepIndex = STEPS.findIndex((s) => s.id === status.current_step)
  const isCompleted = status.status === 'completed'
  const isFailed = status.status === 'failed'

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-gray-900">Processing Document</h3>
        {status.progress !== null && (
          <span className="text-sm text-gray-500">
            {Math.round(status.progress * 100)}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-6">
        <div
          className={clsx(
            'h-full transition-all duration-500',
            isFailed ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-geo-500'
          )}
          style={{ width: `${(status.progress || 0) * 100}%` }}
        />
      </div>

      {/* Steps */}
      <div className="flex justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon
          const isActive = step.id === status.current_step
          const isPast = isCompleted || currentStepIndex > index
          const isCurrent = isActive && !isCompleted && !isFailed

          return (
            <div
              key={step.id}
              className="flex flex-col items-center"
            >
              <div
                className={clsx(
                  'w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-colors',
                  isPast && !isFailed
                    ? 'bg-green-100 text-green-600'
                    : isCurrent
                      ? 'bg-geo-100 text-geo-600'
                      : isFailed && isActive
                        ? 'bg-red-100 text-red-600'
                        : 'bg-gray-100 text-gray-400'
                )}
              >
                {isPast && !isFailed ? (
                  <CheckCircle className="w-5 h-5" />
                ) : isCurrent ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : isFailed && isActive ? (
                  <XCircle className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span
                className={clsx(
                  'text-xs font-medium',
                  isPast && !isFailed
                    ? 'text-green-600'
                    : isCurrent
                      ? 'text-geo-600'
                      : isFailed && isActive
                        ? 'text-red-600'
                        : 'text-gray-400'
                )}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Error message */}
      {isFailed && status.error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{status.error}</p>
        </div>
      )}
    </div>
  )
}
