"""LangGraph workflow for document processing pipeline.

This workflow handles the full document processing flow:
PDF → Text Extraction → Consolidation → DSL Generation → Validation
"""

import os
from typing import TypedDict, Annotated, Literal
from operator import add

from langgraph.graph import StateGraph, START, END

from geo_lm.config import settings
from geo_lm.ai.models import ModelManager
from geo_lm.parsers.dsl import parse_and_validate
from geo_lm.parsers.dsl.errors import DSLSyntaxError, DSLParseError


# --- Prompt Templates ---

CONSOLIDATION_SYSTEM_PROMPT = """You are a senior geologist with many years of experience.
Your job is to consolidate geological descriptions into coherent summaries.
Focus on: rock types present, the orientation of large-scale structures, stratigraphic relationships, erosion, and igneous intrusions.
Ignore: Chemical analysis, mineralogy, and other non-geological information."""

CONSOLIDATION_USER_PROMPT = """Consolidate the following geological description into one or two paragraphs without line breaks.
Avoid using headings and bullet points.

Geological description:
{text}"""

DSL_SYSTEM_PROMPT = """You are an expert geological interpreter and DSL compiler.
Your goal is to read a free-text description of an area's stratigraphy, structures, and events,
then emit a concise, declarative DSL encoding of that description."""

DSL_USER_PROMPT = """Parse the following geological description and output DSL statements.

Geological description:
{consolidated_text}

STRICT SYNTAX RULES:
1. Rock names MUST be in double quotes: name: "Sandstone"
2. Age/time MUST be a NUMBER followed by Ma, ka, or Ga: age: 40Ma, time: 35Ma
3. If age/time is NOT specified in the text, OMIT that field entirely
4. Do NOT use placeholders like T1, T2 - only real numbers or omit the field
5. Use "after:" to show relative ordering when absolute times are unknown

DSL Grammar:
  ROCK <ID> [ name: "<string>"; type: <sedimentary|volcanic|intrusive|metamorphic> ]
  DEPOSITION <ID> [ rock: <ID> ]
  DEPOSITION <ID> [ rock: <ID>; after: <ID> ]
  EROSION <ID> [ after: <ID> ]
  INTRUSION <ID> [ rock: <ID>; style: <dike|sill|stock|batholith>; after: <ID> ]

Example with known ages:
ROCK R1 [ name: "Andesite"; type: volcanic; age: 40Ma ]
DEPOSITION D1 [ rock: R1; time: 40Ma ]

Example with unknown ages (use after: for ordering):
ROCK R1 [ name: "Sandstone"; type: sedimentary ]
ROCK R2 [ name: "Granite"; type: intrusive ]
DEPOSITION D1 [ rock: R1 ]
INTRUSION I1 [ rock: R2; style: stock; after: D1 ]

Instructions:
- Output ONLY valid DSL statements, one per line
- Order: ROCK definitions first, then DEPOSITION, then EROSION, then INTRUSION
- Use "after:" to establish sequence when absolute ages are unknown
- No placeholders, no variables, no comments, no markdown"""

DSL_RETRY_PROMPT = """The previous DSL output had validation errors. Please fix these errors and regenerate.

Previous DSL:
```
{previous_dsl}
```

Validation errors:
{errors}

Original geological description:
{consolidated_text}

Output ONLY the corrected DSL statements, nothing else."""


# --- State Definition ---

class DocumentState(TypedDict):
    """State for document processing workflow."""

    document_id: int
    source_path: str | None
    raw_text: str | None
    consolidated_text: str | None
    dsl_text: str | None
    is_valid: bool
    validation_errors: Annotated[list[str], add]
    retry_count: int
    errors: Annotated[list[str], add]
    status: str


# --- Node Functions ---

async def extract_text(state: DocumentState) -> dict:
    """Extract text from PDF file."""
    source_path = state.get("source_path")

    if not source_path:
        return {
            "errors": ["No source path provided"],
            "status": "failed",
        }

    if not os.path.exists(source_path):
        return {
            "errors": [f"Source file not found: {source_path}"],
            "status": "failed",
        }

    try:
        from geo_lm.parsers.pdf import extract_text_from_pdf

        text = extract_text_from_pdf(source_path)

        if not text:
            return {
                "errors": ["Failed to extract text from PDF"],
                "status": "failed",
            }

        return {
            "raw_text": text,
            "status": "text_extracted",
        }

    except Exception as e:
        return {
            "errors": [f"PDF extraction error: {str(e)}"],
            "status": "failed",
        }


async def consolidate_text(state: DocumentState) -> dict:
    """Consolidate raw text using LLM."""
    raw_text = state.get("raw_text")

    if not raw_text:
        return {
            "errors": ["No raw text to consolidate"],
            "status": "failed",
        }

    try:
        manager = ModelManager()
        provider = await manager.get_default_provider()

        prompt = CONSOLIDATION_USER_PROMPT.format(text=raw_text)

        consolidated = await provider.generate(
            prompt=prompt,
            system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
            temperature=settings.llm_temperature,
        )

        return {
            "consolidated_text": consolidated,
            "status": "consolidated",
        }

    except Exception as e:
        return {
            "errors": [f"Consolidation error: {str(e)}"],
            "status": "failed",
        }


