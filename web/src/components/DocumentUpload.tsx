import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Loader2, X, CheckCircle } from 'lucide-react'
import { uploadDocument } from '../api/client'

export default function DocumentUpload() {
  const queryClient = useQueryClient()
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => {
      setUploadSuccess(true)
      setUploadedFile(null)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setTimeout(() => setUploadSuccess(false), 3000)
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setUploadedFile(file)
      uploadMutation.mutate(file)
    }
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
  })

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
        transition-colors
        ${isDragActive
          ? 'border-geo-500 bg-geo-50'
          : uploadSuccess
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 hover:border-geo-400 hover:bg-gray-50'
        }
      `}
    >
      <input {...getInputProps()} />

      {uploadMutation.isPending ? (
        <div className="flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-geo-500 animate-spin mb-4" />
          <p className="text-gray-600">Uploading {uploadedFile?.name}...</p>
        </div>
      ) : uploadSuccess ? (
        <div className="flex flex-col items-center">
          <CheckCircle className="w-12 h-12 text-green-500 mb-4" />
          <p className="text-green-600 font-medium">Upload successful!</p>
        </div>
      ) : uploadMutation.isError ? (
        <div className="flex flex-col items-center">
          <X className="w-12 h-12 text-red-500 mb-4" />
          <p className="text-red-600 font-medium">Upload failed</p>
          <p className="text-sm text-red-500 mt-1">Please try again</p>
        </div>
      ) : isDragActive ? (
        <div className="flex flex-col items-center">
          <Upload className="w-12 h-12 text-geo-500 mb-4" />
          <p className="text-geo-600 font-medium">Drop the PDF here</p>
        </div>
      ) : (
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 bg-geo-100 rounded-full flex items-center justify-center mb-4">
            <FileText className="w-6 h-6 text-geo-600" />
          </div>
          <p className="text-gray-600 font-medium">
            Drag and drop a PDF file here, or click to browse
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Supports: PDF files only
          </p>
        </div>
      )}
    </div>
  )
}
