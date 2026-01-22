"""Pre-GemPy validation for configuration and data.

This module validates model configuration and spatial data BEFORE
attempting GemPy model creation, enabling early failure with clear errors.
"""

from dataclasses import dataclass, field

from .config import GemPyModelConfig, GemPyModelData


@dataclass
class ValidationResult:
    """Result of validation with errors and warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


class GemPyConfigValidator:
    """Validates GemPyModelConfig before spatial generation.

    These checks ensure the structural configuration is valid before
    attempting the more expensive spatial data generation.
    """

    def validate(self, config: GemPyModelConfig) -> ValidationResult:
        """Validate model configuration.

        Args:
            config: The model configuration to validate

        Returns:
            ValidationResult with any errors or warnings
        """
        result = ValidationResult()

        self._check_minimum_surfaces(config, result)
        self._check_group_coverage(config, result)
        self._check_group_relations(config, result)
        self._check_group_ordering(config, result)

        return result

    def _check_minimum_surfaces(
        self, config: GemPyModelConfig, result: ValidationResult
    ) -> None:
        """Check minimum surface count."""
        if len(config.surfaces) < 2:
            result.add_error(
                f"GemPy requires at least 2 surfaces for interpolation, "
                f"but only {len(config.surfaces)} defined"
            )

    def _check_group_coverage(
        self, config: GemPyModelConfig, result: ValidationResult
    ) -> None:
        """Ensure all surfaces are assigned to exactly one group."""
        all_surface_ids = {s.surface_id for s in config.surfaces}
        grouped_surfaces: set[str] = set()
        duplicate_surfaces: set[str] = set()

        for group in config.structural_groups:
            for surface_id in group.surfaces:
                if surface_id in grouped_surfaces:
                    duplicate_surfaces.add(surface_id)
                grouped_surfaces.add(surface_id)

        # Check for duplicates
        if duplicate_surfaces:
            result.add_error(
                f"Surfaces assigned to multiple groups: {sorted(duplicate_surfaces)}"
            )

        # Check for unassigned surfaces
        unassigned = all_surface_ids - grouped_surfaces
        if unassigned:
            result.add_error(
                f"Surfaces not assigned to any group: {sorted(unassigned)}"
            )

        # Check for unknown surfaces in groups
        unknown = grouped_surfaces - all_surface_ids
        if unknown:
            result.add_error(
                f"Unknown surfaces in structural groups: {sorted(unknown)}"
            )

    def _check_group_relations(
        self, config: GemPyModelConfig, result: ValidationResult
    ) -> None:
        """Check structural group relations are valid."""
        basement_count = sum(
            1 for g in config.structural_groups if g.relation.value == "BASEMENT"
        )

        if basement_count == 0 and config.structural_groups:
            result.add_warning(
                "No BASEMENT group defined; the oldest group should typically "
                "have BASEMENT relation"
            )
        elif basement_count > 1:
            result.add_error(
                f"Multiple BASEMENT groups defined ({basement_count}); "
                f"only one is allowed"
            )

    def _check_group_ordering(
        self, config: GemPyModelConfig, result: ValidationResult
    ) -> None:
        """Check group indices are sequential and valid."""
        if not config.structural_groups:
            return

        indices = [g.group_index for g in config.structural_groups]
        expected = list(range(len(config.structural_groups)))

        if sorted(indices) != expected:
            result.add_error(
                f"Group indices must be sequential starting from 0. "
                f"Got: {sorted(indices)}, expected: {expected}"
            )


class GemPyDataValidator:
    """Validates complete GemPyModelData before GemPy creation.

    These checks ensure the spatial data meets GemPy's minimum requirements.
    """

    def validate(self, data: GemPyModelData) -> ValidationResult:
        """Validate complete model data.

        Args:
            data: The model data to validate

        Returns:
            ValidationResult with any errors or warnings
        """
        result = ValidationResult()

        self._check_points_per_surface(data, result)
        self._check_orientations_per_group(data, result)
        self._check_points_within_extent(data, result)
        self._check_point_distribution(data, result)

        return result

    def _check_points_per_surface(
        self, data: GemPyModelData, result: ValidationResult
    ) -> None:
        """Check minimum points per surface (GemPy requires 2)."""
        surface_counts: dict[str, int] = {}
        for pt in data.surface_points:
            surface_counts[pt.surface] = surface_counts.get(pt.surface, 0) + 1

        for surface in data.config.surfaces:
            count = surface_counts.get(surface.surface_id, 0)
            if count < 2:
                result.add_error(
                    f"Surface '{surface.surface_id}' has {count} point(s); "
                    f"GemPy requires minimum 2"
                )
            elif count < 5:
                result.add_warning(
                    f"Surface '{surface.surface_id}' has only {count} points; "
                    f"consider adding more for better interpolation"
                )

    def _check_orientations_per_group(
        self, data: GemPyModelData, result: ValidationResult
    ) -> None:
        """Check minimum orientations per structural group (GemPy requires 1)."""
        orientation_surfaces = {o.surface for o in data.orientations}

        for group in data.config.structural_groups:
            has_orientation = any(s in orientation_surfaces for s in group.surfaces)
            if not has_orientation:
                result.add_error(
                    f"Structural group '{group.group_name}' has no orientations; "
                    f"GemPy requires minimum 1 per group"
                )

    def _check_points_within_extent(
        self, data: GemPyModelData, result: ValidationResult
    ) -> None:
        """Check all points are within model extent."""
        extent = data.config.extent
        out_of_bounds = []

        for pt in data.surface_points:
            if not (
                extent.x_min <= pt.x <= extent.x_max
                and extent.y_min <= pt.y <= extent.y_max
                and extent.z_min <= pt.z <= extent.z_max
            ):
                out_of_bounds.append(
                    f"({pt.x:.1f}, {pt.y:.1f}, {pt.z:.1f}) for '{pt.surface}'"
                )

        if out_of_bounds:
            # Show first few out-of-bounds points
            shown = out_of_bounds[:3]
            remaining = len(out_of_bounds) - 3
            msg = f"Points outside model extent: {', '.join(shown)}"
            if remaining > 0:
                msg += f" and {remaining} more"
            result.add_warning(msg)

    def _check_point_distribution(
        self, data: GemPyModelData, result: ValidationResult
    ) -> None:
        """Check point distribution for potential interpolation issues."""
        # Check for surfaces with all points at same location
        for surface in data.config.surfaces:
            surface_pts = [
                pt for pt in data.surface_points if pt.surface == surface.surface_id
            ]

            if len(surface_pts) < 2:
                continue  # Already flagged by _check_points_per_surface

            # Check for degenerate distribution (all same X or Y)
            xs = [pt.x for pt in surface_pts]
            ys = [pt.y for pt in surface_pts]

            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)

            if x_range < 1.0 and y_range < 1.0:
                result.add_warning(
                    f"Surface '{surface.surface_id}' has very clustered points "
                    f"(X range: {x_range:.1f}, Y range: {y_range:.1f}); "
                    f"this may cause interpolation issues"
                )
