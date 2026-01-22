"""GemPy integration for geo-lm.

This package handles the conversion of DSL to 3D geological models using GemPy.

Main components:
- transformer: DSL AST -> GemPy configuration
- validator: Pre-GemPy validation
- spatial: Rule-based spatial data generation
- builder: GemPy model construction
- persistence: Database save/load
"""

from .config import (
    GemPyModelConfig,
    GemPyModelData,
    GemPyRelationType,
    ModelExtent,
    ModelResolution,
    Orientation,
    StructuralGroupConfig,
    SurfaceConfig,
    SurfacePoint,
)
from .errors import (
    GemPyBuildError,
    GemPyConfigError,
    GemPyError,
    GemPyValidationError,
    SpatialGenerationError,
    TransformationError,
)
from .transformer import DSLToGemPyTransformer
from .validator import GemPyConfigValidator, GemPyDataValidator, ValidationResult
from .spatial import RuleBasedSpatialGenerator
from .builder import GemPyModelBuilder, build_and_compute
from .persistence import GemPyPersistenceService
from .exporter import MeshExporter, ModelMeshData, SurfaceMesh, export_model_mesh

__all__ = [
    # Config models
    "GemPyModelConfig",
    "GemPyModelData",
    "GemPyRelationType",
    "ModelExtent",
    "ModelResolution",
    "Orientation",
    "StructuralGroupConfig",
    "SurfaceConfig",
    "SurfacePoint",
    # Errors
    "GemPyBuildError",
    "GemPyConfigError",
    "GemPyError",
    "GemPyValidationError",
    "SpatialGenerationError",
    "TransformationError",
    # Components
    "DSLToGemPyTransformer",
    "GemPyConfigValidator",
    "GemPyDataValidator",
    "ValidationResult",
    "RuleBasedSpatialGenerator",
    "GemPyModelBuilder",
    "build_and_compute",
    "GemPyPersistenceService",
    # Exporter
    "MeshExporter",
    "ModelMeshData",
    "SurfaceMesh",
    "export_model_mesh",
]
