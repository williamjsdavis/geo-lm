"""
Semantic validation for the Geology DSL.

Validates:
1. All referenced IDs are defined
2. No circular dependencies in `after:` chains
3. Rock references in events exist
4. Temporal ordering is acyclic
5. Required properties are present
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .ast import (
    Program,
    RockDefinition,
    DepositionEvent,
    IntrusionEvent,
    AbsoluteTime,
    ASTNode,
)
from .errors import (
    DSLValidationError,
    UndefinedReferenceError,
    CircularDependencyError,
    DuplicateIDError,
    MissingRequiredPropertyError,
    TemporalInconsistencyError,
)


@dataclass
class ValidationResult:
    """Result of validation containing errors and warnings."""

    errors: list[DSLValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, error: DSLValidationError):
        self.errors.append(error)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def raise_if_invalid(self):
        """Raise the first error if validation failed."""
        if self.errors:
            raise self.errors[0]


class DSLValidator:
    """
    Validates a parsed DSL Program for semantic correctness.

    Example:
        validator = DSLValidator()
        result = validator.validate(program)
        if not result.is_valid:
            for error in result.errors:
                print(error)
    """

    def validate(self, program: Program) -> ValidationResult:
        """
        Run all validation checks on the program.

        Args:
            program: The parsed Program AST to validate.

        Returns:
            ValidationResult containing any errors and warnings.
        """
        result = ValidationResult()

        # Run validation passes in order
        self._check_duplicate_ids(program, result)
        self._check_required_properties(program, result)
        self._check_rock_references(program, result)
        self._check_event_references(program, result)
        self._check_circular_dependencies(program, result)
        self._check_temporal_consistency(program, result)

        return result

    def _check_duplicate_ids(self, program: Program, result: ValidationResult):
        """Check for duplicate ID definitions."""
        seen_ids: dict[str, ASTNode] = {}

        # Check rocks
        for rock in program.rocks:
            if rock.id in seen_ids:
                result.add_error(
                    DuplicateIDError(
                        id=rock.id,
                        first_location=seen_ids[rock.id].location,
                        second_location=rock.location,
                    )
                )
            else:
                seen_ids[rock.id] = rock

        # Check events
        for event in program.all_events:
            if event.id in seen_ids:
                result.add_error(
                    DuplicateIDError(
                        id=event.id,
                        first_location=seen_ids[event.id].location,
                        second_location=event.location,
                    )
                )
            else:
                seen_ids[event.id] = event

    def _check_required_properties(self, program: Program, result: ValidationResult):
        """Check that required properties are present."""
        for rock in program.rocks:
            if not rock.name:
                result.add_error(
                    MissingRequiredPropertyError(
                        node_type="ROCK",
                        node_id=rock.id,
                        property_name="name",
                        location=rock.location,
                    )
                )

        for dep in program.depositions:
            if not dep.rock_id:
                result.add_error(
                    MissingRequiredPropertyError(
                        node_type="DEPOSITION",
                        node_id=dep.id,
                        property_name="rock",
                        location=dep.location,
                    )
                )

        for intr in program.intrusions:
            if not intr.rock_id:
                result.add_error(
                    MissingRequiredPropertyError(
                        node_type="INTRUSION",
                        node_id=intr.id,
                        property_name="rock",
                        location=intr.location,
                    )
                )

    def _check_rock_references(self, program: Program, result: ValidationResult):
        """Check that rock references in events point to defined rocks."""
        rock_ids = {r.id for r in program.rocks}

        for dep in program.depositions:
            if dep.rock_id and dep.rock_id not in rock_ids:
                result.add_error(
                    UndefinedReferenceError(
                        reference_type="rock",
                        reference_id=dep.rock_id,
                        context=f"DEPOSITION {dep.id}",
                        location=dep.location,
                        available_ids=sorted(rock_ids),
                    )
                )

        for intr in program.intrusions:
            if intr.rock_id and intr.rock_id not in rock_ids:
                result.add_error(
                    UndefinedReferenceError(
                        reference_type="rock",
                        reference_id=intr.rock_id,
                        context=f"INTRUSION {intr.id}",
                        location=intr.location,
                        available_ids=sorted(rock_ids),
                    )
                )

    def _check_event_references(self, program: Program, result: ValidationResult):
        """Check that `after:` references point to defined events."""
        event_ids = {e.id for e in program.all_events}

        for event in program.all_events:
            for ref_id in event.after:
                if ref_id not in event_ids:
                    event_type = event.__class__.__name__.replace("Event", "").upper()
                    result.add_error(
                        UndefinedReferenceError(
                            reference_type="event",
                            reference_id=ref_id,
                            context=f"after: clause in {event_type} {event.id}",
                            location=event.location,
                            available_ids=sorted(event_ids),
                        )
                    )

    def _check_circular_dependencies(
        self, program: Program, result: ValidationResult
    ):
        """Detect cycles in the `after:` dependency graph using DFS."""
        # Build adjacency list: event_id -> list of events it depends on
        graph: dict[str, list[str]] = defaultdict(list)
        for event in program.all_events:
            for dep_id in event.after:
                graph[event.id].append(dep_id)

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = defaultdict(int)
        path: list[str] = []

        def dfs(node: str) -> Optional[list[str]]:
            """Returns cycle path if found, None otherwise."""
            color[node] = GRAY
            path.append(node)

            for neighbor in graph[node]:
                if color[neighbor] == GRAY:
                    # Found cycle - extract it from path
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                elif color[neighbor] == WHITE:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle

            path.pop()
            color[node] = BLACK
            return None

        for event in program.all_events:
            if color[event.id] == WHITE:
                cycle = dfs(event.id)
                if cycle:
                    result.add_error(
                        CircularDependencyError(cycle_path=cycle, location=event.location)
                    )
                    return  # One cycle error is enough

    def _check_temporal_consistency(self, program: Program, result: ValidationResult):
        """
        Check that absolute times are consistent with `after:` ordering.

        If event A has `after: B` and both have absolute times,
        A's time must be <= B's time (more recent or equal).
        """
        # Build map of event_id -> event
        event_map = {e.id: e for e in program.all_events}

        for event in program.all_events:
            if not isinstance(event.time, AbsoluteTime):
                continue

            event_time_ma = event.time.to_ma()

            for dep_id in event.after:
                dep_event = event_map.get(dep_id)
                if not dep_event or not isinstance(dep_event.time, AbsoluteTime):
                    continue

                dep_time_ma = dep_event.time.to_ma()

                # Event must be same age or younger than its dependencies
                if event_time_ma > dep_time_ma:
                    result.add_error(
                        TemporalInconsistencyError(
                            event_id=event.id,
                            event_time=str(event.time),
                            dependency_id=dep_id,
                            dependency_time=str(dep_event.time),
                            location=event.location,
                        )
                    )
