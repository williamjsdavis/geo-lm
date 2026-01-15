import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Play, Loader2, CheckCircle, XCircle, FileText } from 'lucide-react'
import { fetchDocument, startProcessing, fetchWorkflowStatus } from '../api/client'
import DSLEditor from '../components/DSLEditor'
import ProcessingPanel from '../components/ProcessingPanel'

export default function DocumentView() {
  const { id } = useParams<{ id: string }>()
  const documentId = parseInt(id!, 10)
  const queryClient = useQueryClient()
  const [isProcessing, setIsProcessing] = useState(false)

  const { data: document, isLoading, error } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => fetchDocument(documentId),
    refetchInterval: isProcessing ? 2000 : false,
  })

  const processMutation = useMutation({
    mutationFn: () => startProcessing(documentId),
    onSuccess: () => {
      setIsProcessing(true)
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
    },
  })

  const { data: workflowStatus } = useQuery({
    queryKey: ['workflow-status', documentId],
    queryFn: () => fetchWorkflowStatus(documentId),
    enabled: isProcessing,
    refetchInterval: isProcessing ? 1000 : false,
  })

  // Stop polling when completed or failed
  if (workflowStatus && (workflowStatus.status === 'completed' || workflowStatus.status === 'failed')) {
    if (isProcessing) {
      setIsProcessing(false)
      queryClient.invalidateQueries({ queryKey: ['document', documentId] })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-geo-500 animate-spin" />
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        Failed to load document.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/"
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{document.title}</h1>
            <p className="text-sm text-gray-500">
              {document.created_at
                ? new Date(document.created_at).toLocaleDateString()
                : 'No date'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          {document.status === 'pending' && document.source_path && (
            <button
              onClick={() => processMutation.mutate()}
              disabled={processMutation.isPending || isProcessing}
              className="inline-flex items-center px-4 py-2 bg-geo-600 text-white rounded-lg hover:bg-geo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {processMutation.isPending || isProcessing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              Process Document
            </button>
          )}
          {document.status === 'completed' && (
            <span className="inline-flex items-center text-green-600">
              <CheckCircle className="w-5 h-5 mr-2" />
              Completed
            </span>
          )}
          {document.status === 'failed' && (
            <span className="inline-flex items-center text-red-600">
              <XCircle className="w-5 h-5 mr-2" />
              Failed
            </span>
          )}
        </div>
      </div>

      {/* Processing Status */}
      {isProcessing && workflowStatus && (
        <ProcessingPanel status={workflowStatus} />
      )}

      {/* Content Tabs */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Raw/Consolidated Text */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-medium text-gray-900">Text Content</h3>
          </div>
          <div className="p-4 max-h-96 overflow-y-auto">
            {document.consolidated_text ? (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Consolidated</h4>
                <p className="text-sm text-gray-600 whitespace-pre-wrap">
                  {document.consolidated_text}
                </p>
              </div>
            ) : document.raw_text ? (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Raw Text</h4>
                <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-[20]">
                  {document.raw_text.slice(0, 3000)}
                  {document.raw_text.length > 3000 && '...'}
                </p>
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No text content yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Process the document to extract text
                </p>
              </div>
            )}
          </div>
        </div>

        {/* DSL Editor */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-medium text-gray-900">Geology DSL</h3>
          </div>
          <DSLEditor documentId={documentId} />
        </div>
      </div>
    </div>
  )
}
