"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# Import app after setting up test environment
import os
os.environ["GEO_LM_DATABASE_PATH"] = ":memory:"


@pytest.fixture
async def client():
    """Create test client with in-memory database."""
    from api.main import app
    from geo_lm.database.connection import init_db

    # Initialize in-memory database
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check returns OK."""
        response = await client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self, client):
        """Test root endpoint returns app info."""
        response = await client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "geo-lm"
        assert "version" in data


class TestDSLEndpoints:
    """Test DSL-related endpoints."""

    @pytest.mark.asyncio
    async def test_parse_valid_dsl(self, client, sample_dsl_valid):
        """Test parsing valid DSL."""
        response = await client.post(
            "/api/dsl/parse",
            json={"dsl_text": sample_dsl_valid}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is True
        assert data["rocks_count"] == 3
        assert data["depositions_count"] == 2
        assert data["erosions_count"] == 1
        assert data["intrusions_count"] == 1

    @pytest.mark.asyncio
    async def test_parse_invalid_dsl(self, client, sample_dsl_invalid_reference):
        """Test parsing invalid DSL returns errors."""
        response = await client.post(
            "/api/dsl/parse",
            json={"dsl_text": sample_dsl_invalid_reference}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_parse_syntax_error(self, client, sample_dsl_syntax_error):
        """Test parsing DSL with syntax error."""
        response = await client.post(
            "/api/dsl/parse",
            json={"dsl_text": sample_dsl_syntax_error}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_endpoint(self, client, sample_dsl_valid):
        """Test validate endpoint (alias for parse)."""
        response = await client.post(
            "/api/dsl/validate",
            json={"dsl_text": sample_dsl_valid}
        )
        assert response.status_code == 200
        assert response.json()["is_valid"] is True

    @pytest.mark.asyncio
    async def test_create_dsl_document(self, client, sample_dsl_valid):
        """Test creating a DSL document."""
        response = await client.post(
            "/api/dsl",
            json={"dsl_text": sample_dsl_valid}
        )
        assert response.status_code == 201

        data = response.json()
        assert data["id"] is not None
        assert data["is_valid"] is True
        assert data["raw_dsl"] == sample_dsl_valid

    @pytest.mark.asyncio
    async def test_get_grammar_spec(self, client):
        """Test getting grammar specification."""
        response = await client.get("/api/dsl/grammar/spec")
        assert response.status_code == 200

        data = response.json()
        assert "grammar" in data
        assert "example" in data
        assert "ROCK" in data["grammar"]


class TestDocumentEndpoints:
    """Test document-related endpoints."""

    @pytest.mark.asyncio
    async def test_create_document(self, client):
        """Test creating a document."""
        response = await client.post(
            "/api/documents",
            json={"title": "Test Document"}
        )
        assert response.status_code == 201

        data = response.json()
        assert data["id"] is not None
        assert data["title"] == "Test Document"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_documents(self, client):
        """Test listing documents."""
        # Create a document first
        await client.post(
            "/api/documents",
            json={"title": "Test Document"}
        )

        response = await client.get("/api/documents")
        assert response.status_code == 200

        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_document(self, client):
        """Test getting a specific document."""
        # Create a document
        create_response = await client.post(
            "/api/documents",
            json={"title": "Test Document"}
        )
        doc_id = create_response.json()["id"]

        # Get the document
        response = await client.get(f"/api/documents/{doc_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "Test Document"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client):
        """Test getting non-existent document returns 404."""
        response = await client.get("/api/documents/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document(self, client):
        """Test deleting a document."""
        # Create a document
        create_response = await client.post(
            "/api/documents",
            json={"title": "Test Document"}
        )
        doc_id = create_response.json()["id"]

        # Delete the document
        response = await client.delete(f"/api/documents/{doc_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/documents/{doc_id}")
        assert get_response.status_code == 404
