"""
AST node definitions for the Geology DSL.

The hierarchy:
    ASTNode (abstract base)
    ├── Program (root, contains statements)
    ├── RockDefinition
    ├── Event (abstract base for events)
    │   ├── DepositionEvent
    │   ├── ErosionEvent
    │   └── IntrusionEvent
    └── TimeValue (abstract base)
        ├── AbsoluteTime
        ├── EpochTime
        └── UnknownTime
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .visitor import ASTVisitor


class RockType(Enum):
    """Types of rocks in the DSL."""

    SEDIMENTARY = auto()
    VOLCANIC = auto()
    INTRUSIVE = auto()
    METAMORPHIC = auto()


class IntrusionStyle(Enum):
    """Styles of igneous intrusions."""

    DIKE = auto()
    SILL = auto()
    STOCK = auto()
    BATHOLITH = auto()


class TimeUnit(Enum):
    """Geological time units."""

    GA = auto()  # Billion years
    MA = auto()  # Million years
    KA = auto()  # Thousand years


@dataclass(frozen=True)
class SourceLocation:
    """Tracks position in source text for error reporting."""

    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __str__(self) -> str:
        if self.end_line and self.end_line != self.line:
            return f"lines {self.line}-{self.end_line}"
        return f"line {self.line}, column {self.column}"


@dataclass(kw_only=True)
class ASTNode(ABC):
    """Abstract base class for all AST nodes."""

    location: Optional[SourceLocation] = field(default=None, compare=False)

    def accept(self, visitor: "ASTVisitor"):
        """Accept a visitor for traversal."""
        pass


# --- Time Value Nodes ---


@dataclass
class TimeValue(ASTNode, ABC):
    """Abstract base for time specifications."""

    pass


@dataclass(kw_only=True)
class AbsoluteTime(TimeValue):
    """An absolute geological time (e.g., 35Ma)."""

    value: float
    unit: TimeUnit

    def to_ma(self) -> float:
        """Convert to millions of years ago."""
        if self.unit == TimeUnit.GA:
            return self.value * 1000
        elif self.unit == TimeUnit.KA:
            return self.value / 1000
        return self.value

    def __str__(self) -> str:
        unit_str = self.unit.name.lower().capitalize()
        if self.value == int(self.value):
            return f"{int(self.value)}{unit_str}"
        return f"{self.value}{unit_str}"


@dataclass(kw_only=True)
class EpochTime(TimeValue):
    """A geological epoch reference (e.g., 'late Eocene')."""

    epoch_name: str

    def __str__(self) -> str:
        return self.epoch_name


@dataclass(kw_only=True)
class UnknownTime(TimeValue):
    """Unknown or unspecified time."""

    def __str__(self) -> str:
        return "?"


# --- Rock Definition ---


@dataclass(kw_only=True)
class RockDefinition(ASTNode):
    """A ROCK statement defining a rock unit."""

    id: str
    name: str
    rock_type: RockType
    age: Optional[TimeValue] = None


# --- Event Nodes ---


@dataclass(kw_only=True)
class Event(ASTNode, ABC):
    """Abstract base for geological events."""

    id: str
    time: Optional[TimeValue] = None
    after: Sequence[str] = field(default_factory=list)


@dataclass(kw_only=True)
class DepositionEvent(Event):
    """A DEPOSITION statement."""

    rock_id: str = ""


@dataclass(kw_only=True)
class ErosionEvent(Event):
    """An EROSION statement."""

    pass


@dataclass(kw_only=True)
class IntrusionEvent(Event):
    """An INTRUSION statement."""

    rock_id: str = ""
    style: Optional[IntrusionStyle] = None


# --- Program (Root Node) ---


@dataclass(kw_only=True)
class Program(ASTNode):
    """Root AST node containing all statements."""

    rocks: Sequence[RockDefinition] = field(default_factory=list)
    depositions: Sequence[DepositionEvent] = field(default_factory=list)
    erosions: Sequence[ErosionEvent] = field(default_factory=list)
    intrusions: Sequence[IntrusionEvent] = field(default_factory=list)

    @property
    def all_events(self) -> Sequence[Event]:
        """All events in definition order."""
        return [*self.depositions, *self.erosions, *self.intrusions]

    @property
    def all_ids(self) -> set[str]:
        """All defined IDs (rocks and events)."""
        ids = {r.id for r in self.rocks}
        ids.update(e.id for e in self.all_events)
        return ids

    @property
    def rock_ids(self) -> set[str]:
        """All rock IDs."""
        return {r.id for r in self.rocks}

    @property
    def event_ids(self) -> set[str]:
        """All event IDs."""
        return {e.id for e in self.all_events}
