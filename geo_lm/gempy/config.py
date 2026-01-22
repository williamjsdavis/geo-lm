"""Pydantic models for GemPy configuration and data.

This module defines the intermediate data representations used between
DSL parsing and GemPy model creation.
"""

from enum import Enum
from typing import Literal, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator


class GemPyRelationType(str, Enum):
    """Maps to gp.data.StackRelationType."""

    ERODE = "ERODE"
    ONLAP = "ONLAP"
    BASEMENT = "BASEMENT"


class SurfaceConfig(BaseModel):
    """Configuration for a geological surface.

    A surface corresponds to a DEPOSITION or INTRUSION event in the DSL.
    """

    surface_id: str = Field(description="From DSL event ID")
    name: str = Field(description="Rock name from ROCK definition")
    rock_id: str = Field(description="Reference to ROCK definition ID")
    rock_type: Literal["sedimentary", "volcanic", "intrusive", "metamorphic"]
    age_ma: float | None = Field(
        default=None, description="Age normalized to millions of years"
    )


class StructuralGroupConfig(BaseModel):
    """Configuration for a structural group (GemPy stack).

    Groups organize surfaces by their depositional relationship.
    """

    group_index: int = Field(ge=0, description="Position in stack (0 = youngest)")
    group_name: str
    surfaces: list[str] = Field(
        min_length=1, description="Surface IDs in this group"
    )
    relation: GemPyRelationType = GemPyRelationType.ERODE


class ModelExtent(BaseModel):
    """Model spatial extent in world coordinates."""

    x_min: float = Field(default=-500.0)
    x_max: float = Field(default=500.0)
    y_min: float = Field(default=-500.0)
    y_max: float = Field(default=500.0)
    z_min: float = Field(default=-1000.0, description="Deepest point (most negative)")
    z_max: float = Field(default=0.0, description="Surface level")

    @model_validator(mode="after")
    def validate_min_max(self) -> "ModelExtent":
        """Ensure min < max for all dimensions."""
        if self.x_min >= self.x_max:
            raise ValueError(f"x_min ({self.x_min}) must be less than x_max ({self.x_max})")
        if self.y_min >= self.y_max:
            raise ValueError(f"y_min ({self.y_min}) must be less than y_max ({self.y_max})")
        if self.z_min >= self.z_max:
            raise ValueError(f"z_min ({self.z_min}) must be less than z_max ({self.z_max})")
        return self


class ModelResolution(BaseModel):
    """Model grid resolution settings."""

    nx: int = Field(default=50, ge=10, le=200, description="X grid cells")
    ny: int = Field(default=50, ge=10, le=200, description="Y grid cells")
    nz: int = Field(default=50, ge=10, le=200, description="Z grid cells")
    refinement: int = Field(
        default=6, ge=1, le=10, description="Octree refinement levels"
    )


class GemPyModelConfig(BaseModel):
    """Complete configuration for a GemPy model (before spatial data).

    This is the intermediate representation between DSL and GemPy,
    containing structural information but not yet spatial coordinates.
    """

    name: str
    document_id: int | None = None
    dsl_document_id: int | None = None

    surfaces: list[SurfaceConfig]
    structural_groups: list[StructuralGroupConfig]

    extent: ModelExtent = Field(default_factory=ModelExtent)
    resolution: ModelResolution = Field(default_factory=ModelResolution)

    event_order: list[str] = Field(
        default_factory=list, description="Topologically sorted event IDs (youngest first)"
    )

    @field_validator("surfaces")
    @classmethod
    def validate_min_surfaces(cls, v: list[SurfaceConfig]) -> list[SurfaceConfig]:
        """GemPy requires at least 2 surfaces."""
        if len(v) < 2:
            raise ValueError(
                f"GemPy requires at least 2 surfaces for interpolation, got {len(v)}"
            )
        return v


class SurfacePoint(BaseModel):
    """A surface point with coordinates.

    Surface points define the 3D location of geological interfaces.
    """

    x: float
    y: float
    z: float
    surface: str = Field(description="Surface ID this point belongs to")
    series: str | None = Field(default=None, description="Optional series/group name")


class Orientation(BaseModel):
    """An orientation measurement.

    Orientations define the dip and azimuth of surfaces.
    """

    x: float
    y: float
    z: float
    azimuth: float = Field(ge=0, lt=360, description="Dip direction in degrees")
    dip: float = Field(ge=0, le=90, description="Dip angle in degrees")
    polarity: float = Field(default=1.0, description="Normal polarity indicator")
    surface: str = Field(description="Surface ID this orientation belongs to")
    series: str | None = Field(default=None, description="Optional series/group name")


class GemPyModelData(BaseModel):
    """Complete data for GemPy model creation.

    This extends GemPyModelConfig with spatial data (points and orientations).
    """

    config: GemPyModelConfig
    surface_points: list[SurfacePoint]
    orientations: list[Orientation]

    @model_validator(mode="after")
    def validate_data_requirements(self) -> "GemPyModelData":
        """Validate GemPy minimum data requirements."""
        # Check minimum points per surface
        surface_point_counts: dict[str, int] = {}
        for pt in self.surface_points:
            surface_point_counts[pt.surface] = surface_point_counts.get(pt.surface, 0) + 1

        for surface in self.config.surfaces:
            count = surface_point_counts.get(surface.surface_id, 0)
            if count < 2:
                raise ValueError(
                    f"Surface '{surface.surface_id}' has {count} points "
                    f"(GemPy requires minimum 2)"
                )

        # Check minimum orientations per structural group
        orientation_surfaces = {o.surface for o in self.orientations}
        for group in self.config.structural_groups:
            has_orientation = any(s in orientation_surfaces for s in group.surfaces)
            if not has_orientation:
                raise ValueError(
                    f"Structural group '{group.group_name}' has no orientations "
                    f"(GemPy requires minimum 1 per group)"
                )

        return self
