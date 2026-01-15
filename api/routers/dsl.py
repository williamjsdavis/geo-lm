"""DSL parsing and validation API routes."""

from fastapi import APIRouter, HTTPException, status

from geo_lm.domain.document import DSLDocument
from geo_lm.exceptions import NotFoundError
from geo_lm.parsers.dsl import parse, validate, parse_and_validate
from geo_lm.parsers.dsl.errors import DSLSyntaxError, DSLParseError
from api.models import (
    DSLParseRequest,
    DSLParseResponse,
    DSLValidationError,
    DSLDocumentResponse,
)

router = APIRouter(prefix="/dsl", tags=["dsl"])


@router.post("/parse", response_model=DSLParseResponse)
async def parse_dsl(request: DSLParseRequest):
    """Parse and validate DSL text."""
    try:
        program, result = parse_and_validate(request.dsl_text)

        errors = []
        for error in result.errors:
            errors.append(
                DSLValidationError(
                    message=str(error),
                    line=error.location.line if error.location else None,
                    column=error.location.column if error.location else None,
                )
            )

        return DSLParseResponse(
            is_valid=result.is_valid,
            errors=errors,
            rocks_count=len(program.rocks),
            depositions_count=len(program.depositions),
            erosions_count=len(program.erosions),
            intrusions_count=len(program.intrusions),
        )

    except DSLSyntaxError as e:
        return DSLParseResponse(
            is_valid=False,
            errors=[
                DSLValidationError(
                    message=e.message,
                    line=e.line,
                    column=e.column,
                )
            ],
        )

    except DSLParseError as e:
        return DSLParseResponse(
            is_valid=False,
            errors=[DSLValidationError(message=str(e))],
        )


@router.post("/validate", response_model=DSLParseResponse)
async def validate_dsl(request: DSLParseRequest):
    """Validate DSL text (alias for parse)."""
    return await parse_dsl(request)


@router.get("/{dsl_id}", response_model=DSLDocumentResponse)
async def get_dsl_document(dsl_id: int):
    """Get a DSL document by ID."""
    try:
        dsl_doc = await DSLDocument.get(dsl_id)
        return DSLDocumentResponse.model_validate(dsl_doc)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DSL document {dsl_id} not found",
        )


@router.post("", response_model=DSLDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_dsl_document(request: DSLParseRequest, document_id: int = None):
    """Create a new DSL document from text."""
    try:
        program, result = parse_and_validate(request.dsl_text)

        dsl_doc = DSLDocument(
            document_id=document_id,
            raw_dsl=request.dsl_text,
            is_valid=result.is_valid,
            validation_errors="\n".join(str(e) for e in result.errors)
            if result.errors
            else None,
        )
        await dsl_doc.save()

        return DSLDocumentResponse.model_validate(dsl_doc)

    except (DSLSyntaxError, DSLParseError) as e:
        dsl_doc = DSLDocument(
            document_id=document_id,
            raw_dsl=request.dsl_text,
            is_valid=False,
            validation_errors=str(e),
        )
        await dsl_doc.save()

        return DSLDocumentResponse.model_validate(dsl_doc)


@router.get("/grammar/spec")
async def get_grammar_spec():
    """Get the DSL grammar specification."""
    return {
        "grammar": """
# Geology DSL Grammar

## Rock Definition
ROCK <ID> [ name: "<name>"; type: <type>; age?: <age> ]

## Event Types
DEPOSITION <ID> [ rock: <rock_id>; time?: <time>; after?: <id_list> ]
EROSION <ID> [ time?: <time>; after?: <id_list> ]
INTRUSION <ID> [ rock: <rock_id>; style?: <style>; time?: <time>; after?: <id_list> ]

## Values
- type: sedimentary | volcanic | intrusive | metamorphic
- style: dike | sill | stock | batholith
- age/time: <number>Ma | <number>ka | <number>Ga | "?"
- id_list: <ID>, <ID>, ...
""",
        "example": """
ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]
ROCK R2 [ name: "Granite"; type: intrusive; age: 50Ma ]

DEPOSITION D1 [ rock: R1; time: 100Ma ]
INTRUSION I1 [ rock: R2; style: stock; time: 50Ma; after: D1 ]
""",
    }
