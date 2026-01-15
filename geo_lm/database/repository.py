"""Repository pattern for database operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

import aiosqlite

from .connection import get_db

T = TypeVar("T")


async def repo_query(
    query: str, params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Execute a query and return results as list of dicts."""
    async with get_db() as conn:
        if params:
            # Convert named params to positional for aiosqlite
            cursor = await conn.execute(query, params)
        else:
            cursor = await conn.execute(query)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def repo_execute(query: str, params: Optional[tuple] = None) -> int:
    """Execute a query and return rows affected."""
    async with get_db() as conn:
        cursor = await conn.execute(query, params or ())
        return cursor.rowcount


async def repo_create(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new record in the table."""
    columns = list(data.keys())
    placeholders = ", ".join(["?" for _ in columns])
    column_names = ", ".join(columns)
    values = [data[col] for col in columns]

    async with get_db() as conn:
        cursor = await conn.execute(
            f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})", values
        )
        last_id = cursor.lastrowid

        # Fetch the created record
        cursor = await conn.execute(f"SELECT * FROM {table} WHERE id = ?", (last_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {"id": last_id, **data}


async def repo_update(
    table: str, id: int, data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Update a record in the table."""
    # Add updated_at timestamp
    data["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
    values = list(data.values()) + [id]

    async with get_db() as conn:
        await conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", values)

        # Fetch the updated record
        cursor = await conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def repo_delete(table: str, id: int) -> bool:
    """Delete a record from the table."""
    async with get_db() as conn:
        cursor = await conn.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
        return cursor.rowcount > 0


async def repo_get(table: str, id: int) -> Optional[Dict[str, Any]]:
    """Get a single record by ID."""
    async with get_db() as conn:
        cursor = await conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def repo_get_all(
    table: str, order_by: Optional[str] = None, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get all records from a table."""
    query = f"SELECT * FROM {table}"
    if order_by:
        query += f" ORDER BY {order_by}"
    if limit:
        query += f" LIMIT {limit}"

    async with get_db() as conn:
        cursor = await conn.execute(query)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def repo_find(
    table: str, conditions: Dict[str, Any], order_by: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find records matching conditions."""
    where_clause = " AND ".join([f"{col} = ?" for col in conditions.keys()])
    values = list(conditions.values())

    query = f"SELECT * FROM {table} WHERE {where_clause}"
    if order_by:
        query += f" ORDER BY {order_by}"

    async with get_db() as conn:
        cursor = await conn.execute(query, values)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def repo_count(table: str, conditions: Optional[Dict[str, Any]] = None) -> int:
    """Count records in a table."""
    query = f"SELECT COUNT(*) as count FROM {table}"
    values = []

    if conditions:
        where_clause = " AND ".join([f"{col} = ?" for col in conditions.keys()])
        query += f" WHERE {where_clause}"
        values = list(conditions.values())

    async with get_db() as conn:
        cursor = await conn.execute(query, values)
        row = await cursor.fetchone()
        return row["count"] if row else 0
