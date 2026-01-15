"""
Geology DSL Parser and Validator for geo-lm.

This module provides parsing, validation, and serialization of the
geology domain-specific language (DSL) used to describe geological
histories and events.

Quick Start:
    from geo_lm.parsers.dsl import parse, validate, serialize

    # Parse DSL text
    program = parse(dsl_text)

    # Validate
    result = validate(program)
    if not result.is_valid:
        for error in result.errors:
            print(error)

    # Serialize back to text
    output = serialize(program)
"""

from .ast import (
    Program,
    RockDefinition,
    DepositionEvent,
    ErosionEvent,
    IntrusionEvent,
    TimeValue,
    AbsoluteTime,
    EpochTime,
    UnknownTime,
    RockType,
    IntrusionStyle,
    TimeUnit,
    SourceLocation,
)
from .parser import GeologyDSLParser
from .validator import DSLValidator, ValidationResult
from .serializer import DSLSerializer
from .errors import (
    DSLError,
    DSLParseError,
    DSLSyntaxError,
    DSLValidationError,
)

# Module-level parser, validator, serializer instances
_parser = None
_validator = None
_serializer = None


def _get_parser() -> GeologyDSLParser:
    global _parser
    if _parser is None:
        _parser = GeologyDSLParser()
    return _parser


def _get_validator() -> DSLValidator:
    global _validator
    if _validator is None:
        _validator = DSLValidator()
    return _validator


def _get_serializer() -> DSLSerializer:
    global _serializer
    if _serializer is None:
        _serializer = DSLSerializer()
    return _serializer


def parse(text: str) -> Program:
    """Parse DSL text into an AST Program."""
    return _get_parser().parse(text)


def validate(program: Program) -> ValidationResult:
    """Validate a parsed program for semantic correctness."""
    return _get_validator().validate(program)


def serialize(program: Program) -> str:
    """Serialize a Program AST back to DSL text."""
    return _get_serializer().serialize(program)


def parse_and_validate(text: str) -> tuple[Program, ValidationResult]:
    """Parse and validate DSL text in one call."""
    program = parse(text)
    result = validate(program)
    return program, result


__all__ = [
    # Core functions
    "parse",
    "validate",
    "serialize",
    "parse_and_validate",
    # Classes
    "GeologyDSLParser",
    "DSLValidator",
    "ValidationResult",
    "DSLSerializer",
    # AST nodes
    "Program",
    "RockDefinition",
    "DepositionEvent",
    "ErosionEvent",
    "IntrusionEvent",
    "TimeValue",
    "AbsoluteTime",
    "EpochTime",
    "UnknownTime",
    "SourceLocation",
    # Enums
    "RockType",
    "IntrusionStyle",
    "TimeUnit",
    # Errors
    "DSLError",
    "DSLParseError",
    "DSLSyntaxError",
    "DSLValidationError",
]
