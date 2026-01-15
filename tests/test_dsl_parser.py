"""Tests for DSL parser."""

import pytest

from geo_lm.parsers.dsl import parse
from geo_lm.parsers.dsl.ast import (
    Program,
    RockDefinition,
    DepositionEvent,
    ErosionEvent,
    IntrusionEvent,
    RockType,
    IntrusionStyle,
    TimeUnit,
)
from geo_lm.parsers.dsl.errors import DSLSyntaxError


class TestDSLParser:
    """Test DSL parsing functionality."""

    def test_parse_rock_definition(self):
        """Test parsing a rock definition."""
        dsl = 'ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]'
        program = parse(dsl)

        assert len(program.rocks) == 1
        rock = program.rocks[0]
        assert rock.id == "R1"
        assert rock.name == "Sandstone"
        assert rock.rock_type == RockType.SEDIMENTARY
        assert rock.age is not None
        assert rock.age.value == 100
        assert rock.age.unit == TimeUnit.MA

    def test_parse_rock_types(self):
        """Test parsing different rock types."""
        rock_types = [
            ("sedimentary", RockType.SEDIMENTARY),
            ("volcanic", RockType.VOLCANIC),
            ("intrusive", RockType.INTRUSIVE),
            ("metamorphic", RockType.METAMORPHIC),
        ]

        for type_str, expected_type in rock_types:
            dsl = f'ROCK R1 [ name: "Test"; type: {type_str} ]'
            program = parse(dsl)
            assert program.rocks[0].rock_type == expected_type

    def test_parse_age_units(self):
        """Test parsing different age units."""
        age_units = [
            ("100Ma", 100, TimeUnit.MA),
            ("500ka", 500, TimeUnit.KA),
            ("2Ga", 2, TimeUnit.GA),
        ]

        for age_str, value, unit in age_units:
            dsl = f'ROCK R1 [ name: "Test"; type: sedimentary; age: {age_str} ]'
            program = parse(dsl)
            assert program.rocks[0].age.value == value
            assert program.rocks[0].age.unit == unit

    def test_parse_unknown_age(self):
        """Test parsing unknown age marker."""
        dsl = 'ROCK R1 [ name: "Test"; type: sedimentary; age: "?" ]'
        program = parse(dsl)
        assert program.rocks[0].age is not None
        assert program.rocks[0].age.is_unknown

    def test_parse_deposition(self):
        """Test parsing a deposition event."""
        dsl = '''
        ROCK R1 [ name: "Test"; type: sedimentary ]
        DEPOSITION D1 [ rock: R1; time: 100Ma ]
        '''
        program = parse(dsl)

        assert len(program.depositions) == 1
        dep = program.depositions[0]
        assert dep.id == "D1"
        assert dep.rock_id == "R1"
        assert dep.time.value == 100

    def test_parse_deposition_with_after(self):
        """Test parsing deposition with after clause."""
        dsl = '''
        ROCK R1 [ name: "Test"; type: sedimentary ]
        DEPOSITION D1 [ rock: R1 ]
        DEPOSITION D2 [ rock: R1; after: D1 ]
        '''
        program = parse(dsl)

        assert len(program.depositions) == 2
        assert program.depositions[1].after == ["D1"]

    def test_parse_erosion(self):
        """Test parsing an erosion event."""
        dsl = '''
        ROCK R1 [ name: "Test"; type: sedimentary ]
        DEPOSITION D1 [ rock: R1 ]
        EROSION E1 [ time: 50Ma; after: D1 ]
        '''
        program = parse(dsl)

        assert len(program.erosions) == 1
        erosion = program.erosions[0]
        assert erosion.id == "E1"
        assert erosion.time.value == 50
        assert erosion.after == ["D1"]

    def test_parse_intrusion(self):
        """Test parsing an intrusion event."""
        dsl = '''
        ROCK R1 [ name: "Granite"; type: intrusive ]
        INTRUSION I1 [ rock: R1; style: stock; time: 30Ma ]
        '''
        program = parse(dsl)

        assert len(program.intrusions) == 1
        intrusion = program.intrusions[0]
        assert intrusion.id == "I1"
        assert intrusion.rock_id == "R1"
        assert intrusion.style == IntrusionStyle.STOCK
        assert intrusion.time.value == 30

    def test_parse_intrusion_styles(self):
        """Test parsing different intrusion styles."""
        styles = [
            ("dike", IntrusionStyle.DIKE),
            ("sill", IntrusionStyle.SILL),
            ("stock", IntrusionStyle.STOCK),
            ("batholith", IntrusionStyle.BATHOLITH),
        ]

        for style_str, expected_style in styles:
            dsl = f'''
            ROCK R1 [ name: "Granite"; type: intrusive ]
            INTRUSION I1 [ rock: R1; style: {style_str} ]
            '''
            program = parse(dsl)
            assert program.intrusions[0].style == expected_style

    def test_parse_multiple_after(self):
        """Test parsing multiple after references."""
        dsl = '''
        ROCK R1 [ name: "Test"; type: sedimentary ]
        DEPOSITION D1 [ rock: R1 ]
        DEPOSITION D2 [ rock: R1 ]
        EROSION E1 [ after: D1, D2 ]
        '''
        program = parse(dsl)

        assert program.erosions[0].after == ["D1", "D2"]

    def test_parse_full_program(self, sample_dsl_valid):
        """Test parsing a complete DSL program."""
        program = parse(sample_dsl_valid)

        assert len(program.rocks) == 3
        assert len(program.depositions) == 2
        assert len(program.erosions) == 1
        assert len(program.intrusions) == 1

    def test_parse_comments(self):
        """Test that comments are handled."""
        dsl = '''
        # This is a comment
        ROCK R1 [ name: "Test"; type: sedimentary ]
        # Another comment
        '''
        program = parse(dsl)
        assert len(program.rocks) == 1

    def test_parse_syntax_error(self, sample_dsl_syntax_error):
        """Test that syntax errors raise appropriate exception."""
        with pytest.raises(DSLSyntaxError):
            parse(sample_dsl_syntax_error)

    def test_program_all_events(self, sample_dsl_valid):
        """Test Program.all_events property."""
        program = parse(sample_dsl_valid)

        events = program.all_events
        assert len(events) == 4  # 2 depositions + 1 erosion + 1 intrusion

    def test_program_all_ids(self, sample_dsl_valid):
        """Test Program.all_ids property."""
        program = parse(sample_dsl_valid)

        ids = program.all_ids
        expected = {"R1", "R2", "R3", "D1", "D2", "E1", "I1"}
        assert ids == expected
