"""Verification Agent.

The Verification Agent has authority to:
  - downgrade confidence scores
  - reject findings without sufficient evidence
  - request additional evidence
  - validate evidence chains

This is the hallucination resistance layer.
"""

from __future__ import annotations

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding, FindingStatus
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class VerificationAgent(BaseAgent):
    """Critically inspects findings from other agents."""

    name = "verification"
    description = "Verifies findings, downgrades uncertain claims, rejects unsupported claims"

    # Minimum evidence requirements by severity
    MIN_EVIDENCE: dict[str, int] = {
        "critical": 3,
        "high": 2,
        "medium": 1,
        "low": 1,
        "info": 1,
    }

    MIN_CONFIDENCE = 0.3  # Below this, findings are rejected

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Verify all findings from other agents.

        Note: This agent receives findings passed externally, not from its own analysis.
        In the orchestrator, findings from all agents are collected and passed here.
        """
        # This agent is called by the orchestrator with all findings
        # For now, return empty — the orchestrator handles the verification loop
        return []

    def verify_findings(self, findings: list[Finding], trace: AgentTrace) -> list[Finding]:
        """Verify a collection of findings from other agents.

        Returns the same findings with updated status, confidence, and notes.
        """
        verified: list[Finding] = []

        for finding in findings:
            result = self._verify_single(finding, trace)
            verified.append(result)

        # Summary
        accepted = sum(1 for f in verified if f.status == FindingStatus.VERIFIED)
        rejected = sum(1 for f in verified if f.status == FindingStatus.REJECTED)
        uncertain = sum(1 for f in verified if f.status == FindingStatus.UNCERTAIN)

        trace.add_step("verification_complete", {
            "accepted": accepted,
            "rejected": rejected,
            "uncertain": uncertain,
        })

        self.logger.info(
            "verification.complete",
            total=len(findings),
            accepted=accepted,
            rejected=rejected,
            uncertain=uncertain,
        )

        return verified

    def _verify_single(self, finding: Finding, trace: AgentTrace) -> Finding:
        """Verify a single finding."""
        reasons: list[str] = []

        # Rule 1: Must have at least one piece of evidence
        if not finding.evidence:
            finding.status = FindingStatus.REJECTED
            finding.verified_by = self.name
            finding.reasoning += "\n[VERIFICATION] REJECTED: No evidence provided."
            trace.add_step("rejected", {"finding_id": finding.id, "reason": "no_evidence"})
            return finding

        # Rule 2: Check evidence type diversity
        evidence_types = {e.evidence_type for e in finding.evidence}
        has_static = EvidenceType.STATIC_ANALYSIS in evidence_types
        has_file = EvidenceType.FILE_PATH in evidence_types or EvidenceType.AST_NODE in evidence_types
        has_import = EvidenceType.IMPORT_STATEMENT in evidence_types or EvidenceType.IMPORT_STATEMENT in evidence_types

        # Rule 3: Minimum confidence check
        avg_evidence_confidence = sum(e.confidence for e in finding.evidence) / len(finding.evidence)

        if avg_evidence_confidence < self.MIN_CONFIDENCE:
            finding.confidence = avg_evidence_confidence * 0.5
            finding.status = FindingStatus.REJECTED
            finding.verified_by = self.name
            finding.reasoning += f"\n[VERIFICATION] REJECTED: Average evidence confidence too low ({avg_evidence_confidence:.2f})."
            trace.add_step("rejected", {"finding_id": finding.id, "reason": "low_confidence"})
            return finding

        # Rule 4: Check severity vs evidence count
        min_evidence = self.MIN_EVIDENCE.get(finding.severity.value, 1)
        if len(finding.evidence) < min_evidence:
            # Downgrade confidence
            penalty = 1.0 - (min_evidence - len(finding.evidence)) * 0.15
            finding.confidence *= max(penalty, 0.3)
            reasons.append(f"Insufficient evidence for {finding.severity.value} severity "
                         f"(has {len(finding.evidence)}, needs {min_evidence})")

        # Rule 5: LLM-only evidence should be treated with lower confidence
        llm_only = all(e.evidence_type == EvidenceType.LLM_REASONING for e in finding.evidence)
        if llm_only:
            finding.confidence *= 0.5
            finding.status = FindingStatus.UNCERTAIN
            reasons.append("Evidence is LLM-only — not machine-verifiable")
            trace.add_step("downgraded", {"finding_id": finding.id, "reason": "llm_only_evidence"})

        # Rule 6: Source file evidence is stronger
        has_source_files = any(e.source_file for e in finding.evidence)
        if not has_source_files:
            finding.confidence *= 0.8
            reasons.append("No source file references in evidence")

        # Rule 7: Content snippets add confidence
        has_snippets = any(e.content_snippet for e in finding.evidence)
        if has_snippets:
            finding.confidence = min(finding.confidence * 1.1, 1.0)

        # Apply findings
        if finding.status != FindingStatus.REJECTED:
            if finding.confidence >= 0.7:
                finding.status = FindingStatus.VERIFIED
            elif finding.confidence >= 0.4:
                finding.status = FindingStatus.UNCERTAIN
            else:
                finding.status = FindingStatus.REJECTED

        finding.verified_by = self.name

        if reasons:
            finding.reasoning += f"\n[VERIFICATION] {'; '.join(reasons)}"

        trace.add_step("verified", {
            "finding_id": finding.id,
            "status": finding.status.value,
            "confidence": finding.confidence,
        })

        return finding
