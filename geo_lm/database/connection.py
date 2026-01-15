"""SQLite database connection management."""

import os
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite

from geo_lm.config import settings


class DatabaseConnection:
    """Manages SQLite database connections."""

    _connection: Optional[aiosqlite.Connection] = None
    _db_path: str = None

    @classmethod
    def set_db_path(cls, path: str):
        """Set the database path."""
        cls._db_path = path

    @classmethod
    def get_db_path(cls) -> str:
        """Get the database path."""
        if cls._db_path:
            return cls._db_path
        return settings.database_path

    @classmethod
    async def get_connection(cls) -> aiosqlite.Connection:
        """Get or create the database connection."""
        if cls._connection is None:
            db_path = cls.get_db_path()
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            cls._connection = await aiosqlite.connect(db_path)
            cls._connection.row_factory = aiosqlite.Row
            # Enable foreign keys
            await cls._connection.execute("PRAGMA foreign_keys = ON")
        return cls._connection

    @classmethod
    async def close(cls):
        """Close the database connection."""
        if cls._connection:
            await cls._connection.close()
            cls._connection = None


@asynccontextmanager
async def get_db():
    """Context manager for database connections."""
    conn = await DatabaseConnection.get_connection()
    try:
        yield conn
    except Exception:
        await conn.rollback()
        raise
    else:
        await conn.commit()


async def init_db():
    """Initialize the database with schema."""
    async with get_db() as conn:
        await conn.executescript(SCHEMA)


SCHEMA = """
-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_path TEXT,
    raw_text TEXT,
    consolidated_text TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DSL documents
CREATE TABLE IF NOT EXISTS dsl_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    raw_dsl TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT FALSE,
    validation_errors TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- Geological models
CREATE TABLE IF NOT EXISTS geological_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    document_id INTEGER,
    dsl_document_id INTEGER,
    status TEXT DEFAULT 'pending',
    extent_json TEXT,
    resolution_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (dsl_document_id) REFERENCES dsl_documents(id) ON DELETE SET NULL
);

-- Surface points (GemPy input)
CREATE TABLE IF NOT EXISTS surface_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    surface TEXT NOT NULL,
    series TEXT,
    FOREIGN KEY (model_id) REFERENCES geological_models(id) ON DELETE CASCADE
);

-- Orientations (GemPy input)
CREATE TABLE IF NOT EXISTS orientations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    azimuth REAL NOT NULL,
    dip REAL NOT NULL,
    polarity REAL DEFAULT 1.0,
    surface TEXT NOT NULL,
    series TEXT,
    FOREIGN KEY (model_id) REFERENCES geological_models(id) ON DELETE CASCADE
);

-- Structural groups (GemPy input)
CREATE TABLE IF NOT EXISTS structural_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    group_index INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    elements_json TEXT NOT NULL,
    relation TEXT NOT NULL,
    FOREIGN KEY (model_id) REFERENCES geological_models(id) ON DELETE CASCADE
);

-- Settings table (key-value store)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_surface_points_model_id ON surface_points(model_id);
CREATE INDEX IF NOT EXISTS idx_orientations_model_id ON orientations(model_id);
CREATE INDEX IF NOT EXISTS idx_structural_groups_model_id ON structural_groups(model_id);
"""
