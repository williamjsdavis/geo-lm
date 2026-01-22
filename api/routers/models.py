"""Geological model building and management API routes."""

from fastapi import APIRouter, HTTPException, status

from geo_lm.domain import DSLDocument, GeologicalModel
from geo_lm.exceptions import NotFoundError
from geo_lm.graphs.model import build_model_from_dsl
from geo_lm.gempy.persistence import GemPyPersistenceService
from geo_lm.gempy.exporter import export_model_mesh
from api.models import (
    ModelBuildRequest,
    ModelBuildResponse,
    ModelDataResponse,
    ModelListResponse,
    GeologicalModelResponse,
    StructuralGroupInfo,
    ModelMeshResponse,
    SurfaceMeshResponse,
    ModelExtentResponse,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/build", response_model=ModelBuildResponse)
async def build_model(request: ModelBuildRequest):
    """Build a 3D geological model from a validated DSL document.

    The workflow:
    1. Parse and validate DSL (must be valid)
    2. Transform to GemPy configuration
    3. Generate spatial data (rule-based)
    4. Build and compute GemPy model
    5. Persist to database
    """
    # Fetch DSL document
    try:
        dsl_doc = await DSLDocument.get(request.dsl_document_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DSL document {request.dsl_document_id} not found",
        )

    if not dsl_doc.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DSL document must be valid before building model. "
            f"Validation errors: {dsl_doc.validation_errors}",
        )

    # Run the model building workflow
    final_state = await build_model_from_dsl(
        dsl_document_id=request.dsl_document_id,
        dsl_text=dsl_doc.raw_dsl,
        model_name=request.name,
    )

    return ModelBuildResponse(
        model_id=final_state.get("model_id"),
        status=final_state["status"],
        errors=final_state.get("errors", []),
        warnings=final_state.get("warnings", []),
    )


@router.get("", response_model=ModelListResponse)
async def list_models():
    """List all geological models."""
    models = await GeologicalModel.get_all(order_by="created_at DESC")
    return ModelListResponse(
        models=[GeologicalModelResponse.model_validate(m) for m in models],
        total=len(models),
    )


@router.get("/test/mesh", response_model=ModelMeshResponse)
async def get_test_mesh():
    """Return hardcoded test mesh data for frontend debugging.

    Creates 3 flat colored planes at different Z levels to verify
    the frontend Three.js rendering works correctly.
    """
    def create_flat_plane(z_level: float, size: float, color: str, name: str):
        half = size / 2
        return SurfaceMeshResponse(
            name=name,
            surface_id=name,
            color=color,
            vertices=[
                [-half, -half, z_level],
                [half, -half, z_level],
                [half, half, z_level],
                [-half, half, z_level],
            ],
            faces=[
                [0, 1, 2],
                [0, 2, 3],
            ],
        )

    return ModelMeshResponse(
        model_id=9999,
        name="TestPlanes",
        surfaces=[
            create_flat_plane(-200, 400, "#FF0000", "RedPlane"),
            create_flat_plane(-400, 400, "#00FF00", "GreenPlane"),
            create_flat_plane(-600, 400, "#0000FF", "BluePlane"),
        ],
        extent=ModelExtentResponse(
            x_min=-500,
            x_max=500,
            y_min=-500,
            y_max=500,
            z_min=-800,
            z_max=0,
        ),
    )


@router.get("/{model_id}", response_model=ModelDataResponse)
async def get_model(model_id: int):
    """Get detailed model data and summary."""
    persistence = GemPyPersistenceService()
    summary = await persistence.get_model_summary(model_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    # Convert structural groups to schema
    structural_groups = [
        StructuralGroupInfo(
            group_name=g["group_name"],
            surfaces=g["surfaces"],
            relation=g["relation"],
        )
        for g in summary.get("structural_groups", [])
    ]

    return ModelDataResponse(
        id=summary["id"],
        name=summary["name"],
        status=summary["status"],
        document_id=summary.get("document_id"),
        dsl_document_id=summary.get("dsl_document_id"),
        extent=summary.get("extent", {}),
        resolution=summary.get("resolution", {}),
        surface_points_count=summary.get("surface_points_count", 0),
        orientations_count=summary.get("orientations_count", 0),
        structural_groups=structural_groups,
        created_at=summary.get("created_at"),
        updated_at=summary.get("updated_at"),
    )


@router.get("/{model_id}/basic", response_model=GeologicalModelResponse)
async def get_model_basic(model_id: int):
    """Get basic model information."""
    try:
        model = await GeologicalModel.get(model_id)
        return GeologicalModelResponse.model_validate(model)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )


@router.get("/{model_id}/mesh", response_model=ModelMeshResponse)
async def get_model_mesh(model_id: int, compute: bool = True):
    """Export model mesh data for 3D visualization.

    This endpoint loads the model data from the database, rebuilds the
    GemPy model, and extracts mesh vertices/faces for each surface.

    Args:
        model_id: The model ID to export
        compute: If True (default), compute full meshes using GemPy.
                 If False, return point cloud representation (faster).

    Returns:
        ModelMeshResponse with vertices and faces for each surface
    """
    persistence = GemPyPersistenceService()

    # Load model data from database
    model_data = await persistence.load_model_data(model_id)
    if not model_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )

    try:
        # Export mesh data
        mesh_data = export_model_mesh(
            model_id=model_id,
            data=model_data,
            compute_meshes=compute,
        )

        # Convert to response schema
        return ModelMeshResponse(
            model_id=mesh_data.model_id,
            name=mesh_data.name,
            surfaces=[
                SurfaceMeshResponse(
                    name=s.name,
                    surface_id=s.surface_id,
                    color=s.color,
                    vertices=s.vertices,
                    faces=s.faces,
                )
                for s in mesh_data.surfaces
            ],
            extent=ModelExtentResponse(
                x_min=mesh_data.extent.x_min,
                x_max=mesh_data.extent.x_max,
                y_min=mesh_data.extent.y_min,
                y_max=mesh_data.extent.y_max,
                z_min=mesh_data.extent.z_min,
                z_max=mesh_data.extent.z_max,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export mesh: {str(e)}",
        )


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: int):
    """Delete a geological model and all associated data.

    Note: This cascades to delete surface_points, orientations, and structural_groups.
    """
    try:
        model = await GeologicalModel.get(model_id)
        await model.delete()
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found",
        )


@router.get("/by-dsl/{dsl_document_id}", response_model=ModelListResponse)
async def get_models_by_dsl(dsl_document_id: int):
    """Get all models built from a specific DSL document."""
    models = await GeologicalModel.find(
        {"dsl_document_id": dsl_document_id},
        order_by="created_at DESC",
    )
    return ModelListResponse(
        models=[GeologicalModelResponse.model_validate(m) for m in models],
        total=len(models),
    )
