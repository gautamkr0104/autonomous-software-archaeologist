"""Tests for the evidence model — the hallucination resistance layer."""

import pytest
from asa.core.evidence import (
    ConfidenceLevel,
    Evidence,
    EvidenceChain,
    EvidenceChainStep,
    Finding,
    FindingStatus,
)
from asa.core.types import EvidenceType, FindingCategory, FindingSeverity


class TestConfidenceLevel:
    def test_from_score_very_high(self):
        assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.VERY_HIGH

    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(0.80) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(0.60) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(0.30) == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        assert ConfidenceLevel.from_score(0.10) == ConfidenceLevel.VERY_LOW


class TestEvidence:
    def test_create_evidence(self):
        ev = Evidence(
            evidence_type=EvidenceType.AST_NODE,
            description="Class definition found",
            source_file="main.py",
            confidence=0.9,
        )
        assert ev.evidence_type == EvidenceType.AST_NODE
        assert ev.confidence == 0.9
        assert ev.source_file == "main.py"

    def test_evidence_str(self):
        ev = Evidence(
            evidence_type=EvidenceType.IMPORT_STATEMENT,
            description="import os",
            source_file="test.py",
            source_location={"line_start": 5},
        )
        s = str(ev)
        assert "import os" in s
        assert "test.py" in s

    def test_evidence_has_id(self):
        ev = Evidence(
            evidence_type=EvidenceType.STATIC_ANALYSIS,
            description="test",
        )
        assert ev.id  # UUID auto-generated


class TestFinding:
    def test_create_finding(self):
        finding = Finding(
            claim="Test claim",
            category=FindingCategory.ARCHITECTURE,
            severity=FindingSeverity.INFO,
        )
        assert finding.claim == "Test claim"
        assert finding.status == FindingStatus.PENDING
        assert finding.confidence == 0.0

    def test_add_evidence_updates_confidence(self):
        finding = Finding(claim="Test claim")
        ev = Evidence(
            evidence_type=EvidenceType.STATIC_ANALYSIS,
            description="test evidence",
            confidence=0.9,
        )
        finding.add_evidence(ev)
        assert finding.confidence > 0
        assert finding.evidence_count == 1

    def test_multiple_evidence_types_increase_confidence(self):
        finding = Finding(claim="Test claim")
        finding.add_evidence(Evidence(
            evidence_type=EvidenceType.AST_NODE,
            description="AST evidence",
            confidence=0.9,
        ))
        finding.add_evidence(Evidence(
            evidence_type=EvidenceType.IMPORT_STATEMENT,
            description="Import evidence",
            confidence=0.9,
        ))
        # More diverse evidence should give bonus
        assert finding.confidence >= 0.9

    def test_verify_accepted(self):
        finding = Finding(claim="Test claim")
        finding.verify("verifier", accepted=True)
        assert finding.status == FindingStatus.VERIFIED
        assert finding.verified_by == "verifier"
        assert finding.verified_at is not None

    def test_verify_rejected(self):
        finding = Finding(claim="Test claim")
        finding.verify("verifier", accepted=False)
        assert finding.status == FindingStatus.REJECTED

    def test_confidence_level_property(self):
        finding = Finding(claim="Test")
        finding.confidence = 0.85
        assert finding.confidence_level == ConfidenceLevel.HIGH

    def test_no_evidence_zero_confidence(self):
        finding = Finding(claim="Test")
        finding._recalculate_confidence()
        assert finding.confidence == 0.0


class TestEvidenceChain:
    def test_create_chain(self):
        chain = EvidenceChain(claim="A depends on B")
        chain.steps.append(EvidenceChainStep(
            step_number=1,
            description="A imports B",
            from_entity="A",
            to_entity="B",
            relationship="IMPORTS",
        ))
        assert len(chain.steps) == 1
        assert chain.steps[0].from_entity == "A"
