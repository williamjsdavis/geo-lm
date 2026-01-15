"""Workflow execution API routes."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from geo_lm.domain.document import Document, DSLDocument
from geo_lm.exceptions import NotFoundError
from geo_lm.graphs import process_document, process_text
from api.models import (
    WorkflowRequest,
    WorkflowStatusResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Simple in-memory workflow status tracking
# In production, this should be in database or Redis
_workflow_status: dict[int, dict] = {}


@router.post("/{document_id}/process", response_model=WorkflowStatusResponse)
async def start_document_processing(
    document_id: int,
):
    """
    Start processing a document through the full pipeline.

    This runs asynchronously in the background. Use the status endpoint
    to check progress.
    """
    try:
        doc = await Document.get(document_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Initialize status
    _workflow_status[document_id] = {
        "status": "pending",
        "current_step": "queued",
        "progress": 0.0,
        "error": None,
    }

    # Run workflow in background using asyncio.create_task
    asyncio.create_task(_run_workflow(document_id, doc))

    return WorkflowStatusResponse(
        status="pending",
        current_step="queued",
        progress=0.0,
    )


async def _run_workflow(document_id: int, doc: Document):
    """Execute the workflow and update status."""
    try:
        _workflow_status[document_id]["status"] = "running"
        _workflow_status[document_id]["current_step"] = "extract_text"
        _workflow_status[document_id]["progress"] = 0.1

        # Update document status
        doc.status = "processing"
        await doc.save()

        # Determine whether to use PDF extraction or raw text
        if doc.source_path:
            _workflow_status[document_id]["current_step"] = "extract_text"
            result = await process_document(document_id, doc.source_path)
        elif doc.raw_text:
            _workflow_status[document_id]["current_step"] = "consolidate"
            _workflow_status[document_id]["progress"] = 0.25
            result = await process_text(document_id, doc.raw_text)
        else:
            _workflow_status[document_id]["status"] = "failed"
            _workflow_status[document_id]["error"] = "No source file or raw text"
            doc.status = "failed"
            await doc.save()
            return

        # Update progress based on final state
        if result["status"] == "completed":
            _workflow_status[document_id]["status"] = "completed"
            _workflow_status[document_id]["current_step"] = "completed"
            _workflow_status[document_id]["progress"] = 1.0

            # Save results to document
            if result.get("raw_text"):
                doc.raw_text = result["raw_text"]
            if result.get("consolidated_text"):
                doc.consolidated_text = result["consolidated_text"]
            doc.status = "completed"
            await doc.save()

            # Save DSL document if generated
            if result.get("dsl_text"):
                dsl_doc = DSLDocument(
                    document_id=document_id,
                    raw_dsl=result["dsl_text"],
                    is_valid=result.get("is_valid", False),
                    validation_errors="\n".join(result.get("validation_errors", [])) or None,
                )
                await dsl_doc.save()

        else:
            _workflow_status[document_id]["status"] = "failed"
            # Check for validation errors first, then general errors
            errors = result.get("errors", [])
            validation_errors = result.get("validation_errors", [])
            if validation_errors:
                _workflow_status[document_id]["error"] = f"DSL validation failed after {result.get('retry_count', 0)} retries: {'; '.join(validation_errors[:3])}"
            elif errors:
                _workflow_status[document_id]["error"] = "; ".join(errors)
            else:
                _workflow_status[document_id]["error"] = f"Workflow ended with status: {result.get('status', 'unknown')}"

            # Save partial results even on failure
            if result.get("raw_text"):
                doc.raw_text = result["raw_text"]
            if result.get("consolidated_text"):
                doc.consolidated_text = result["consolidated_text"]
            doc.status = "failed"
            await doc.save()

            # Save DSL document even if invalid (for debugging)
            if result.get("dsl_text"):
                dsl_doc = DSLDocument(
                    document_id=document_id,
                    raw_dsl=result["dsl_text"],
                    is_valid=False,
                    validation_errors="\n".join(validation_errors) if validation_errors else None,
                )
                await dsl_doc.save()

    except Exception as e:
        _workflow_status[document_id]["status"] = "failed"
        _workflow_status[document_id]["error"] = str(e)
        try:
            doc.status = "failed"
            await doc.save()
        except Exception:
            pass


@router.get("/{document_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(document_id: int):
    """Get the status of a document processing workflow."""
    if document_id not in _workflow_status:
        # Check if document exists
        try:
            doc = await Document.get(document_id)
            # Return status based on document status
            return WorkflowStatusResponse(
                status=doc.status,
                current_step=None,
                progress=1.0 if doc.status == "completed" else 0.0,
            )
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

    status_data = _workflow_status[document_id]
    return WorkflowStatusResponse(
        status=status_data["status"],
        current_step=status_data.get("current_step"),
        progress=status_data.get("progress"),
        error=status_data.get("error"),
    )


@router.post("/process-text")
async def process_raw_text(
    text: str,
    title: Optional[str] = "Untitled",
    background_tasks: BackgroundTasks = None,
):
    """
    Process raw text directly through the pipeline.

    Creates a new document and processes it.
    """
    # Create document with raw text
    doc = Document(
        title=title,
        raw_text=text,
        status="pending",
    )
    await doc.save()

    # Initialize status
    _workflow_status[doc.id] = {
        "status": "pending",
        "current_step": "queued",
        "progress": 0.0,
        "error": None,
    }

    # Run workflow in background
    if background_tasks:
        background_tasks.add_task(_run_workflow, doc.id, doc)
    else:
        # Run synchronously for testing
        await _run_workflow(doc.id, doc)

    return {
        "document_id": doc.id,
        "status": "pending",
        "message": "Document created and processing started",
    }
