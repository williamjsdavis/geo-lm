"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# --- Document Schemas ---


class DocumentCreate(BaseModel):
    """Schema for creating a document."""

    title: str = Field(..., min_length=1, max_length=255)


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: int
    title: str
    source_path: Optional[str] = None
    raw_text: Optional[str] = None
    consolidated_text: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for list of documents."""

    documents: List[DocumentResponse]
    total: int


# --- DSL Schemas ---


class DSLParseRequest(BaseModel):
    """Schema for DSL parsing request."""

    dsl_text: str = Field(..., min_length=1)


class DSLValidationError(BaseModel):
    """Schema for a validation error."""

    message: str
    line: Optional[int] = None
    column: Optional[int] = None


class DSLParseResponse(BaseModel):
    """Schema for DSL parsing response."""

    is_valid: bool
    errors: List[DSLValidationError] = []
    rocks_count: int = 0
    depositions_count: int = 0
    erosions_count: int = 0
    intrusions_count: int = 0


class DSLDocumentResponse(BaseModel):
    """Schema for DSL document response."""

    id: int
    document_id: Optional[int] = None
    raw_dsl: str
    is_valid: bool
    validation_errors: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Model Schemas ---


class GeologicalModelCreate(BaseModel):
    """Schema for creating a geological model."""

    name: str = Field(..., min_length=1, max_length=255)
    document_id: Optional[int] = None
    dsl_document_id: Optional[int] = None


class GeologicalModelResponse(BaseModel):
    """Schema for geological model response."""

    id: int
    name: str
    document_id: Optional[int] = None
    dsl_document_id: Optional[int] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelBuildRequest(BaseModel):
    """Schema for model build request."""

    dsl_document_id: int = Field(..., description="ID of the DSL document to build from")
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Optional custom model name"
    )


class ModelBuildResponse(BaseModel):
    """Schema for model build response."""

    model_id: Optional[int] = None
    status: str
    errors: List[str] = []
    warnings: List[str] = []


class StructuralGroupInfo(BaseModel):
    """Schema for structural group info in model data."""

    group_name: str
    surfaces: List[str]
    relation: str


class ModelDataResponse(BaseModel):
    """Schema for detailed model data response."""

    id: int
    name: str
    status: str
    document_id: Optional[int] = None
    dsl_document_id: Optional[int] = None
    extent: dict = {}
    resolution: dict = {}
    surface_points_count: int = 0
    orientations_count: int = 0
    structural_groups: List[StructuralGroupInfo] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ModelListResponse(BaseModel):
    """Schema for list of models."""

    models: List[GeologicalModelResponse]
    total: int


# --- Workflow Schemas ---


class WorkflowRequest(BaseModel):
    """Schema for workflow execution request."""

    document_id: int


class WorkflowStatusResponse(BaseModel):
    """Schema for workflow status response."""

    status: str  # pending, running, completed, failed
    current_step: Optional[str] = None
    progress: Optional[float] = None
    error: Optional[str] = None


# --- Settings Schemas ---


class SettingsResponse(BaseModel):
    """Schema for settings response."""

    default_model: str
    default_consolidation_model: str
    default_dsl_model: str


class SettingsUpdate(BaseModel):
    """Schema for settings update."""

    default_model: Optional[str] = None
    default_consolidation_model: Optional[str] = None
    default_dsl_model: Optional[str] = None


# --- Health Check ---


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str = "ok"
    version: str
    database: str = "connected"


# --- Mesh Schemas ---


class ModelExtentResponse(BaseModel):
    """Schema for model spatial extent."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float


class SurfaceMeshResponse(BaseModel):
    """Schema for a single surface mesh."""

    name: str = Field(description="Surface name")
    surface_id: str = Field(description="Surface ID from DSL")
    color: str = Field(description="Hex color code")
    vertices: List[List[float]] = Field(description="[[x,y,z], ...] vertex coordinates")
    faces: List[List[int]] = Field(description="[[i,j,k], ...] triangle indices")


class ModelMeshResponse(BaseModel):
    """Schema for complete model mesh data for 3D visualization."""

    model_id: int
    name: str
    surfaces: List[SurfaceMeshResponse]
    extent: ModelExtentResponse
