"""Evidence model — the cornerstone of ASA's hallucination resistance.

Every important conclusion must have:
  - claim
  - evidence
  - source files
  - source locations when available
  - reasoning
  - confidence score
  - analysis timestamp
  - analyzer/agent responsible
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from asa.core.types import EvidenceType, FindingCategory, FindingSeverity


class ConfidenceLevel(str, Enum):
    """Human-readable confidence levels mapped to numeric ranges."""

    VERY_HIGH = "very_high"  # 0.90 – 1.00
    HIGH = "high"            # 0.75 – 0.89
    MEDIUM = "medium"        # 0.50 – 0.74
    LOW = "low"              # 0.25 – 0.49
    VERY_LOW = "very_low"    # 0.00 – 0.24

    @classmethod
    def from_score(cls, score: float) -> ConfidenceLevel:
        if score >= 0.90:
            return cls.VERY_HIGH
        if score >= 0.75:
            return cls.HIGH
        if score >= 0.50:
            return cls.MEDIUM
        if score >= 0.25:
            return cls.LOW
        return cls.VERY_LOW


class Evidence(BaseModel):
    """A single piece of machine-verifiable evidence backing a claim."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evidence_type: EvidenceType
    description: str
    source_file: str | None = None
    source_location: dict[str, Any] | None = None  # SourceLocation serialised
    content_snippet: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collected_by: str = ""  # agent or analyzer name

    def __str__(self) -> str:
        loc = ""
        if self.source_file:
            loc = f" ({self.source_file}"
            if self.source_location:
                ls = self.source_location.get("line_start", "")
                loc += f":{ls}" if ls else ""
            loc += ")"
        return f"[{self.evidence_type.value}] {self.description}{loc}"


class FindingStatus(str, Enum):
    """Verification status of a finding."""

    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"
    PENDING = "pending"


class Finding(BaseModel):
    """An evidence-backed finding produced by an analysis agent.

    This is the primary output artifact of ASA.  Every finding links to
    concrete evidence so that claims can be audited by humans or by the
    Verification Agent.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: FindingStatus = FindingStatus.PENDING
    category: FindingCategory = FindingCategory.ARCHITECTURE
    severity: FindingSeverity = FindingSeverity.INFO

    # Provenance
    created_by: str = ""  # agent name
    verified_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: datetime | None = None

    # Source context
    source_files: list[str] = Field(default_factory=list)
    source_locations: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str = ""

    # Relations
    related_findings: list[str] = Field(default_factory=list)  # finding IDs
    tags: list[str] = Field(default_factory=list)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return ConfidenceLevel.from_score(self.confidence)

    @property
    def is_verified(self) -> bool:
        return self.status == FindingStatus.VERIFIED

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)
        self._recalculate_confidence()

    def verify(self, verified_by: str, accepted: bool) -> None:
        self.verified_by = verified_by
        self.verified_at = datetime.utcnow()
        self.status = FindingStatus.VERIFIED if accepted else FindingStatus.REJECTED

    def _recalculate_confidence(self) -> None:
        """Recalculate confidence based on evidence quality."""
        if not self.evidence:
            self.confidence = 0.0
            return
        # Weighted average: more evidence and higher individual confidence = higher overall
        scores = [e.confidence for e in self.evidence]
        base = sum(scores) / len(scores)
        # Bonus for multiple independent evidence sources
        unique_types = len({e.evidence_type for e in self.evidence})
        multiplier = min(1.0 + (unique_types - 1) * 0.05, 1.2)
        self.confidence = min(base * multiplier, 1.0)


class EvidenceChain(BaseModel):
    """An ordered chain of evidence tracing how a conclusion was reached.

    Example chain for "CheckoutService depends on PostgreSQL":
        CheckoutService → CheckoutRepository → SQLAlchemy → PostgreSQL config
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim: str
    steps: list[EvidenceChainStep] = Field(default_factory=list)
    final_confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceChainStep(BaseModel):
    """A single step in an evidence chain."""

    step_number: int
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    from_entity: str = ""
    to_entity: str = ""
    relationship: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
