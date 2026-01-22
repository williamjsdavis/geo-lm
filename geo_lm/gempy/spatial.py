"""Rule-based spatial data generation for GemPy models.

This module generates synthetic surface points and orientations based on
geological rules, producing data that meets GemPy's minimum requirements.
"""

import math
import random
from typing import Sequence

from .config import (
    GemPyModelConfig,
    GemPyModelData,
    SurfaceConfig,
    SurfacePoint,
    Orientation,
    ModelExtent,
)
from .errors import SpatialGenerationError


class RuleBasedSpatialGenerator:
    """Generates synthetic spatial data based on geological rules.

    Generation rules:
    - Surfaces are placed at depths based on their stratigraphic position
    - Sedimentary rocks: low dip (0-10 degrees), horizontal layers
    - Volcanic rocks: moderate dip variability
    - Intrusive rocks: dip depends on style (dikes steep, sills flat)
    - Points are distributed across the X-Y extent with noise
    """

    def __init__(
        self,
        points_per_surface: int = 10,
        layer_thickness: float = 100.0,
        base_dip: float = 5.0,
        base_azimuth: float = 0.0,
        seed: int | None = None,
    ):
        """Initialize the spatial generator.

        Args:
            points_per_surface: Number of points to generate per surface
            layer_thickness: Vertical spacing between layers
            base_dip: Default dip angle in degrees
            base_azimuth: Default dip direction in degrees
            seed: Optional random seed for reproducibility
        """
        self.points_per_surface = points_per_surface
        self.layer_thickness = layer_thickness
        self.base_dip = base_dip
        self.base_azimuth = base_azimuth
        self.seed = seed

    def generate(self, config: GemPyModelConfig) -> GemPyModelData:
        """Generate spatial data for the model configuration.

        Args:
            config: Model configuration with surfaces and structural groups

        Returns:
            Complete GemPyModelData with points and orientations

        Raises:
            SpatialGenerationError: If generation fails
        """
        # Reset random seed if provided (for reproducibility)
        if self.seed is not None:
            random.seed(self.seed)

        try:
            # Sort surfaces by age (oldest first = deepest)
            sorted_surfaces = self._sort_surfaces_by_depth(config)

            # Generate points and orientations
            all_points: list[SurfacePoint] = []
            all_orientations: list[Orientation] = []

            for i, surface in enumerate(sorted_surfaces):
                # Calculate base Z for this surface
                z_base = self._calculate_z_base(i, len(sorted_surfaces), config.extent)

                # Get rock-type-specific parameters
                dip, azimuth = self._get_orientation_params(surface)

                # Generate surface points
                points = self._generate_surface_points(
                    surface, config.extent, z_base, dip, azimuth
                )
                all_points.extend(points)

                # Generate orientation for first surface in each group
                if self._should_generate_orientation(surface, config):
                    orientation = self._generate_orientation(
                        surface, config.extent, z_base, dip, azimuth
                    )
                    all_orientations.append(orientation)

            # Ensure we have at least one orientation per group
            self._ensure_group_orientations(
                config, all_points, all_orientations, sorted_surfaces
            )

            # Update extent to fit actual points with margin
            updated_extent = self._calculate_dynamic_extent(all_points, config.extent)
            config.extent = updated_extent

            return GemPyModelData(
                config=config,
                surface_points=all_points,
                orientations=all_orientations,
            )

        except Exception as e:
            raise SpatialGenerationError(f"Failed to generate spatial data: {e}")

    def _sort_surfaces_by_depth(
        self, config: GemPyModelConfig
    ) -> list[SurfaceConfig]:
        """Sort surfaces by stratigraphic position (oldest/deepest first).

        Uses event_order from config if available, otherwise falls back to age.
        """
        # Create lookup from event order (reversed because oldest is first in order)
        if config.event_order:
            order_lookup = {
                surface_id: i for i, surface_id in enumerate(config.event_order)
            }
            return sorted(
                config.surfaces,
                key=lambda s: order_lookup.get(s.surface_id, 0),
            )
        else:
            # Fall back to age-based sorting
            return sorted(
                config.surfaces,
                key=lambda s: s.age_ma if s.age_ma is not None else float("inf"),
                reverse=True,  # Oldest first
            )

    def _calculate_z_base(
        self, layer_index: int, total_layers: int, extent: ModelExtent
    ) -> float:
        """Calculate base Z depth for a layer.

        Distributes layers evenly within the Z extent, with oldest at bottom.
        """
        z_range = extent.z_max - extent.z_min
        # Leave margin at top and bottom (10% each)
        usable_range = z_range * 0.8
        margin = z_range * 0.1

        if total_layers == 1:
            # Single layer in the middle
            return extent.z_min + margin + usable_range / 2

        # Distribute layers evenly
        layer_spacing = usable_range / (total_layers - 1)
        return extent.z_min + margin + layer_index * layer_spacing

    def _get_orientation_params(
        self, surface: SurfaceConfig
    ) -> tuple[float, float]:
        """Get dip and azimuth based on rock type.

        Returns:
            Tuple of (dip_degrees, azimuth_degrees)
        """
        rock_type = surface.rock_type.lower()

        if rock_type == "sedimentary":
            # Sedimentary: generally flat with slight regional dip
            dip = self.base_dip + random.uniform(-2, 2)
            azimuth = self.base_azimuth + random.uniform(-10, 10)

        elif rock_type == "volcanic":
            # Volcanic: can have more variable orientations
            dip = self.base_dip + random.uniform(-5, 10)
            azimuth = self.base_azimuth + random.uniform(-30, 30)

        elif rock_type == "intrusive":
            # Intrusive: varies by style, but generally steeper
            dip = random.uniform(10, 45)
            azimuth = random.uniform(0, 360)

        elif rock_type == "metamorphic":
            # Metamorphic: often foliated, variable dips
            dip = random.uniform(20, 60)
            azimuth = self.base_azimuth + random.uniform(-45, 45)

        else:
            # Default to base parameters
            dip = self.base_dip
            azimuth = self.base_azimuth

        # Normalize values
        dip = max(0, min(90, dip))
        azimuth = azimuth % 360

        return dip, azimuth

    def _generate_surface_points(
        self,
        surface: SurfaceConfig,
        extent: ModelExtent,
        z_base: float,
        dip: float,
        azimuth: float,
    ) -> list[SurfacePoint]:
        """Generate points on a tilted planar surface with noise."""
        points = []

        x_range = extent.x_max - extent.x_min
        y_range = extent.y_max - extent.y_min
        x_center = (extent.x_max + extent.x_min) / 2
        y_center = (extent.y_max + extent.y_min) / 2

        # Convert dip/azimuth to radians for calculation
        dip_rad = math.radians(dip)
        azimuth_rad = math.radians(azimuth)

        for _ in range(self.points_per_surface):
            # Generate X, Y within inner 80% of extent
            x = extent.x_min + random.uniform(0.1, 0.9) * x_range
            y = extent.y_min + random.uniform(0.1, 0.9) * y_range

            # Calculate Z offset from dip
            dx = x - x_center
            dy = y - y_center

            # Project onto dip direction
            dip_distance = dx * math.cos(azimuth_rad) + dy * math.sin(azimuth_rad)
            z_offset = dip_distance * math.tan(dip_rad)

            # Add small noise
            z_noise = random.gauss(0, 5)

            z = z_base + z_offset + z_noise

            points.append(
                SurfacePoint(
                    x=round(x, 2),
                    y=round(y, 2),
                    z=round(z, 2),
                    surface=surface.surface_id,
                )
            )

        return points

    def _should_generate_orientation(
        self, surface: SurfaceConfig, config: GemPyModelConfig
    ) -> bool:
        """Check if this surface needs an orientation (first in its group)."""
        for group in config.structural_groups:
            if surface.surface_id in group.surfaces:
                return surface.surface_id == group.surfaces[0]
        return True  # Generate for ungrouped surfaces

    def _generate_orientation(
        self,
        surface: SurfaceConfig,
        extent: ModelExtent,
        z_base: float,
        dip: float,
        azimuth: float,
    ) -> Orientation:
        """Generate an orientation measurement at the surface center."""
        x_center = (extent.x_max + extent.x_min) / 2
        y_center = (extent.y_max + extent.y_min) / 2

        return Orientation(
            x=round(x_center, 2),
            y=round(y_center, 2),
            z=round(z_base, 2),
            azimuth=round(azimuth, 1),
            dip=round(dip, 1),
            polarity=1.0,
            surface=surface.surface_id,
        )

    def _ensure_group_orientations(
        self,
        config: GemPyModelConfig,
        points: list[SurfacePoint],
        orientations: list[Orientation],
        sorted_surfaces: Sequence[SurfaceConfig],
    ) -> None:
        """Ensure every structural group has at least one orientation."""
        orientation_surfaces = {o.surface for o in orientations}

        for group in config.structural_groups:
            has_orientation = any(s in orientation_surfaces for s in group.surfaces)

            if not has_orientation and group.surfaces:
                # Find the first surface in this group
                first_surface_id = group.surfaces[0]
                first_surface = next(
                    (s for s in config.surfaces if s.surface_id == first_surface_id),
                    None,
                )

                if first_surface:
                    # Find the z_base for this surface
                    surface_points = [p for p in points if p.surface == first_surface_id]
                    if surface_points:
                        avg_z = sum(p.z for p in surface_points) / len(surface_points)
                        dip, azimuth = self._get_orientation_params(first_surface)

                        orientations.append(
                            Orientation(
                                x=round((config.extent.x_max + config.extent.x_min) / 2, 2),
                                y=round((config.extent.y_max + config.extent.y_min) / 2, 2),
                                z=round(avg_z, 2),
                                azimuth=round(azimuth, 1),
                                dip=round(dip, 1),
                                polarity=1.0,
                                surface=first_surface_id,
                            )
                        )

    def _calculate_dynamic_extent(
        self, points: list[SurfacePoint], original_extent: ModelExtent
    ) -> ModelExtent:
        """Calculate extent from actual points with margin.

        Uses the larger of original extent or data extent + margin.
        """
        if not points:
            return original_extent

        xs = [p.x for p in points]
        ys = [p.y for p in points]
        zs = [p.z for p in points]

        # Data bounds
        data_x_min, data_x_max = min(xs), max(xs)
        data_y_min, data_y_max = min(ys), max(ys)
        data_z_min, data_z_max = min(zs), max(zs)

        # Add 10% margin
        x_margin = (data_x_max - data_x_min) * 0.1 or 50
        y_margin = (data_y_max - data_y_min) * 0.1 or 50
        z_margin = (data_z_max - data_z_min) * 0.1 or 50

        return ModelExtent(
            x_min=min(original_extent.x_min, data_x_min - x_margin),
            x_max=max(original_extent.x_max, data_x_max + x_margin),
            y_min=min(original_extent.y_min, data_y_min - y_margin),
            y_max=max(original_extent.y_max, data_y_max + y_margin),
            z_min=min(original_extent.z_min, data_z_min - z_margin),
            z_max=max(original_extent.z_max, data_z_max + z_margin),
        )
