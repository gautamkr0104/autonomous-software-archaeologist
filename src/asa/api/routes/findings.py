"""Findings API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from asa.core.evidence import Finding, FindingStatus
from asa.core.types import FindingCategory, FindingSeverity

router = APIRouter()

# In-memory findings store
_findings_store: list[Finding] = []


class FindingResponse(BaseModel):
    """A finding with full evidence chain."""

    id: str
    claim: str
    evidence_count: int
    confidence: float
    confidence_level: str
    status: str
    category: str
    severity: str
    source_files: list[str]
    reasoning: str
    created_by: str


@router.get("/")
async def list_findings(
    category: FindingCategory | None = Query(None),
    severity: FindingSeverity | None = Query(None),
    status: FindingStatus | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[FindingResponse]:
    """List findings with optional filters."""
    filtered = _findings_store

    if category:
        filtered = [f for f in filtered if f.category == category]
    if severity:
        filtered = [f for f in filtered if f.severity == severity]
    if status:
        filtered = [f for f in filtered if f.status == status]
    filtered = [f for f in filtered if f.confidence >= min_confidence]

    # Paginate
    page = filtered[offset : offset + limit]

    return [
        FindingResponse(
            id=f.id,
            claim=f.claim,
            evidence_count=f.evidence_count,
            confidence=f.confidence,
            confidence_level=f.confidence_level.value,
            status=f.status.value,
            category=f.category.value,
            severity=f.severity.value,
            source_files=f.source_files,
            reasoning=f.reasoning,
            created_by=f.created_by,
        )
        for f in page
    ]


@router.get("/{finding_id}")
async def get_finding(finding_id: str) -> dict:
    """Get a specific finding with full evidence."""
    for f in _findings_store:
        if f.id == finding_id:
            return f.model_dump()
    raise HTTPException(status_code=404, detail="Finding not found")


@router.post("/{finding_id}/verify")
async def verify_finding(
    finding_id: str,
    accepted: bool,
    verified_by: str = "manual",
) -> dict:
    """Verify or reject a finding."""
    for f in _findings_store:
        if f.id == finding_id:
            f.verify(verified_by=verified_by, accepted=accepted)
            return f.model_dump()
    raise HTTPException(status_code=404, detail="Finding not found")


def add_finding(finding: Finding) -> None:
    """Add a finding to the store."""
    _findings_store.append(finding)


def clear_findings() -> None:
    """Clear all findings."""
    _findings_store.clear()
