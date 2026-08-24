"""Base agent class.

Every agent must operate using:
  - task
  - available evidence
  - tools
  - hypothesis
  - evidence collection
  - conclusion
  - confidence
  - verification

Implement maximum iteration limits, token budgets, timeouts, and cancellation.
"""

from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from asa.config.settings import Settings, get_settings
from asa.core.evidence import Evidence, EvidenceType, Finding, FindingStatus
from asa.core.logging import get_logger
from asa.core.models import ProjectAnalysis
from asa.core.types import (
    AgentStatus,
    FindingCategory,
    FindingSeverity,
)


class AgentTrace:
    """Stores the trace of an agent's reasoning for debugging."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.steps: list[dict[str, Any]] = []
        self.hypotheses: list[str] = []
        self.evidence_collected: list[Evidence] = []
        self.start_time = time.time()

    def add_step(self, step: str, details: dict[str, Any] | None = None) -> None:
        self.steps.append({
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed": round(time.time() - self.start_time, 2),
            **(details or {}),
        })

    def add_hypothesis(self, hypothesis: str) -> None:
        self.hypotheses.append(hypothesis)
        self.add_step("hypothesis", {"text": hypothesis})

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence_collected.append(evidence)
        self.add_step("evidence_collected", {"evidence_type": evidence.evidence_type.value})

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent_name,
            "steps": self.steps,
            "hypotheses": self.hypotheses,
            "evidence_count": len(self.evidence_collected),
            "duration": round(time.time() - self.start_time, 2),
        }


class BaseAgent(ABC):
    """Abstract base class for all analysis agents."""

    name: str = "base"
    description: str = ""
    max_iterations: int = 10
    timeout_seconds: int = 300

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = get_logger(f"asa.agent.{self.name}")

    async def run(self, project: ProjectAnalysis) -> list[Finding]:
        """Execute the agent with lifecycle management.

        Returns a list of verified findings produced by this agent.
        """
        trace = AgentTrace(self.name)
        status = AgentStatus.RUNNING
        findings: list[Finding] = []

        self.logger.info("agent.start", name=self.name, repo=project.repository.name)
        trace.add_step("started")

        try:
            # Check timeout budget
            start = time.time()

            findings = await self._execute(project, trace)

            elapsed = time.time() - start
            if elapsed > self.timeout_seconds:
                status = AgentStatus.TIMEOUT
                self.logger.warning("agent.timeout", name=self.name, elapsed=f"{elapsed:.1f}s")
            else:
                status = AgentStatus.COMPLETED

            trace.add_step("completed", {
                "findings_count": len(findings),
                "status": status.value,
            })

        except Exception as e:
            status = AgentStatus.FAILED
            self.logger.error("agent.error", name=self.name, error=str(e))
            trace.add_step("failed", {"error": str(e), "traceback": traceback.format_exc()})

        self.logger.info(
            "agent.complete",
            name=self.name,
            status=status.value,
            findings=len(findings),
        )

        return findings

    @abstractmethod
    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Core agent logic — must be implemented by subclasses."""
        ...

    def _create_finding(
        self,
        claim: str,
        evidence: list[Evidence],
        category: FindingCategory = FindingCategory.ARCHITECTURE,
        severity: FindingSeverity = FindingSeverity.INFO,
        reasoning: str = "",
        source_files: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Finding:
        """Create a finding with proper confidence calculation."""
        finding = Finding(
            claim=claim,
            category=category,
            severity=severity,
            reasoning=reasoning,
            created_by=self.name,
            source_files=source_files or [],
            tags=tags or [],
            status=FindingStatus.PENDING,
        )
        for ev in evidence:
            finding.add_evidence(ev)
        return finding

    def _create_evidence(
        self,
        evidence_type: EvidenceType,
        description: str,
        source_file: str | None = None,
        line: int | None = None,
        confidence: float = 1.0,
        content_snippet: str | None = None,
    ) -> Evidence:
        """Create a single piece of evidence."""
        location = None
        if source_file and line:
            location = {"file_path": source_file, "line_start": line}

        return Evidence(
            evidence_type=evidence_type,
            description=description,
            source_file=source_file,
            source_location=location,
            confidence=confidence,
            collected_by=self.name,
            content_snippet=content_snippet,
        )
