"""Mesh export from GemPy models for 3D visualization.

This module extracts mesh data (vertices, faces) from computed GemPy models
and converts it to JSON-serializable format for frontend rendering.
"""

from typing import TYPE_CHECKING, Optional
import numpy as np

from pydantic import BaseModel, Field

from .config import GemPyModelData, ModelExtent
from .builder import GemPyModelBuilder
from .errors import GemPyBuildError

if TYPE_CHECKING:
    import gempy as gp


# Rock type to color mapping
ROCK_TYPE_COLORS = {
    "sedimentary": "#D2B48C",  # Tan
    "volcanic": "#2F4F4F",     # Dark slate gray
    "intrusive": "#808080",    # Gray
    "metamorphic": "#696969",  # Dim gray
}

# Fallback colors for surfaces (if rock type not available)
SURFACE_COLORS = [
    "#E6B422",  # Gold
    "#8B4513",  # Saddle brown
    "#2E8B57",  # Sea green
    "#4682B4",  # Steel blue
    "#9932CC",  # Dark orchid
    "#CD853F",  # Peru
    "#20B2AA",  # Light sea green
    "#DAA520",  # Goldenrod
    "#708090",  # Slate gray
    "#BC8F8F",  # Rosy brown
]


class SurfaceMesh(BaseModel):
    """Mesh data for a single geological surface."""

    name: str = Field(description="Surface name")
    surface_id: str = Field(description="Surface ID from DSL")
    color: str = Field(description="Hex color code")
    vertices: list[list[float]] = Field(description="[[x,y,z], ...] vertex coordinates")
    faces: list[list[int]] = Field(description="[[i,j,k], ...] triangle indices")


class ModelMeshData(BaseModel):
    """Complete mesh data for 3D visualization."""

    model_id: int
    name: str
    surfaces: list[SurfaceMesh]
    extent: ModelExtent


