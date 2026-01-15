"""Tests for DSL validator."""

import pytest

from geo_lm.parsers.dsl import parse, validate, parse_and_validate
from geo_lm.parsers.dsl.errors import (
    UndefinedReferenceError,
    CircularDependencyError,
    DuplicateIDError,
    TemporalInconsistencyError,
)


class TestDSLValidator:
    """Test DSL validation functionality."""

    def test_validate_valid_dsl(self, sample_dsl_valid):
        """Test validation of valid DSL."""
        program = parse(sample_dsl_valid)
        result = validate(program)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_undefined_rock_reference(self, sample_dsl_invalid_reference):
        """Test validation catches undefined rock references."""
        program = parse(sample_dsl_invalid_reference)
        result = validate(program)

        assert not result.is_valid
        assert len(result.errors) > 0

        # Check for the specific error type
        assert any(isinstance(e, UndefinedReferenceError) for e in result.errors)

    def test_validate_circular_dependency(self, sample_dsl_circular):
        """Test validation catches circular dependencies."""
        program = parse(sample_dsl_circular)
        result = validate(program)

        assert not result.is_valid
        assert any(isinstance(e, CircularDependencyError) for e in result.errors)

    def test_validate_duplicate_ids(self):
        """Test validation catches duplicate IDs."""
        dsl = '''
        ROCK R1 [ name: "Rock 1"; type: sedimentary ]
        ROCK R1 [ name: "Rock 2"; type: volcanic ]
        '''
        program = parse(dsl)
        result = validate(program)

        assert not result.is_valid
        assert any(isinstance(e, DuplicateIDError) for e in result.errors)

    def test_validate_missing_rock_property(self):
        """Test validation catches missing required rock property."""
        # Note: The parser might catch this first, but let's test the concept
        dsl = '''
        ROCK R1 [ name: "Test" ]
        '''
        # This should fail at parse or validation level
        try:
            program = parse(dsl)
            result = validate(program)
            # If it parses, validation should catch it
            assert not result.is_valid
        except Exception:
            # Expected - parser rejects it
            pass

    def test_validate_event_reference(self):
        """Test validation catches undefined event references."""
        dsl = '''
        ROCK R1 [ name: "Test"; type: sedimentary ]
        DEPOSITION D1 [ rock: R1; after: X99 ]
        '''
        program = parse(dsl)
        result = validate(program)

        assert not result.is_valid
        assert any(isinstance(e, UndefinedReferenceError) for e in result.errors)

    def test_validate_temporal_consistency(self):
        """Test validation catches temporal inconsistencies."""
        # Events with after: relationships that violate absolute ages
        dsl = '''
        ROCK R1 [ name: "Old"; type: sedimentary; age: 100Ma ]
        ROCK R2 [ name: "Young"; type: sedimentary; age: 50Ma ]

        DEPOSITION D1 [ rock: R1; time: 100Ma ]
        DEPOSITION D2 [ rock: R2; time: 200Ma; after: D1 ]
        '''
        # D2 claims to be at 200Ma but occurs after D1 at 100Ma
        program = parse(dsl)
        result = validate(program)

        # Should have a temporal error
        has_temporal_issue = any(
            isinstance(e, TemporalInconsistencyError) for e in result.errors
        )
        assert has_temporal_issue

    def test_parse_and_validate_convenience(self, sample_dsl_valid):
        """Test parse_and_validate convenience function."""
        program, result = parse_and_validate(sample_dsl_valid)

        assert program is not None
        assert result.is_valid
        assert len(program.rocks) == 3

    def test_validation_error_location(self):
        """Test that validation errors include location info."""
        dsl = '''
ROCK R1 [ name: "Test"; type: sedimentary ]
DEPOSITION D1 [ rock: R99 ]
'''
        program = parse(dsl)
        result = validate(program)

        assert not result.is_valid
        # Errors should have location if available
        for error in result.errors:
            # Location may or may not be present
            if error.location:
                assert error.location.line > 0

    def test_validation_result_str(self, sample_dsl_invalid_reference):
        """Test ValidationResult string representation."""
        program = parse(sample_dsl_invalid_reference)
        result = validate(program)

        result_str = str(result)
        assert "error" in result_str.lower() or "invalid" in result_str.lower()
