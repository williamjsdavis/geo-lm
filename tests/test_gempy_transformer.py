"""Tests for GemPy transformer and spatial generator."""

import pytest

from geo_lm.parsers.dsl import parse_and_validate
from geo_lm.gempy.transformer import DSLToGemPyTransformer
from geo_lm.gempy.spatial import RuleBasedSpatialGenerator
from geo_lm.gempy.validator import GemPyConfigValidator, GemPyDataValidator
from geo_lm.gempy.config import GemPyRelationType


class TestDSLToGemPyTransformer:
    """Tests for DSL to GemPy transformation."""

    @pytest.fixture
    def simple_dsl(self) -> str:
        """Simple DSL with two depositions."""
        return """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
"""

    @pytest.fixture
    def erosion_dsl(self) -> str:
        """DSL with erosion creating unconformity."""
        return """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
ROCK R3 [ name: "Shale"; type: sedimentary ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
EROSION E1 [ after: D2 ]
DEPOSITION D3 [ rock: R3; after: E1 ]
"""

    @pytest.fixture
    def intrusion_dsl(self) -> str:
        """DSL with igneous intrusion."""
        return """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
ROCK R3 [ name: "Granite"; type: intrusive ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
INTRUSION I1 [ rock: R3; style: stock; after: D2 ]
"""

    def test_simple_transformation(self, simple_dsl: str):
        """Test basic DSL transformation."""
        program, result = parse_and_validate(simple_dsl)
        assert result.is_valid

        transformer = DSLToGemPyTransformer()
        config = transformer.transform(program, name="SimpleModel")

        assert config.name == "SimpleModel"
        assert len(config.surfaces) == 2
        assert len(config.structural_groups) == 1

        # Check surface IDs match event IDs
        surface_ids = {s.surface_id for s in config.surfaces}
        assert surface_ids == {"D1", "D2"}

        # Oldest group should be BASEMENT
        assert config.structural_groups[0].relation == GemPyRelationType.BASEMENT

    def test_erosion_creates_onlap(self, erosion_dsl: str):
        """Test that post-erosion deposition gets ONLAP relation."""
        program, result = parse_and_validate(erosion_dsl)
        assert result.is_valid

        transformer = DSLToGemPyTransformer()
        config = transformer.transform(program, name="ErosionModel")

        assert len(config.surfaces) == 3  # D1, D2, D3
        assert len(config.structural_groups) == 2

        # Find the ONLAP group
        onlap_groups = [
            g for g in config.structural_groups
            if g.relation == GemPyRelationType.ONLAP
        ]
        assert len(onlap_groups) == 1
        assert "D3" in onlap_groups[0].surfaces

    def test_intrusion_creates_erode_group(self, intrusion_dsl: str):
        """Test that intrusions get their own group with ERODE relation."""
        program, result = parse_and_validate(intrusion_dsl)
        assert result.is_valid

        transformer = DSLToGemPyTransformer()
        config = transformer.transform(program, name="IntrusionModel")

        assert len(config.surfaces) == 3  # D1, D2, I1

        # Find the intrusion group
        intrusion_groups = [
            g for g in config.structural_groups
            if "I1" in g.surfaces
        ]
        assert len(intrusion_groups) == 1
        assert intrusion_groups[0].relation == GemPyRelationType.ERODE

    def test_event_order(self, erosion_dsl: str):
        """Test that events are ordered chronologically."""
        program, result = parse_and_validate(erosion_dsl)
        assert result.is_valid

        transformer = DSLToGemPyTransformer()
        config = transformer.transform(program, name="OrderModel")

        # Events should be in chronological order (oldest first)
        assert config.event_order == ["D1", "D2", "E1", "D3"]

    def test_surface_rock_type_preserved(self, intrusion_dsl: str):
        """Test that rock type information is preserved."""
        program, result = parse_and_validate(intrusion_dsl)
        transformer = DSLToGemPyTransformer()
        config = transformer.transform(program, name="RockTypeModel")

        # Find surfaces by rock type
        sedimentary = [s for s in config.surfaces if s.rock_type == "sedimentary"]
        intrusive = [s for s in config.surfaces if s.rock_type == "intrusive"]

        assert len(sedimentary) == 2
        assert len(intrusive) == 1


class TestRuleBasedSpatialGenerator:
    """Tests for rule-based spatial data generation."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        dsl = """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
"""
        program, _ = parse_and_validate(dsl)
        transformer = DSLToGemPyTransformer()
        return transformer.transform(program, name="TestConfig")

    def test_generates_minimum_points(self, config):
        """Test that generator creates minimum required points per surface."""
        generator = RuleBasedSpatialGenerator(points_per_surface=5, seed=42)
        model_data = generator.generate(config)

        # Count points per surface
        points_per_surface = {}
        for pt in model_data.surface_points:
            points_per_surface[pt.surface] = points_per_surface.get(pt.surface, 0) + 1

        # Each surface should have at least 2 points (GemPy minimum)
        for count in points_per_surface.values():
            assert count >= 2

    def test_generates_orientations_per_group(self, config):
        """Test that each structural group gets at least one orientation."""
        generator = RuleBasedSpatialGenerator(seed=42)
        model_data = generator.generate(config)

        orientation_surfaces = {o.surface for o in model_data.orientations}

        # Each group should have at least one orientation
        for group in config.structural_groups:
            has_orientation = any(s in orientation_surfaces for s in group.surfaces)
            assert has_orientation, f"Group {group.group_name} missing orientation"

    def test_reproducible_with_seed(self):
        """Test that generation is reproducible with same seed."""
        # Create fresh configs for each run (since generate modifies extent)
        dsl = """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
"""
        program, _ = parse_and_validate(dsl)
        transformer = DSLToGemPyTransformer()

        config1 = transformer.transform(program, name="TestConfig1")
        config2 = transformer.transform(program, name="TestConfig2")

        gen1 = RuleBasedSpatialGenerator(seed=123)
        gen2 = RuleBasedSpatialGenerator(seed=123)

        data1 = gen1.generate(config1)
        data2 = gen2.generate(config2)

        assert len(data1.surface_points) == len(data2.surface_points)
        # Check first point is the same
        assert data1.surface_points[0].x == data2.surface_points[0].x


class TestGemPyValidators:
    """Tests for GemPy validators."""

    @pytest.fixture
    def valid_config(self):
        """Create a valid config."""
        dsl = """
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Limestone"; type: sedimentary ]
DEPOSITION D1 [ rock: R1 ]
DEPOSITION D2 [ rock: R2; after: D1 ]
"""
        program, _ = parse_and_validate(dsl)
        transformer = DSLToGemPyTransformer()
        return transformer.transform(program, name="ValidConfig")

    def test_config_validator_passes_valid(self, valid_config):
        """Test that valid config passes validation."""
        validator = GemPyConfigValidator()
        result = validator.validate(valid_config)
        assert result.is_valid

    def test_data_validator_passes_valid(self, valid_config):
        """Test that valid data passes validation."""
        generator = RuleBasedSpatialGenerator(seed=42)
        model_data = generator.generate(valid_config)

        validator = GemPyDataValidator()
        result = validator.validate(model_data)
        assert result.is_valid
