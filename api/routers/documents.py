"""Document management API routes."""

import os
import shutil
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from geo_lm.config import settings
from geo_lm.domain.document import Document
from geo_lm.exceptions import NotFoundError
from api.models import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(document: DocumentCreate):
    """Create a new document."""
    doc = Document(title=document.title)
    await doc.save()
    return DocumentResponse.model_validate(doc)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), title: Optional[str] = None):
    """Upload a PDF document."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Create uploads directory if needed
    os.makedirs(settings.uploads_dir, exist_ok=True)

    # Save file
    file_path = os.path.join(settings.uploads_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create document record
    doc = Document(
        title=title or file.filename,
        source_path=file_path,
        status="pending",
    )
    await doc.save()

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all documents."""
    documents = await Document.get_all(order_by="created_at DESC")
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int):
    """Get a document by ID."""
    try:
        doc = await Document.get(document_id)
        return DocumentResponse.model_validate(doc)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: int):
    """Delete a document."""
    try:
        doc = await Document.get(document_id)

        # Delete associated file if exists
        if doc.source_path and os.path.exists(doc.source_path):
            os.remove(doc.source_path)

        await doc.delete()
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )


@router.post("/{document_id}/extract", response_model=DocumentResponse)
async def extract_text(document_id: int):
    """Extract text from a document's PDF."""
    try:
        doc = await Document.get(document_id)

        if not doc.source_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no source file",
            )

        if not os.path.exists(doc.source_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source file not found",
            )

        from geo_lm.parsers.pdf import extract_text_from_pdf

        doc.status = "processing"
        await doc.save()

        try:
            text = extract_text_from_pdf(doc.source_path)
            doc.raw_text = text
            doc.status = "completed"
        except Exception as e:
            doc.status = "failed"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract text: {e}",
            )
        finally:
            await doc.save()

        return DocumentResponse.model_validate(doc)

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
