"""
Error types for the Geology DSL parser and validator.

Provides detailed, user-friendly error messages with source locations.
"""

from dataclasses import dataclass
from typing import Optional, Sequence

from .ast import SourceLocation


class DSLError(Exception):
    """Base class for all DSL errors."""

    def __init__(self, message: str, location: Optional[SourceLocation] = None):
        self.location = location
        super().__init__(message)

    def __str__(self):
        if self.location:
            return f"{self.location}: {self.args[0]}"
        return self.args[0]


class DSLParseError(DSLError):
    """General parsing error."""

    pass


@dataclass
class DSLSyntaxError(DSLError):
    """Syntax error with detailed context."""

    message: str
    line: int
    column: int
    context_line: str = ""
    expected: Sequence[str] = ()

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        context_line: str = "",
        expected: Sequence[str] = (),
    ):
        self.message = message
        self.line = line
        self.column = column
        self.context_line = context_line
        self.expected = expected
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [
            f"Syntax error at line {self.line}, column {self.column}: {self.message}"
        ]

        if self.context_line:
            lines.append(f"  {self.context_line}")
            lines.append("  " + " " * (self.column - 1) + "^")

        if self.expected:
            expected_str = ", ".join(sorted(self.expected)[:5])
            if len(self.expected) > 5:
                expected_str += f", ... ({len(self.expected)} options)"
            lines.append(f"  Expected: {expected_str}")

        return "\n".join(lines)

    @classmethod
    def from_lark_error(cls, error, source: str) -> "DSLSyntaxError":
        """Create from a Lark parsing error."""
        from lark.exceptions import UnexpectedToken, UnexpectedCharacters

        lines = source.splitlines()
        context_line = lines[error.line - 1] if error.line <= len(lines) else ""

        expected = []
        if isinstance(error, UnexpectedToken):
            expected = list(error.expected) if error.expected else []
            message = f"Unexpected token '{error.token}'"
        elif isinstance(error, UnexpectedCharacters):
            message = f"Unexpected character '{error.char}'"
        else:
            message = str(error)

        return cls(
            message=message,
            line=error.line,
            column=error.column,
            context_line=context_line,
            expected=expected,
        )


class DSLValidationError(DSLError):
    """Base class for semantic validation errors."""

    pass


class UndefinedReferenceError(DSLValidationError):
    """Reference to an undefined ID."""

    def __init__(
        self,
        reference_type: str,
        reference_id: str,
        context: str,
        location: Optional[SourceLocation] = None,
        available_ids: Sequence[str] = (),
    ):
        self.reference_type = reference_type
        self.reference_id = reference_id
        self.context = context
        self.available_ids = available_ids
        msg = self._format_message()
        super().__init__(msg, location)

    def _format_message(self) -> str:
        msg = f"Undefined {self.reference_type} '{self.reference_id}' in {self.context}"
        if self.available_ids:
            suggestions = self._find_suggestions()
            if suggestions:
                msg += f". Did you mean: {', '.join(suggestions)}?"
            else:
                available = ", ".join(list(self.available_ids)[:5])
                msg += f". Available {self.reference_type}s: {available}"
        return msg

    def _find_suggestions(self) -> list[str]:
        """Find similar IDs using edit distance."""

        def edit_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return edit_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            prev_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            return prev_row[-1]

        scored = [
            (edit_distance(self.reference_id, aid), aid) for aid in self.available_ids
        ]
        scored.sort()
        return [aid for dist, aid in scored[:3] if dist <= 2]


class DuplicateIDError(DSLValidationError):
    """Duplicate ID definition."""

    def __init__(
        self,
        id: str,
        first_location: Optional[SourceLocation] = None,
        second_location: Optional[SourceLocation] = None,
    ):
        self.id = id
        self.first_location = first_location
        self.second_location = second_location
        msg = f"Duplicate ID '{id}'"
        if first_location:
            msg += f" (first defined at {first_location})"
        super().__init__(msg, second_location)


class CircularDependencyError(DSLValidationError):
    """Circular dependency in `after:` chain."""

    def __init__(
        self, cycle_path: Sequence[str], location: Optional[SourceLocation] = None
    ):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join(cycle_path)
        super().__init__(f"Circular dependency detected: {cycle_str}", location)


class MissingRequiredPropertyError(DSLValidationError):
    """Required property is missing."""

    def __init__(
        self,
        node_type: str,
        node_id: str,
        property_name: str,
        location: Optional[SourceLocation] = None,
    ):
        self.node_type = node_type
        self.node_id = node_id
        self.property_name = property_name
        super().__init__(
            f"{node_type} '{node_id}' is missing required property '{property_name}'",
            location,
        )


class TemporalInconsistencyError(DSLValidationError):
    """Absolute times inconsistent with ordering."""

    def __init__(
        self,
        event_id: str,
        event_time: str,
        dependency_id: str,
        dependency_time: str,
        location: Optional[SourceLocation] = None,
    ):
        self.event_id = event_id
        self.event_time = event_time
        self.dependency_id = dependency_id
        self.dependency_time = dependency_time
        super().__init__(
            f"Temporal inconsistency: {event_id} ({event_time}) claims to be after "
            f"{dependency_id} ({dependency_time}), but {event_time} is older",
            location,
        )