class MeshExporter:
    """Extracts mesh data from GemPy models.

    The exporter can operate in two modes:
    1. Full mesh mode: Computes GemPy model and extracts marching cubes meshes
    2. Point cloud mode: Uses surface points as fallback when mesh extraction fails
    """

    def __init__(self, use_point_cloud_fallback: bool = True):
        """Initialize the mesh exporter.

        Args:
            use_point_cloud_fallback: If True, return point cloud data when
                mesh extraction fails
        """
        self.use_point_cloud_fallback = use_point_cloud_fallback

    def export_from_data(
        self,
        model_id: int,
        data: GemPyModelData,
        compute_meshes: bool = True,
    ) -> ModelMeshData:
        """Export mesh data from GemPyModelData.

        Args:
            model_id: Database model ID
            data: Complete model data with points and orientations
            compute_meshes: If True, build and compute GemPy model for meshes

        Returns:
            ModelMeshData ready for JSON serialization
        """
        if compute_meshes:
            try:
                return self._export_computed_meshes(model_id, data)
            except Exception as e:
                if self.use_point_cloud_fallback:
                    # Fall back to point cloud
                    return self._export_point_cloud(model_id, data)
                raise GemPyBuildError(f"Mesh export failed: {e}")
        else:
            return self._export_point_cloud(model_id, data)

    def _export_computed_meshes(
        self,
        model_id: int,
        data: GemPyModelData,
    ) -> ModelMeshData:
        """Export meshes from a computed GemPy model."""
        import gempy as gp
        from gempy.modules.mesh_extranction import marching_cubes

        # Build and compute the model
        builder = GemPyModelBuilder()
        geo_model = builder.build(data)
        builder.compute(geo_model)

        # Extract meshes using marching cubes (if not already done)
        if geo_model.solutions.dc_meshes is None:
            marching_cubes.set_meshes_with_marching_cubes(geo_model)

        # Build surface ID to config mapping
        surface_config_map = {s.surface_id: s for s in data.config.surfaces}

        surfaces: list[SurfaceMesh] = []
        color_idx = 0

        # Iterate through structural groups to get meshes in order
        for group in geo_model.structural_frame.structural_groups:
            for element in group.elements:
                element_name = element.name

                # Get config for this surface
                config = surface_config_map.get(element_name)

                # Determine color
                if config and config.rock_type in ROCK_TYPE_COLORS:
                    color = ROCK_TYPE_COLORS[config.rock_type]
                else:
                    color = SURFACE_COLORS[color_idx % len(SURFACE_COLORS)]
                    color_idx += 1

                # Extract vertices and faces
                if element.vertices is not None and element.edges is not None:
                    # Apply inverse transform to get world coordinates
                    vertices_transformed = element.vertices
                    if hasattr(geo_model, 'input_transform') and geo_model.input_transform is not None:
                        vertices_world = geo_model.input_transform.apply_inverse(
                            vertices_transformed
                        )
                    else:
                        vertices_world = vertices_transformed

                    surfaces.append(
                        SurfaceMesh(
                            name=config.name if config else element_name,
                            surface_id=element_name,
                            color=color,
                            vertices=vertices_world.tolist(),
                            faces=element.edges.tolist(),
                        )
                    )

        return ModelMeshData(
            model_id=model_id,
            name=data.config.name,
            surfaces=surfaces,
            extent=data.config.extent,
        )

    def _export_point_cloud(
        self,
        model_id: int,
        data: GemPyModelData,
    ) -> ModelMeshData:
        """Export surface points as point cloud (fallback mode).

        Creates pseudo-meshes where each point becomes a small tetrahedron
        to be visible in the 3D viewer.
        """
        # Build surface ID to config mapping
        surface_config_map = {s.surface_id: s for s in data.config.surfaces}

        # Group points by surface
        points_by_surface: dict[str, list[tuple[float, float, float]]] = {}
        for pt in data.surface_points:
            if pt.surface not in points_by_surface:
                points_by_surface[pt.surface] = []
            points_by_surface[pt.surface].append((pt.x, pt.y, pt.z))

        surfaces: list[SurfaceMesh] = []
        color_idx = 0

        for surface_id, points in points_by_surface.items():
            config = surface_config_map.get(surface_id)

            # Determine color
            if config and config.rock_type in ROCK_TYPE_COLORS:
                color = ROCK_TYPE_COLORS[config.rock_type]
            else:
                color = SURFACE_COLORS[color_idx % len(SURFACE_COLORS)]
                color_idx += 1

            # Create small tetrahedra for each point
            vertices, faces = self._points_to_tetrahedra(points)

            surfaces.append(
                SurfaceMesh(
                    name=config.name if config else surface_id,
                    surface_id=surface_id,
                    color=color,
                    vertices=vertices,
                    faces=faces,
                )
            )

        return ModelMeshData(
            model_id=model_id,
            name=data.config.name,
            surfaces=surfaces,
            extent=data.config.extent,
        )

    def _points_to_tetrahedra(
        self,
        points: list[tuple[float, float, float]],
        size: float = 10.0,
    ) -> tuple[list[list[float]], list[list[int]]]:
        """Convert points to small tetrahedra for visualization.

        Creates a tetrahedron centered at each point to make points
        visible as small 3D shapes.

        Args:
            points: List of (x, y, z) coordinates
            size: Size of each tetrahedron

        Returns:
            (vertices, faces) for all tetrahedra
        """
        all_vertices: list[list[float]] = []
        all_faces: list[list[int]] = []

        # Tetrahedron template (centered at origin)
        # Regular tetrahedron with vertices at:
        s = size / 2
        tetra_template = np.array([
            [0, 0, s * 1.633],      # Top
            [s, 0, -s * 0.577],     # Front right
            [-s, 0, -s * 0.577],    # Front left
            [0, s, -s * 0.577],     # Back
        ])

        # Tetrahedron faces (4 triangular faces)
        face_template = [
            [0, 1, 2],  # Front face
            [0, 2, 3],  # Left face
            [0, 3, 1],  # Right face
            [1, 3, 2],  # Bottom face
        ]

        for i, (x, y, z) in enumerate(points):
            base_idx = i * 4  # 4 vertices per tetrahedron

            # Translate tetrahedron to point location
            vertices = tetra_template + np.array([x, y, z])
            all_vertices.extend(vertices.tolist())

            # Add faces with offset indices
            for face in face_template:
                all_faces.append([f + base_idx for f in face])

        return all_vertices, all_faces


def export_model_mesh(
    model_id: int,
    data: GemPyModelData,
    compute_meshes: bool = True,
) -> ModelMeshData:
    """Convenience function to export mesh data.

    Args:
        model_id: Database model ID
        data: Complete GemPyModelData
        compute_meshes: Whether to compute full meshes or use point cloud

    Returns:
        ModelMeshData ready for JSON serialization
    """
    exporter = MeshExporter()
    return exporter.export_from_data(model_id, data, compute_meshes)