async def generate_dsl(state: DocumentState) -> dict:
    """Generate DSL from consolidated text using LLM."""
    consolidated_text = state.get("consolidated_text")

    if not consolidated_text:
        return {
            "errors": ["No consolidated text for DSL generation"],
            "status": "failed",
        }

    try:
        manager = ModelManager()
        provider = await manager.get_default_provider()

        # Check if this is a retry
        previous_dsl = state.get("dsl_text")
        validation_errors = state.get("validation_errors", [])

        if previous_dsl and validation_errors:
            # Retry with error feedback
            prompt = DSL_RETRY_PROMPT.format(
                previous_dsl=previous_dsl,
                errors="\n".join(validation_errors),
                consolidated_text=consolidated_text,
            )
        else:
            # Initial generation
            prompt = DSL_USER_PROMPT.format(consolidated_text=consolidated_text)

        dsl_text = await provider.generate(
            prompt=prompt,
            system_prompt=DSL_SYSTEM_PROMPT,
            temperature=settings.llm_temperature,
        )

        # Clean up response - extract DSL from code blocks if present
        dsl_text = _clean_dsl_response(dsl_text)

        return {
            "dsl_text": dsl_text,
            "status": "dsl_generated",
        }

    except Exception as e:
        return {
            "errors": [f"DSL generation error: {str(e)}"],
            "status": "failed",
        }


def _clean_dsl_response(text: str) -> str:
    """Clean LLM response to extract just DSL code."""
    import re

    # Try to extract from code blocks
    code_block_match = re.search(r"```(?:dsl)?\n?(.*?)```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Otherwise return as-is, stripping whitespace
    return text.strip()


async def validate_dsl(state: DocumentState) -> dict:
    """Validate the generated DSL."""
    dsl_text = state.get("dsl_text")

    if not dsl_text:
        return {
            "is_valid": False,
            "validation_errors": ["No DSL text to validate"],
            "status": "validation_failed",
        }

    try:
        program, result = parse_and_validate(dsl_text)

        if result.is_valid:
            return {
                "is_valid": True,
                "validation_errors": [],
                "status": "completed",
            }
        else:
            error_messages = [str(e) for e in result.errors]
            return {
                "is_valid": False,
                "validation_errors": error_messages,
                "retry_count": state.get("retry_count", 0) + 1,
                "status": "validation_failed",
            }

    except DSLSyntaxError as e:
        return {
            "is_valid": False,
            "validation_errors": [f"Syntax error at line {e.line}: {e.message}"],
            "retry_count": state.get("retry_count", 0) + 1,
            "status": "validation_failed",
        }

    except DSLParseError as e:
        return {
            "is_valid": False,
            "validation_errors": [str(e)],
            "retry_count": state.get("retry_count", 0) + 1,
            "status": "validation_failed",
        }


# --- Routing Functions ---

def should_retry(state: DocumentState) -> str:
    """Determine if we should retry DSL generation."""
    if state.get("is_valid"):
        return END

    retry_count = state.get("retry_count", 0)
    max_retries = settings.max_dsl_retries

    if retry_count < max_retries:
        return "generate_dsl"
    else:
        return END


def check_extraction(state: DocumentState) -> str:
    """Check if text extraction succeeded."""
    if state.get("status") == "failed":
        return END
    return "consolidate"


def check_consolidation(state: DocumentState) -> str:
    """Check if consolidation succeeded."""
    if state.get("status") == "failed":
        return END
    return "generate_dsl"


def check_generation(state: DocumentState) -> str:
    """Check if DSL generation succeeded."""
    if state.get("status") == "failed":
        return END
    return "validate_dsl"


# --- Workflow Definition ---

def create_document_workflow() -> StateGraph:
    """Create and return the document processing workflow."""
    workflow = StateGraph(DocumentState)

    # Add nodes
    workflow.add_node("extract_text", extract_text)
    workflow.add_node("consolidate", consolidate_text)
    workflow.add_node("generate_dsl", generate_dsl)
    workflow.add_node("validate_dsl", validate_dsl)

    # Add edges
    workflow.add_edge(START, "extract_text")
    workflow.add_conditional_edges("extract_text", check_extraction)
    workflow.add_conditional_edges("consolidate", check_consolidation)
    workflow.add_conditional_edges("generate_dsl", check_generation)
    workflow.add_conditional_edges("validate_dsl", should_retry)

    return workflow


def compile_document_workflow():
    """Compile the document processing workflow."""
    workflow = create_document_workflow()
    return workflow.compile()


# --- Convenience Functions ---

async def process_document(
    document_id: int,
    source_path: str,
) -> DocumentState:
    """
    Process a document through the full pipeline.

    Args:
        document_id: The document ID in the database.
        source_path: Path to the PDF file.

    Returns:
        Final state after processing.
    """
    app = compile_document_workflow()

    initial_state: DocumentState = {
        "document_id": document_id,
        "source_path": source_path,
        "raw_text": None,
        "consolidated_text": None,
        "dsl_text": None,
        "is_valid": False,
        "validation_errors": [],
        "retry_count": 0,
        "errors": [],
        "status": "pending",
    }

    # Run the workflow
    final_state = await app.ainvoke(initial_state)

    return final_state


async def process_text(
    document_id: int,
    raw_text: str,
) -> DocumentState:
    """
    Process raw text through the pipeline (skip PDF extraction).

    Args:
        document_id: The document ID in the database.
        raw_text: The raw text to process.

    Returns:
        Final state after processing.
    """
    app = compile_document_workflow()

    initial_state: DocumentState = {
        "document_id": document_id,
        "source_path": None,
        "raw_text": raw_text,
        "consolidated_text": None,
        "dsl_text": None,
        "is_valid": False,
        "validation_errors": [],
        "retry_count": 0,
        "errors": [],
        "status": "text_extracted",  # Skip extraction
    }

    # Run from consolidation step
    final_state = await app.ainvoke(initial_state)

    return final_state
