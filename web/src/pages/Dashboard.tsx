import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileText, Trash2, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { fetchDocuments, deleteDocument, Document } from '../api/client'
import DocumentUpload from '../components/DocumentUpload'

function StatusBadge({ status }: { status: string }) {
  const config = {
    pending: { icon: Clock, color: 'text-yellow-500 bg-yellow-50', label: 'Pending' },
    processing: { icon: Loader2, color: 'text-blue-500 bg-blue-50 animate-spin', label: 'Processing' },
    completed: { icon: CheckCircle, color: 'text-green-500 bg-green-50', label: 'Completed' },
    failed: { icon: XCircle, color: 'text-red-500 bg-red-50', label: 'Failed' },
  }[status] || { icon: Clock, color: 'text-gray-500 bg-gray-50', label: status }

  const Icon = config.icon

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="w-3 h-3 mr-1" />
      {config.label}
    </span>
  )
}

function DocumentCard({ document, onDelete }: { document: Document; onDelete: () => void }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center">
          <FileText className="w-8 h-8 text-geo-500 mr-3" />
          <div>
            <Link
              to={`/documents/${document.id}`}
              className="text-lg font-medium text-gray-900 hover:text-geo-600"
            >
              {document.title}
            </Link>
            <p className="text-sm text-gray-500">
              {document.created_at
                ? new Date(document.created_at).toLocaleDateString()
                : 'No date'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <StatusBadge status={document.status} />
          <button
            onClick={(e) => {
              e.preventDefault()
              onDelete()
            }}
            className="p-1 text-gray-400 hover:text-red-500 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      {document.source_path && (
        <p className="mt-2 text-xs text-gray-400 truncate">
          Source: {document.source_path.split('/').pop()}
        </p>
      )}
    </div>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500 mt-1">
            Upload and process geological documents
          </p>
        </div>
      </div>

      {/* Upload Section */}
      <DocumentUpload />

      {/* Documents List */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Recent Documents</h2>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-geo-500 animate-spin" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Failed to load documents. Is the API running?
          </div>
        )}

        {data && data.documents.length === 0 && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No documents yet. Upload a PDF to get started.</p>
          </div>
        )}

        {data && data.documents.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.documents.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onDelete={() => handleDelete(doc.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
