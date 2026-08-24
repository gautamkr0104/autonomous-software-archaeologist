"""Analysis API routes."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# In-memory store for demo purposes; production would use a database
_analysis_store: dict[str, dict[str, Any]] = {}


class AnalysisRequest(BaseModel):
    """Request to start a new analysis."""

    url: str | None = Field(None, description="GitHub URL to analyze")
    local_path: str | None = Field(None, description="Local repository path")
    commit_ref: str | None = Field(None, description="Specific commit to analyze")
    branch: str | None = Field(None, description="Branch to checkout")
    phases: list[str] | None = Field(None, description="Phases to run")


class AnalysisResponse(BaseModel):
    """Response with analysis status."""

    id: str
    status: str
    message: str


async def _run_background_analysis(analysis_id: str, request: AnalysisRequest) -> None:
    """Run analysis in background."""
    from asa.config.settings import get_settings
    from asa.core.orchestrator import AnalysisOrchestrator

    _analysis_store[analysis_id]["status"] = "running"

    try:
        settings = get_settings()
        orchestrator = AnalysisOrchestrator(settings)
        project = await orchestrator.run_full_analysis(
            url=request.url,
            local_path=request.local_path,
            commit_ref=request.commit_ref,
            branch=request.branch,
            phases=request.phases,
        )
        _analysis_store[analysis_id]["status"] = "completed"
        _analysis_store[analysis_id]["result"] = project.model_dump()
    except Exception as e:
        _analysis_store[analysis_id]["status"] = "failed"
        _analysis_store[analysis_id]["error"] = str(e)


@router.post("/start", response_model=AnalysisResponse)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> AnalysisResponse:
    """Start a new repository analysis."""
    import uuid

    if not request.url and not request.local_path:
        raise HTTPException(status_code=400, detail="Must provide url or local_path")

    analysis_id = str(uuid.uuid4())[:8]
    _analysis_store[analysis_id] = {"status": "pending"}

    background_tasks.add_task(_run_background_analysis, analysis_id, request)

    return AnalysisResponse(
        id=analysis_id,
        status="pending",
        message="Analysis started in background",
    )


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict:
    """Get analysis results."""
    if analysis_id not in _analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _analysis_store[analysis_id]


@router.get("/")
async def list_analyses() -> list[dict]:
    """List all analyses."""
    return [
        {"id": aid, "status": data.get("status", "unknown")}
        for aid, data in _analysis_store.items()
    ]
