"""FastAPI application for geo-lm."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from geo_lm import __version__
from geo_lm.config import settings
from geo_lm.database.connection import init_db, DatabaseConnection
from api.models import HealthResponse
from api.routers import documents, dsl, workflows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.ensure_directories()
    await init_db()
    yield
    # Shutdown
    await DatabaseConnection.close()


app = FastAPI(
    title="geo-lm API",
    description="API for geological document processing and 3D model generation",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api")
app.include_router(dsl.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
        database="connected",
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "geo-lm",
        "version": __version__,
        "docs": "/docs",
        "api": "/api",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
