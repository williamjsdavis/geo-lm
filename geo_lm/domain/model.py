"""Geological model domain models."""

import json
from typing import ClassVar, Optional

from .base import ObjectModel


class GeologicalModel(ObjectModel):
    """A GemPy geological model."""

    table_name: ClassVar[str] = "geological_models"

    name: str
    document_id: Optional[int] = None
    dsl_document_id: Optional[int] = None
    status: str = "pending"  # pending, generating, computed, failed
    extent_json: Optional[str] = None
    resolution_json: Optional[str] = None

    @property
    def extent(self) -> dict:
        """Get the model extent as a dictionary."""
        if self.extent_json:
            return json.loads(self.extent_json)
        return {}

    @extent.setter
    def extent(self, value: dict) -> None:
        """Set the model extent from a dictionary."""
        self.extent_json = json.dumps(value)

    @property
    def resolution(self) -> dict:
        """Get the model resolution as a dictionary."""
        if self.resolution_json:
            return json.loads(self.resolution_json)
        return {}

    @resolution.setter
    def resolution(self, value: dict) -> None:
        """Set the model resolution from a dictionary."""
        self.resolution_json = json.dumps(value)

    @property
    def is_computed(self) -> bool:
        """Check if model has been successfully computed."""
        return self.status == "computed"

    @property
    def is_failed(self) -> bool:
        """Check if model computation failed."""
        return self.status == "failed"

    @property
    def is_pending(self) -> bool:
        """Check if model is waiting to be processed."""
        return self.status in ("pending", "generating")
