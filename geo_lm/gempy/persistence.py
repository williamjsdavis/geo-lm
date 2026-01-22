"""Database persistence for GemPy model data.

This module handles saving and loading model data to/from the database,
enabling retry/refinement without regenerating all data.
"""

import json
from typing import Optional

from geo_lm.database.repository import (
    repo_create,
    repo_find,
    repo_get,
    repo_update,
    repo_count,
)
from .config import (
    GemPyModelConfig,
    GemPyModelData,
    SurfaceConfig,
    StructuralGroupConfig,
    SurfacePoint,
    Orientation,
    ModelExtent,
    ModelResolution,
    GemPyRelationType,
)


class GemPyPersistenceService:
    """Persists GemPy model data to database."""

    async def save_model_data(self, data: GemPyModelData) -> int:
        """Save complete model data to database.

        Creates records in:
        - geological_models (main record)
        - surface_points
        - orientations
        - structural_groups

        Args:
            data: Complete GemPyModelData to save

        Returns:
            The geological_models.id
        """
        config = data.config

        # Create main model record
        model_record = await repo_create(
            "geological_models",
            {
                "name": config.name,
                "document_id": config.document_id,
                "dsl_document_id": config.dsl_document_id,
                "status": "computed",
                "extent_json": json.dumps(config.extent.model_dump()),
                "resolution_json": json.dumps(config.resolution.model_dump()),
            },
        )
        model_id = model_record["id"]

        # Save surface points
        for pt in data.surface_points:
            await repo_create(
                "surface_points",
                {
                    "model_id": model_id,
                    "x": pt.x,
                    "y": pt.y,
                    "z": pt.z,
                    "surface": pt.surface,
                    "series": pt.series,
                },
            )

        # Save orientations
        for o in data.orientations:
            await repo_create(
                "orientations",
                {
                    "model_id": model_id,
                    "x": o.x,
                    "y": o.y,
                    "z": o.z,
                    "azimuth": o.azimuth,
                    "dip": o.dip,
                    "polarity": o.polarity,
                    "surface": o.surface,
                    "series": o.series,
                },
            )

        # Save structural groups
        for group in config.structural_groups:
            await repo_create(
                "structural_groups",
                {
                    "model_id": model_id,
                    "group_index": group.group_index,
                    "group_name": group.group_name,
                    "elements_json": json.dumps(list(group.surfaces)),
                    "relation": group.relation.value,
                },
            )

        return model_id

    async def update_model_status(self, model_id: int, status: str) -> None:
        """Update the status of a model.

        Args:
            model_id: The model ID
            status: New status (pending, generating, computed, failed)
        """
        await repo_update("geological_models", model_id, {"status": status})

    async def load_model_data(self, model_id: int) -> Optional[GemPyModelData]:
        """Load model data from database.

        Args:
            model_id: The model ID to load

        Returns:
            GemPyModelData or None if not found
        """
        # Get main model record
        model_record = await repo_get("geological_models", model_id)
        if not model_record:
            return None

        # Load surface points
        points_records = await repo_find(
            "surface_points", {"model_id": model_id}
        )
        surface_points = [
            SurfacePoint(
                x=r["x"],
                y=r["y"],
                z=r["z"],
                surface=r["surface"],
                series=r.get("series"),
            )
            for r in points_records
        ]

        # Load orientations
        orientation_records = await repo_find(
            "orientations", {"model_id": model_id}
        )
        orientations = [
            Orientation(
                x=r["x"],
                y=r["y"],
                z=r["z"],
                azimuth=r["azimuth"],
                dip=r["dip"],
                polarity=r.get("polarity", 1.0),
                surface=r["surface"],
                series=r.get("series"),
            )
            for r in orientation_records
        ]

        # Load structural groups
        group_records = await repo_find(
            "structural_groups", {"model_id": model_id}, order_by="group_index"
        )
        structural_groups = [
            StructuralGroupConfig(
                group_index=r["group_index"],
                group_name=r["group_name"],
                surfaces=json.loads(r["elements_json"]),
                relation=GemPyRelationType(r["relation"]),
            )
            for r in group_records
        ]

        # Parse extent and resolution
        extent_data = json.loads(model_record.get("extent_json", "{}"))
        resolution_data = json.loads(model_record.get("resolution_json", "{}"))

        # Reconstruct surfaces from structural groups
        # Note: This is a simplified reconstruction; full surface data
        # would require storing it separately or reconstructing from DSL
        unique_surfaces = set()
        for group in structural_groups:
            unique_surfaces.update(group.surfaces)

        surfaces = [
            SurfaceConfig(
                surface_id=surface_id,
                name=surface_id,  # Simplified; real name not stored
                rock_id=surface_id,
                rock_type="sedimentary",  # Default; not stored
                age_ma=None,
            )
            for surface_id in unique_surfaces
        ]

        config = GemPyModelConfig(
            name=model_record["name"],
            document_id=model_record.get("document_id"),
            dsl_document_id=model_record.get("dsl_document_id"),
            surfaces=surfaces,
            structural_groups=structural_groups,
            extent=ModelExtent(**extent_data) if extent_data else ModelExtent(),
            resolution=ModelResolution(**resolution_data) if resolution_data else ModelResolution(),
        )

        return GemPyModelData(
            config=config,
            surface_points=surface_points,
            orientations=orientations,
        )

    async def get_model_summary(self, model_id: int) -> Optional[dict]:
        """Get a summary of a model for API responses.

        Args:
            model_id: The model ID

        Returns:
            Summary dict or None if not found
        """
        model_record = await repo_get("geological_models", model_id)
        if not model_record:
            return None

        # Count related data
        points_count = await repo_count("surface_points", {"model_id": model_id})
        orientations_count = await repo_count("orientations", {"model_id": model_id})

        # Get structural groups
        groups = await repo_find("structural_groups", {"model_id": model_id})

        return {
            "id": model_id,
            "name": model_record["name"],
            "status": model_record["status"],
            "document_id": model_record.get("document_id"),
            "dsl_document_id": model_record.get("dsl_document_id"),
            "extent": json.loads(model_record.get("extent_json", "{}")),
            "resolution": json.loads(model_record.get("resolution_json", "{}")),
            "surface_points_count": points_count,
            "orientations_count": orientations_count,
            "structural_groups": [
                {
                    "group_name": g["group_name"],
                    "surfaces": json.loads(g["elements_json"]),
                    "relation": g["relation"],
                }
                for g in groups
            ],
            "created_at": model_record.get("created_at"),
            "updated_at": model_record.get("updated_at"),
        }
