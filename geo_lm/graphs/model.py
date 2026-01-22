"""LangGraph workflow for GemPy model building.

This workflow handles the conversion of validated DSL to GemPy 3D models:
DSL Text → Transform → Validate Config → Generate Spatial → Validate Data → Build Model
"""

from typing import TypedDict, Annotated, Any
from operator import add

from langgraph.graph import StateGraph, START, END

from geo_lm.parsers.dsl import parse_and_validate
from geo_lm.gempy.transformer import DSLToGemPyTransformer
from geo_lm.gempy.validator import GemPyConfigValidator, GemPyDataValidator
from geo_lm.gempy.spatial import RuleBasedSpatialGenerator
from geo_lm.gempy.builder import GemPyModelBuilder
from geo_lm.gempy.persistence import GemPyPersistenceService
from geo_lm.gempy.config import GemPyModelConfig, GemPyModelData


# --- State Definition ---


class ModelBuildState(TypedDict):
    """State for model building workflow."""

    # Input
    dsl_document_id: int
    dsl_text: str
    model_name: str | None

    # Intermediate data (serialized as dicts for state management)
    config: dict | None
    model_data: dict | None

    # Output
    model_id: int | None

    # Error tracking
    errors: Annotated[list[str], add]
    warnings: Annotated[list[str], add]

    # Status tracking
    status: str  # pending, parsing, transforming, generating, building, completed, failed


# --- Node Functions ---


async def parse_dsl_node(state: ModelBuildState) -> dict:
    """Parse and validate DSL text."""
    dsl_text = state.get("dsl_text")

    if not dsl_text:
        return {
            "errors": ["No DSL text provided"],
            "status": "failed",
        }

    try:
        program, result = parse_and_validate(dsl_text)

        if not result.is_valid:
            return {
                "errors": [str(e) for e in result.errors],
                "status": "failed",
            }

        # DSL is valid - transform node will re-parse to get AST
        # (AST objects can't be serialized in LangGraph state)
        return {
            "status": "parsed",
        }

    except Exception as e:
        return {
            "errors": [f"DSL parsing failed: {e}"],
            "status": "failed",
        }


async def transform_to_config_node(state: ModelBuildState) -> dict:
    """Transform DSL AST to GemPy configuration."""
    # Re-parse DSL since the AST can't be persisted in LangGraph state
    dsl_text = state.get("dsl_text")

    if not dsl_text:
        return {
            "errors": ["No DSL text available for transformation"],
            "status": "failed",
        }

    try:
        # Parse again to get the AST (lightweight operation)
        program, parse_result = parse_and_validate(dsl_text)

        if not parse_result.is_valid:
            return {
                "errors": [str(e) for e in parse_result.errors],
                "status": "failed",
            }

        transformer = DSLToGemPyTransformer()
        model_name = state.get("model_name") or f"Model_{state['dsl_document_id']}"

        config = transformer.transform(
            program,
            name=model_name,
            dsl_document_id=state.get("dsl_document_id"),
        )

        # Validate config before spatial generation
        validator = GemPyConfigValidator()
        result = validator.validate(config)

        warnings = []
        if result.warnings:
            warnings = result.warnings

        if not result.is_valid:
            return {
                "errors": result.errors,
                "warnings": warnings,
                "status": "failed",
            }

        return {
            "config": config.model_dump(),
            "warnings": warnings,
            "status": "transformed",
        }

    except Exception as e:
        return {
            "errors": [f"Transformation failed: {e}"],
            "status": "failed",
        }


async def generate_spatial_node(state: ModelBuildState) -> dict:
    """Generate spatial data (points and orientations)."""
    config_dict = state.get("config")

    if not config_dict:
        return {
            "errors": ["No model configuration available"],
            "status": "failed",
        }

    try:
        config = GemPyModelConfig(**config_dict)

        # Generate spatial data
        generator = RuleBasedSpatialGenerator()
        model_data = generator.generate(config)

        # Validate complete data
        validator = GemPyDataValidator()
        result = validator.validate(model_data)

        warnings = []
        if result.warnings:
            warnings = result.warnings

        if not result.is_valid:
            return {
                "errors": result.errors,
                "warnings": warnings,
                "status": "failed",
            }

        return {
            "model_data": model_data.model_dump(),
            "warnings": warnings,
            "status": "spatial_generated",
        }

    except Exception as e:
        return {
            "errors": [f"Spatial generation failed: {e}"],
            "status": "failed",
        }


async def build_model_node(state: ModelBuildState) -> dict:
    """Build and compute GemPy model, then persist to database."""
    model_data_dict = state.get("model_data")

    if not model_data_dict:
        return {
            "errors": ["No model data available"],
            "status": "failed",
        }

    try:
        model_data = GemPyModelData(**model_data_dict)

        # Build GemPy model
        builder = GemPyModelBuilder()
        geo_model = builder.build(model_data)

        # Compute the model
        builder.compute(geo_model)

        # Persist to database
        persistence = GemPyPersistenceService()
        model_id = await persistence.save_model_data(model_data)

        return {
            "model_id": model_id,
            "status": "completed",
        }

    except Exception as e:
        return {
            "errors": [f"GemPy build failed: {e}"],
            "status": "failed",
        }


# --- Routing Functions ---


def check_status(state: ModelBuildState) -> str:
    """Check if we should continue or stop."""
    if state.get("status") == "failed":
        return END
    return "continue"


# --- Workflow Definition ---


def create_model_workflow() -> StateGraph:
    """Create and return the model building workflow."""
    workflow = StateGraph(ModelBuildState)

    # Add nodes
    workflow.add_node("parse_dsl", parse_dsl_node)
    workflow.add_node("transform_config", transform_to_config_node)
    workflow.add_node("generate_spatial", generate_spatial_node)
    workflow.add_node("build_model", build_model_node)

    # Add edges
    workflow.add_edge(START, "parse_dsl")
    workflow.add_conditional_edges(
        "parse_dsl",
        check_status,
        {"continue": "transform_config", END: END},
    )
    workflow.add_conditional_edges(
        "transform_config",
        check_status,
        {"continue": "generate_spatial", END: END},
    )
    workflow.add_conditional_edges(
        "generate_spatial",
        check_status,
        {"continue": "build_model", END: END},
    )
    workflow.add_edge("build_model", END)

    return workflow


def compile_model_workflow():
    """Compile the model building workflow."""
    workflow = create_model_workflow()
    return workflow.compile()


# --- Convenience Functions ---


async def build_model_from_dsl(
    dsl_document_id: int,
    dsl_text: str,
    model_name: str | None = None,
) -> ModelBuildState:
    """Build a model from DSL text.

    Args:
        dsl_document_id: The DSL document ID in the database
        dsl_text: The raw DSL text to process
        model_name: Optional custom model name

    Returns:
        Final state after processing
    """
    app = compile_model_workflow()

    initial_state: ModelBuildState = {
        "dsl_document_id": dsl_document_id,
        "dsl_text": dsl_text,
        "model_name": model_name,
        "config": None,
        "model_data": None,
        "model_id": None,
        "errors": [],
        "warnings": [],
        "status": "pending",
    }

    # Run the workflow
    final_state = await app.ainvoke(initial_state)

    return final_state
