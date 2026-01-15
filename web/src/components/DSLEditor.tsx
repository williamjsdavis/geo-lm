import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import CodeMirror from '@uiw/react-codemirror'
import { CheckCircle, XCircle, AlertCircle, Play } from 'lucide-react'
import { parseDSL, DSLParseResult } from '../api/client'

interface DSLEditorProps {
  documentId: number
  initialDSL?: string
}

const EXAMPLE_DSL = `# Example Geology DSL
ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]
ROCK R2 [ name: "Granite"; type: intrusive; age: 50Ma ]

DEPOSITION D1 [ rock: R1; time: 100Ma ]
INTRUSION I1 [ rock: R2; style: stock; time: 50Ma; after: D1 ]`

export default function DSLEditor({ documentId, initialDSL }: DSLEditorProps) {
  const [dslText, setDSLText] = useState(initialDSL || '')
  const [validationResult, setValidationResult] = useState<DSLParseResult | null>(null)

  const validateMutation = useMutation({
    mutationFn: parseDSL,
    onSuccess: (result) => {
      setValidationResult(result)
    },
  })

  const handleValidate = () => {
    if (dslText.trim()) {
      validateMutation.mutate(dslText)
    }
  }

  // Auto-validate on change (debounced)
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (dslText.trim()) {
        validateMutation.mutate(dslText)
      } else {
        setValidationResult(null)
      }
    }, 500)

    return () => clearTimeout(timeout)
  }, [dslText])

  return (
    <div className="flex flex-col h-96">
      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={dslText}
          height="100%"
          onChange={(value) => setDSLText(value)}
          placeholder={EXAMPLE_DSL}
          basicSetup={{
            lineNumbers: true,
            highlightActiveLineGutter: true,
            highlightActiveLine: true,
            foldGutter: false,
          }}
          className="h-full text-sm"
        />
      </div>

      {/* Validation Results */}
      <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {validationResult === null ? (
              <span className="text-sm text-gray-500">Enter DSL to validate</span>
            ) : validationResult.is_valid ? (
              <span className="inline-flex items-center text-sm text-green-600">
                <CheckCircle className="w-4 h-4 mr-1" />
                Valid DSL
              </span>
            ) : (
              <span className="inline-flex items-center text-sm text-red-600">
                <XCircle className="w-4 h-4 mr-1" />
                {validationResult.errors.length} error(s)
              </span>
            )}

            {validationResult?.is_valid && (
              <span className="text-sm text-gray-500">
                {validationResult.rocks_count} rocks,{' '}
                {validationResult.depositions_count} depositions,{' '}
                {validationResult.erosions_count} erosions,{' '}
                {validationResult.intrusions_count} intrusions
              </span>
            )}
          </div>

          <button
            onClick={handleValidate}
            disabled={!dslText.trim() || validateMutation.isPending}
            className="inline-flex items-center px-3 py-1.5 text-sm bg-geo-600 text-white rounded hover:bg-geo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="w-3 h-3 mr-1" />
            Validate
          </button>
        </div>

        {/* Error list */}
        {validationResult && !validationResult.is_valid && validationResult.errors.length > 0 && (
          <div className="mt-3 space-y-1">
            {validationResult.errors.slice(0, 5).map((error, i) => (
              <div
                key={i}
                className="flex items-start text-sm text-red-600 bg-red-50 px-2 py-1 rounded"
              >
                <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                <span>
                  {error.line && `Line ${error.line}: `}
                  {error.message}
                </span>
              </div>
            ))}
            {validationResult.errors.length > 5 && (
              <p className="text-xs text-gray-500 pl-6">
                ...and {validationResult.errors.length - 5} more errors
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
