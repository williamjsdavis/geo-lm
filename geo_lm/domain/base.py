"""Base domain model with SQLite CRUD operations."""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict

from geo_lm.database.repository import (
    repo_create,
    repo_delete,
    repo_get,
    repo_get_all,
    repo_update,
    repo_find,
)
from geo_lm.exceptions import NotFoundError, DatabaseError

T = TypeVar("T", bound="ObjectModel")


class ObjectModel(BaseModel):
    """
    Base class for domain models with SQLite CRUD operations.

    Subclasses must define:
        table_name: ClassVar[str] - the database table name

    Example:
        class Document(ObjectModel):
            table_name: ClassVar[str] = "documents"
            title: str
            content: Optional[str] = None

        # Create
        doc = Document(title="My Doc")
        await doc.save()

        # Read
        doc = await Document.get(1)

        # Update
        doc.content = "Hello"
        await doc.save()

        # Delete
        await doc.delete()
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    id: Optional[int] = None
    table_name: ClassVar[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def get(cls: Type[T], id: int) -> T:
        """
        Get a record by ID.

        Args:
            id: The record ID.

        Returns:
            The model instance.

        Raises:
            NotFoundError: If record not found.
        """
        if not cls.table_name:
            raise ValueError("table_name must be defined")

        data = await repo_get(cls.table_name, id)
        if not data:
            raise NotFoundError(f"{cls.__name__} with id {id} not found")

        return cls(**data)

    @classmethod
    async def get_all(cls: Type[T], order_by: Optional[str] = None) -> List[T]:
        """
        Get all records.

        Args:
            order_by: Optional column to order by.

        Returns:
            List of model instances.
        """
        if not cls.table_name:
            raise ValueError("table_name must be defined")

        rows = await repo_get_all(cls.table_name, order_by=order_by)
        return [cls(**row) for row in rows]

    @classmethod
    async def find(
        cls: Type[T], conditions: Dict[str, Any], order_by: Optional[str] = None
    ) -> List[T]:
        """
        Find records matching conditions.

        Args:
            conditions: Dict of column=value conditions.
            order_by: Optional column to order by.

        Returns:
            List of matching model instances.
        """
        if not cls.table_name:
            raise ValueError("table_name must be defined")

        rows = await repo_find(cls.table_name, conditions, order_by=order_by)
        return [cls(**row) for row in rows]

    async def save(self) -> None:
        """
        Save the model to the database.

        Creates a new record if id is None, otherwise updates existing.
        """
        if not self.__class__.table_name:
            raise ValueError("table_name must be defined")

        # Prepare data for saving
        data = self._prepare_save_data()

        try:
            if self.id is None:
                # Create new record
                result = await repo_create(self.__class__.table_name, data)
                # Update instance with returned data
                for key, value in result.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            else:
                # Update existing record
                result = await repo_update(self.__class__.table_name, self.id, data)
                if result:
                    for key, value in result.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
        except Exception as e:
            raise DatabaseError(f"Failed to save {self.__class__.__name__}: {e}")

    async def delete(self) -> bool:
        """
        Delete the record from the database.

        Returns:
            True if deleted, False otherwise.

        Raises:
            ValueError: If id is None.
        """
        if self.id is None:
            raise ValueError("Cannot delete object without an ID")

        if not self.__class__.table_name:
            raise ValueError("table_name must be defined")

        return await repo_delete(self.__class__.table_name, self.id)

    async def refresh(self) -> None:
        """Refresh the model from the database."""
        if self.id is None:
            raise ValueError("Cannot refresh object without an ID")

        fresh = await self.__class__.get(self.id)
        for key, value in fresh.model_dump().items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _prepare_save_data(self) -> Dict[str, Any]:
        """Prepare data for saving to database."""
        data = self.model_dump(exclude={"id", "table_name", "created_at", "updated_at"})
        # Filter out None values except for nullable fields
        return {k: v for k, v in data.items() if v is not None}
