"""GemPy model construction from validated data.

This module handles the actual creation of GemPy GeoModel objects
from validated GemPyModelData.
"""

import os
import tempfile
from typing import TYPE_CHECKING

from .config import GemPyModelData, GemPyRelationType
from .errors import GemPyBuildError

if TYPE_CHECKING:
    import gempy as gp


# Mapping from our relation enum to GemPy's
def _get_relation_map():
    """Lazy import to avoid loading GemPy at module level."""
    import gempy as gp

    return {
        GemPyRelationType.ERODE: gp.data.StackRelationType.ERODE,
        GemPyRelationType.ONLAP: gp.data.StackRelationType.ONLAP,
        GemPyRelationType.BASEMENT: gp.data.StackRelationType.BASEMENT,
    }


class GemPyModelBuilder:
    """Builds GemPy GeoModel from validated GemPyModelData.

    The builder:
    1. Creates temporary CSV files for GemPy's importer
    2. Initializes the GeoModel with extent and resolution
    3. Defines structural groups and relationships
    4. Cleans up temporary files
    """

    def build(self, data: GemPyModelData) -> "gp.data.GeoModel":
        """Build GemPy model from complete model data.

        Args:
            data: Validated GemPyModelData with points and orientations

        Returns:
            Configured GemPy GeoModel (not yet computed)

        Raises:
            GemPyBuildError: If model creation fails
        """
        import gempy as gp

        temp_points_path = None
        temp_orientations_path = None

        try:
            # Write data to temporary CSV files
            temp_points_path = self._write_points_csv(data)
            temp_orientations_path = self._write_orientations_csv(data)

            # Create the GeoModel
            geo_model = self._create_model(data, temp_points_path, temp_orientations_path)

            # Define structural groups
            self._define_structural_groups(geo_model, data)

            return geo_model

        except GemPyBuildError:
            raise
        except Exception as e:
            raise GemPyBuildError(
                f"Failed to build GemPy model: {e}",
                details={"model_name": data.config.name},
            )
        finally:
            # Clean up temporary files
            if temp_points_path and os.path.exists(temp_points_path):
                os.unlink(temp_points_path)
            if temp_orientations_path and os.path.exists(temp_orientations_path):
                os.unlink(temp_orientations_path)

    def _write_points_csv(self, data: GemPyModelData) -> str:
        """Write surface points to temporary CSV file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            # Write header
            f.write("X,Y,Z,surface\n")

            # Write points
            for pt in data.surface_points:
                f.write(f"{pt.x},{pt.y},{pt.z},{pt.surface}\n")

            return f.name

    def _write_orientations_csv(self, data: GemPyModelData) -> str:
        """Write orientations to temporary CSV file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            # Write header
            f.write("X,Y,Z,azimuth,dip,polarity,surface\n")

            # Write orientations
            for o in data.orientations:
                f.write(f"{o.x},{o.y},{o.z},{o.azimuth},{o.dip},{o.polarity},{o.surface}\n")

            return f.name

    def _create_model(
        self,
        data: GemPyModelData,
        points_path: str,
        orientations_path: str,
    ) -> "gp.data.GeoModel":
        """Create the initial GemPy GeoModel."""
        import gempy as gp

        extent = data.config.extent
        resolution = data.config.resolution

        geo_model = gp.create_geomodel(
            project_name=data.config.name,
            extent=[
                extent.x_min,
                extent.x_max,
                extent.y_min,
                extent.y_max,
                extent.z_min,
                extent.z_max,
            ],
            resolution=[resolution.nx, resolution.ny, resolution.nz],
            refinement=resolution.refinement,
            importer_helper=gp.data.ImporterHelper(
                path_to_orientations=orientations_path,
                path_to_surface_points=points_path,
            ),
        )

        return geo_model

    def _define_structural_groups(
        self, geo_model: "gp.data.GeoModel", data: GemPyModelData
    ) -> None:
        """Define structural groups from configuration."""
        import gempy as gp

        relation_map = _get_relation_map()

        for group_config in data.config.structural_groups:
            # Get element objects from the model
            elements = []
            missing = []

            for surface_id in group_config.surfaces:
                try:
                    element = geo_model.structural_frame.get_element_by_name(surface_id)
                    elements.append(element)
                except ValueError:
                    missing.append(surface_id)

            if missing:
                # Try to find close matches for better error message
                available = list(geo_model.structural_frame.structural_elements.keys())
                raise GemPyBuildError(
                    f"Surfaces not found in model: {missing}",
                    details={
                        "group": group_config.group_name,
                        "missing": missing,
                        "available": available,
                    },
                )

            if elements:
                gp.add_structural_group(
                    model=geo_model,
                    group_index=group_config.group_index,
                    structural_group_name=group_config.group_name,
                    elements=elements,
                    structural_relation=relation_map[group_config.relation],
                )

        # Remove default_formation group if it exists
        try:
            gp.remove_structural_group_by_name(
                model=geo_model, group_name="default_formation"
            )
        except ValueError:
            pass  # Group didn't exist, that's fine

    def compute(self, geo_model: "gp.data.GeoModel") -> "gp.data.GeoModel":
        """Compute the GemPy model interpolation.

        Args:
            geo_model: Configured GemPy GeoModel

        Returns:
            Computed GemPy GeoModel with solutions

        Raises:
            GemPyBuildError: If computation fails
        """
        import gempy as gp

        try:
            gp.compute_model(gempy_model=geo_model)
            return geo_model
        except Exception as e:
            raise GemPyBuildError(
                f"GemPy model computation failed: {e}",
                details={"model_name": geo_model.meta.name},
            )


def build_and_compute(data: GemPyModelData) -> "gp.data.GeoModel":
    """Convenience function to build and compute a model in one step.

    Args:
        data: Validated GemPyModelData

    Returns:
        Computed GemPy GeoModel
    """
    builder = GemPyModelBuilder()
    geo_model = builder.build(data)
    return builder.compute(geo_model)
