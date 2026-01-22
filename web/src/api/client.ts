// API client for geo-lm backend

const API_BASE = '/api'

export interface Document {
  id: number
  title: string
  source_path: string | null
  raw_text: string | null
  consolidated_text: string | null
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface DocumentList {
  documents: Document[]
  total: number
}

export interface DSLDocument {
  id: number
  document_id: number | null
  raw_dsl: string
  is_valid: boolean
  validation_errors: string | null
  created_at: string | null
}

export interface DSLParseResult {
  is_valid: boolean
  errors: Array<{
    message: string
    line: number | null
    column: number | null
  }>
  rocks_count: number
  depositions_count: number
  erosions_count: number
  intrusions_count: number
}

export interface WorkflowStatus {
  status: string
  current_step: string | null
  progress: number | null
  error: string | null
}

// Model types
export interface ModelBuildRequest {
  dsl_document_id: number
  name?: string
}

export interface ModelBuildResponse {
  model_id: number | null
  status: string
  errors: string[]
  warnings: string[]
}

export interface ModelExtent {
  x_min: number
  x_max: number
  y_min: number
  y_max: number
  z_min: number
  z_max: number
}

export interface SurfaceMesh {
  name: string
  surface_id: string
  color: string
  vertices: number[][]
  faces: number[][]
}

export interface ModelMesh {
  model_id: number
  name: string
  surfaces: SurfaceMesh[]
  extent: ModelExtent
}

export interface GeologicalModel {
  id: number
  name: string
  document_id: number | null
  dsl_document_id: number | null
  status: string
  created_at: string | null
  updated_at: string | null
}

// Documents API
export async function fetchDocuments(): Promise<DocumentList> {
  const response = await fetch(`${API_BASE}/documents`)
  if (!response.ok) {
    throw new Error('Failed to fetch documents')
  }
  return response.json()
}

export async function fetchDocument(id: number): Promise<Document> {
  const response = await fetch(`${API_BASE}/documents/${id}`)
  if (!response.ok) {
    throw new Error('Failed to fetch document')
  }
  return response.json()
}

export async function createDocument(title: string): Promise<Document> {
  const response = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  if (!response.ok) {
    throw new Error('Failed to create document')
  }
  return response.json()
}

export async function uploadDocument(file: File, title?: string): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }

  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    throw new Error('Failed to upload document')
  }
  return response.json()
}

export async function deleteDocument(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error('Failed to delete document')
  }
}

// DSL API
export async function parseDSL(dslText: string): Promise<DSLParseResult> {
  const response = await fetch(`${API_BASE}/dsl/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dsl_text: dslText }),
  })
  if (!response.ok) {
    throw new Error('Failed to parse DSL')
  }
  return response.json()
}

export async function fetchDSLDocument(id: number): Promise<DSLDocument> {
  const response = await fetch(`${API_BASE}/dsl/${id}`)
  if (!response.ok) {
    throw new Error('Failed to fetch DSL document')
  }
  return response.json()
}

export async function fetchDSLByDocumentId(documentId: number): Promise<DSLDocument | null> {
  const response = await fetch(`${API_BASE}/dsl/by-document/${documentId}`)
  if (response.status === 404) {
    return null
  }
  if (!response.ok) {
    throw new Error('Failed to fetch DSL document')
  }
  return response.json()
}

// Workflow API
export async function startProcessing(documentId: number): Promise<WorkflowStatus> {
  const response = await fetch(`${API_BASE}/workflows/${documentId}/process`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to start processing')
  }
  return response.json()
}

export async function fetchWorkflowStatus(documentId: number): Promise<WorkflowStatus> {
  const response = await fetch(`${API_BASE}/workflows/${documentId}/status`)
  if (!response.ok) {
    throw new Error('Failed to fetch workflow status')
  }
  return response.json()
}

// Health check
export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error('API not available')
  }
  return response.json()
}

// Models API
export async function buildModel(request: ModelBuildRequest): Promise<ModelBuildResponse> {
  const response = await fetch(`${API_BASE}/models/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to build model' }))
    throw new Error(error.detail || 'Failed to build model')
  }
  return response.json()
}

export async function fetchModelMesh(modelId: number, compute: boolean = true): Promise<ModelMesh> {
  const url = new URL(`${API_BASE}/models/${modelId}/mesh`, window.location.origin)
  url.searchParams.set('compute', compute.toString())

  const response = await fetch(url.toString())
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch model mesh' }))
    throw new Error(error.detail || 'Failed to fetch model mesh')
  }
  return response.json()
}

export async function fetchModelsByDsl(dslDocumentId: number): Promise<{ models: GeologicalModel[]; total: number }> {
  const response = await fetch(`${API_BASE}/models/by-dsl/${dslDocumentId}`)
  if (!response.ok) {
    throw new Error('Failed to fetch models')
  }
  return response.json()
}
