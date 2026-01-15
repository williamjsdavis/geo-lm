"""Document domain models."""

from datetime import datetime
from typing import ClassVar, Optional

from .base import ObjectModel


class Document(ObjectModel):
    """A geological document (PDF, text file)."""

    table_name: ClassVar[str] = "documents"

    title: str
    source_path: Optional[str] = None
    raw_text: Optional[str] = None
    consolidated_text: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed

    @property
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.status == "completed"

    @property
    def has_text(self) -> bool:
        """Check if document has extracted text."""
        return bool(self.raw_text)

    @property
    def has_consolidated_text(self) -> bool:
        """Check if document has consolidated text."""
        return bool(self.consolidated_text)


class DSLDocument(ObjectModel):
    """A parsed and validated DSL document."""

    table_name: ClassVar[str] = "dsl_documents"

    document_id: Optional[int] = None
    raw_dsl: str
    is_valid: bool = False
    validation_errors: Optional[str] = None

    @property
    def errors_list(self) -> list[str]:
        """Get validation errors as a list."""
        if not self.validation_errors:
            return []
        return self.validation_errors.split("\n")
