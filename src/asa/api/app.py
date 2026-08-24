"""FastAPI application for ASA web interface and API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from asa.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ASA — Autonomous Software Archaeologist",
        description="Reconstructs how software works from repositories.",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and register routes
    from asa.api.routes import analysis, findings, graph, health, investigation

    app.include_router(health.router, tags=["health"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    app.include_router(findings.router, prefix="/api/findings", tags=["findings"])
    app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
    app.include_router(investigation.router, prefix="/api/investigate", tags=["investigation"])

    return app
