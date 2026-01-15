"""
Lark-based parser for the Geology DSL.

Usage:
    parser = GeologyDSLParser()
    program = parser.parse(dsl_text)
"""

from pathlib import Path
from typing import Optional

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError, UnexpectedInput

from .ast import (
    Program,
    RockDefinition,
    DepositionEvent,
    ErosionEvent,
    IntrusionEvent,
    RockType,
    IntrusionStyle,
    TimeUnit,
    AbsoluteTime,
    EpochTime,
    UnknownTime,
    SourceLocation,
)
from .errors import DSLParseError, DSLSyntaxError


# Path to grammar file (relative to this module)
GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


class ASTTransformer(Transformer):
    """
    Transforms Lark parse tree into AST nodes.

    Each method corresponds to a grammar rule and builds the appropriate AST node.
    """

    def _get_location(self, meta) -> Optional[SourceLocation]:
        """Extract source location from Lark meta information."""
        if hasattr(meta, "line"):
            return SourceLocation(
                line=meta.line,
                column=meta.column,
                end_line=getattr(meta, "end_line", None),
                end_column=getattr(meta, "end_column", None),
            )
        return None

    # --- Top-level ---

    def start(self, items):
        """Build Program from all statements."""
        rocks = []
        depositions = []
        erosions = []
        intrusions = []

        for item in items:
            if item is None:
                continue
            if isinstance(item, RockDefinition):
                rocks.append(item)
            elif isinstance(item, DepositionEvent):
                depositions.append(item)
            elif isinstance(item, ErosionEvent):
                erosions.append(item)
            elif isinstance(item, IntrusionEvent):
                intrusions.append(item)

        return Program(
            rocks=rocks,
            depositions=depositions,
            erosions=erosions,
            intrusions=intrusions,
        )

    def statement(self, items):
        """Pass through statement."""
        return items[0] if items else None

    # --- Rock Statement ---

    @v_args(meta=True)
    def rock_stmt(self, meta, items):
        id_token = str(items[0])
        props_dict = items[1] if len(items) > 1 else {}
        return RockDefinition(
            id=id_token,
            name=props_dict.get("name", ""),
            rock_type=props_dict.get("type", RockType.SEDIMENTARY),
            age=props_dict.get("age"),
            location=self._get_location(meta),
        )

    def rock_body(self, items):
        """Collect rock properties into a dict."""
        result = {}
        for item in items:
            if item and isinstance(item, tuple):
                key, value = item
                result[key] = value
        return result

    def name_prop(self, items):
        # Remove quotes from string if present
        name = str(items[0])
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        return ("name", name.strip())

    def type_prop(self, items):
        type_str = str(items[0]).upper()
        return ("type", RockType[type_str])

    def age_prop(self, items):
        return ("age", items[0])

    # --- Event Statements ---

    @v_args(meta=True)
    def deposition_stmt(self, meta, items):
        id_token = str(items[0])
        props_dict = items[1] if len(items) > 1 else {}
        return DepositionEvent(
            id=id_token,
            rock_id=props_dict.get("rock", ""),
            time=props_dict.get("time"),
            after=props_dict.get("after", []),
            location=self._get_location(meta),
        )

    @v_args(meta=True)
    def erosion_stmt(self, meta, items):
        id_token = str(items[0])
        props_dict = items[1] if len(items) > 1 else {}
        return ErosionEvent(
            id=id_token,
            time=props_dict.get("time"),
            after=props_dict.get("after", []),
            location=self._get_location(meta),
        )

    @v_args(meta=True)
    def intrusion_stmt(self, meta, items):
        id_token = str(items[0])
        props_dict = items[1] if len(items) > 1 else {}
        return IntrusionEvent(
            id=id_token,
            rock_id=props_dict.get("rock", ""),
            style=props_dict.get("style"),
            time=props_dict.get("time"),
            after=props_dict.get("after", []),
            location=self._get_location(meta),
        )

    def event_body(self, items):
        result = {}
        for item in items:
            if item and isinstance(item, tuple):
                key, value = item
                result[key] = value
        return result

    def erosion_body(self, items):
        return self.event_body(items)

    def intrusion_body(self, items):
        return self.event_body(items)

    def rock_ref_prop(self, items):
        return ("rock", str(items[0]))

    def time_prop(self, items):
        return ("time", items[0])

    def after_prop(self, items):
        return ("after", items[0])

    def style_prop(self, items):
        style_str = str(items[0]).upper()
        return ("style", IntrusionStyle[style_str])

    # --- Time Values ---

    def absolute_age(self, items):
        value = float(items[0])
        unit_str = str(items[1]).upper()
        return AbsoluteTime(value=value, unit=TimeUnit[unit_str])

    def absolute_time(self, items):
        value = float(items[0])
        unit_str = str(items[1]).upper()
        return AbsoluteTime(value=value, unit=TimeUnit[unit_str])

    def epoch_age(self, items):
        return EpochTime(epoch_name=str(items[0]).strip())

    def epoch_time(self, items):
        return EpochTime(epoch_name=str(items[0]).strip())

    def unknown_age(self, items):
        return UnknownTime()

    def unknown_time(self, items):
        return UnknownTime()

    # --- ID List ---

    def id_list(self, items):
        return [str(item) for item in items]


class GeologyDSLParser:
    """
    Main parser class for the Geology DSL.

    Example:
        parser = GeologyDSLParser()
        try:
            program = parser.parse(dsl_text)
        except DSLParseError as e:
            print(f"Parse error: {e}")
    """

    def __init__(self, grammar_path: Optional[Path] = None):
        """
        Initialize parser with grammar.

        Args:
            grammar_path: Optional path to grammar file. Uses default if not provided.
        """
        grammar_file = grammar_path or GRAMMAR_PATH
        with open(grammar_file, "r") as f:
            grammar_text = f.read()

        self._lark = Lark(
            grammar_text,
            start="start",
            parser="earley",  # Earley for better error messages
            propagate_positions=True,  # Enable source location tracking
            maybe_placeholders=False,
        )
        self._transformer = ASTTransformer()

    def parse(self, text: str) -> Program:
        """
        Parse DSL text into an AST Program.

        Args:
            text: The DSL source text to parse.

        Returns:
            A Program AST node containing all parsed statements.

        Raises:
            DSLSyntaxError: If the text contains syntax errors.
            DSLParseError: For other parsing errors.
        """
        try:
            tree = self._lark.parse(text)
            return self._transformer.transform(tree)
        except UnexpectedInput as e:
            raise DSLSyntaxError.from_lark_error(e, text)
        except LarkError as e:
            raise DSLParseError(str(e))

    def parse_file(self, filepath: Path) -> Program:
        """Parse a DSL file."""
        with open(filepath, "r") as f:
            return self.parse(f.read())
