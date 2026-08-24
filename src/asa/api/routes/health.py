"""Health check endpoint."""

from fastapi import APIRouter

from asa.config.settings import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """System health check."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "name": settings.app_name,
    }


@router.get("/status")
async def status() -> dict:
    """Detailed system status."""
    from asa.analysis.parsers.tree_sitter_parser import TreeSitterParser

    parser = TreeSitterParser()
    settings = get_settings()

    return {
        "status": "ok",
        "version": settings.app_version,
        "tree_sitter": {
            "available": bool(parser.available_languages),
            "languages": sorted(parser.available_languages),
        },
        "features": {
            "repository_ingestion": True,
            "static_analysis": True,
            "dependency_graph": True,
            "knowledge_graph": True,
            "git_history": True,
        },
    }
