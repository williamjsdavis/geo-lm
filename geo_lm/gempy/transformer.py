"""Transform DSL AST to GemPy configuration.

This module converts validated DSL Program AST into GemPyModelConfig,
which captures structural relationships without spatial coordinates.
"""

from collections import defaultdict
from typing import Sequence

from geo_lm.parsers.dsl.ast import (
    Program,
    RockDefinition,
    Event,
    DepositionEvent,
    ErosionEvent,
    IntrusionEvent,
    AbsoluteTime,
    TimeValue,
)
from .config import (
    GemPyModelConfig,
    SurfaceConfig,
    StructuralGroupConfig,
    GemPyRelationType,
    ModelExtent,
    ModelResolution,
)
from .errors import TransformationError


class DSLToGemPyTransformer:
    """Transforms validated DSL AST to GemPy configuration.

    This transformer handles:
    - Extracting surfaces from DEPOSITION and INTRUSION events
    - Topological sorting of events based on dependencies and time
    - Grouping surfaces into structural groups with appropriate relations
    """

    def transform(
        self,
        program: Program,
        name: str,
        document_id: int | None = None,
        dsl_document_id: int | None = None,
        extent: ModelExtent | None = None,
        resolution: ModelResolution | None = None,
    ) -> GemPyModelConfig:
        """Transform DSL Program to GemPyModelConfig.

        Args:
            program: Validated DSL Program AST
            name: Model name
            document_id: Optional source document ID
            dsl_document_id: Optional DSL document ID
            extent: Optional model extent override
            resolution: Optional model resolution override

        Returns:
            GemPyModelConfig ready for spatial data generation

        Raises:
            TransformationError: If transformation fails
        """
        try:
            # Build lookup maps
            self._rocks_by_id = {r.id: r for r in program.rocks}
            self._events_by_id: dict[str, Event] = {}
            for event in program.all_events:
                self._events_by_id[event.id] = event

            # Extract surfaces from rock-producing events
            surfaces = self._extract_surfaces(program)

            if len(surfaces) < 2:
                raise TransformationError(
                    f"Need at least 2 surfaces for GemPy model, but DSL only "
                    f"defines {len(surfaces)} rock-producing events (DEPOSITION/INTRUSION)"
                )

            # Topologically sort events
            event_order = self._topological_sort(program)

            # Build structural groups from event sequence
            structural_groups = self._build_structural_groups(program, event_order)

            return GemPyModelConfig(
                name=name,
                document_id=document_id,
                dsl_document_id=dsl_document_id,
                surfaces=surfaces,
                structural_groups=structural_groups,
                extent=extent or ModelExtent(),
                resolution=resolution or ModelResolution(),
                event_order=event_order,
            )

        except TransformationError:
            raise
        except Exception as e:
            raise TransformationError(f"Failed to transform DSL to GemPy config: {e}")

    def _extract_surfaces(self, program: Program) -> list[SurfaceConfig]:
        """Extract surfaces from DEPOSITION and INTRUSION events.

        Only these events produce rock surfaces; EROSION removes material
        but doesn't create new surfaces.
        """
        surfaces = []

        # Process depositions
        for dep in program.depositions:
            rock = self._get_rock(dep.rock_id)
            age_ma = self._normalize_time_to_ma(dep.time or rock.age)

            surfaces.append(
                SurfaceConfig(
                    surface_id=dep.id,
                    name=rock.name,
                    rock_id=rock.id,
                    rock_type=rock.rock_type.name.lower(),
                    age_ma=age_ma,
                )
            )

        # Process intrusions
        for intr in program.intrusions:
            rock = self._get_rock(intr.rock_id)
            age_ma = self._normalize_time_to_ma(intr.time or rock.age)

            surfaces.append(
                SurfaceConfig(
                    surface_id=intr.id,
                    name=rock.name,
                    rock_id=rock.id,
                    rock_type=rock.rock_type.name.lower(),
                    age_ma=age_ma,
                )
            )

        return surfaces

    def _get_rock(self, rock_id: str) -> RockDefinition:
        """Get rock definition by ID."""
        rock = self._rocks_by_id.get(rock_id)
        if not rock:
            raise TransformationError(f"Rock '{rock_id}' not found in DSL")
        return rock

    def _normalize_time_to_ma(self, time: TimeValue | None) -> float | None:
        """Convert time value to millions of years (Ma).

        Returns None for epoch times and unknown times since they
        can't be numerically compared.
        """
        if time is None:
            return None
        if isinstance(time, AbsoluteTime):
            return time.to_ma()
        return None

    def _topological_sort(self, program: Program) -> list[str]:
        """Sort events topologically based on after: dependencies and time.

        Returns events in chronological order (oldest first), which will
        be reversed for GemPy (youngest first in structural groups).

        Uses Kahn's algorithm with time-based tie-breaking.
        """
        # Build adjacency list and in-degree count
        # Edge A -> B means A must come before B (A is older)
        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {}

        all_event_ids = list(program.event_ids)
        for event_id in all_event_ids:
            in_degree[event_id] = 0

        # Add edges from after: dependencies
        # If event B has after: [A], then A must come before B
        for event in program.all_events:
            for after_id in event.after:
                if after_id in program.event_ids:
                    graph[after_id].append(event.id)
                    in_degree[event.id] += 1

        # Collect events with no dependencies
        queue: list[tuple[float | None, str]] = []
        for event_id in all_event_ids:
            if in_degree[event_id] == 0:
                event = self._events_by_id[event_id]
                age = self._get_event_age(event)
                # Use negative age for max-heap behavior (oldest first)
                queue.append((-(age or 0), event_id))

        # Sort by age (oldest first when no dependencies)
        queue.sort(reverse=True)

        result = []
        while queue:
            # Pop oldest event (highest age = most negative stored value)
            _, event_id = queue.pop()
            result.append(event_id)

            # Update dependencies
            for neighbor in graph[event_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    event = self._events_by_id[neighbor]
                    age = self._get_event_age(event)
                    queue.append((-(age or 0), neighbor))
                    queue.sort(reverse=True)

        # Check for cycles (shouldn't happen if DSL validation passed)
        if len(result) != len(all_event_ids):
            raise TransformationError(
                "Circular dependency detected in event ordering"
            )

        return result

    def _get_event_age(self, event: Event) -> float | None:
        """Get age in Ma for an event, preferring event time over rock age."""
        if event.time:
            return self._normalize_time_to_ma(event.time)

        # For depositions/intrusions, fall back to rock age
        if isinstance(event, (DepositionEvent, IntrusionEvent)):
            rock = self._rocks_by_id.get(event.rock_id)
            if rock and rock.age:
                return self._normalize_time_to_ma(rock.age)

        return None

    def _build_structural_groups(
        self, program: Program, event_order: list[str]
    ) -> list[StructuralGroupConfig]:
        """Build structural groups from sorted events.

        Mapping rules:
        - Consecutive depositions → same group
        - EROSION event → creates group boundary (next group is ONLAP)
        - INTRUSION → its own group with ERODE relation
        - Oldest/bottom group → BASEMENT relation
        """
        groups: list[StructuralGroupConfig] = []
        current_group_surfaces: list[str] = []
        next_relation = GemPyRelationType.ERODE
        erosion_occurred = False

        # Process in chronological order (oldest first)
        for event_id in event_order:
            event = self._events_by_id[event_id]

            if isinstance(event, ErosionEvent):
                # Erosion creates unconformity - finalize current group
                if current_group_surfaces:
                    groups.append(
                        StructuralGroupConfig(
                            group_index=0,  # Will be renumbered later
                            group_name=self._generate_group_name(
                                len(groups), current_group_surfaces
                            ),
                            surfaces=current_group_surfaces.copy(),
                            relation=next_relation,
                        )
                    )
                    current_group_surfaces = []

                # Next group after erosion gets ONLAP relation
                next_relation = GemPyRelationType.ONLAP
                erosion_occurred = True

            elif isinstance(event, DepositionEvent):
                # Add to current group
                current_group_surfaces.append(event.id)
                # Reset relation after first surface in ONLAP group
                if next_relation == GemPyRelationType.ONLAP and len(current_group_surfaces) > 1:
                    pass  # Keep building the group

            elif isinstance(event, IntrusionEvent):
                # Intrusions get their own group with ERODE relation
                # First, finalize any pending deposition group
                if current_group_surfaces:
                    groups.append(
                        StructuralGroupConfig(
                            group_index=0,
                            group_name=self._generate_group_name(
                                len(groups), current_group_surfaces
                            ),
                            surfaces=current_group_surfaces.copy(),
                            relation=next_relation,
                        )
                    )
                    current_group_surfaces = []
                    next_relation = GemPyRelationType.ERODE

                # Create intrusion group
                groups.append(
                    StructuralGroupConfig(
                        group_index=0,
                        group_name=f"Intrusion_{event.rock_id}",
                        surfaces=[event.id],
                        relation=GemPyRelationType.ERODE,
                    )
                )

        # Finalize last group
        if current_group_surfaces:
            groups.append(
                StructuralGroupConfig(
                    group_index=0,
                    group_name=self._generate_group_name(
                        len(groups), current_group_surfaces
                    ),
                    surfaces=current_group_surfaces.copy(),
                    relation=next_relation,
                )
            )

        # Reverse order for GemPy (youngest first) and renumber
        groups = list(reversed(groups))
        for i, group in enumerate(groups):
            group.group_index = i

        # Set oldest group to BASEMENT
        if groups:
            groups[-1].relation = GemPyRelationType.BASEMENT

        return groups

    def _generate_group_name(self, index: int, surfaces: Sequence[str]) -> str:
        """Generate a descriptive group name."""
        if len(surfaces) == 1:
            # Use surface ID for single-surface groups
            return f"Group_{surfaces[0]}"
        else:
            # Use generic name for multi-surface groups
            return f"Strata_Group_{index}"
