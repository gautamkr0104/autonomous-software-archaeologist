"""Dependency Agent.

Analyzes coupling and dependency structure:
  - Internal dependency health
  - External dependency risk
  - Dependency centrality
  - Dependency volatility
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class DependencyAgent(BaseAgent):
    """Analyzes dependency structure and coupling."""

    name = "dependency"
    description = "Analyzes internal and external dependency structure"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        findings.extend(self._analyze_external_deps(project, trace))
        findings.extend(self._analyze_internal_deps(project, trace))
        findings.extend(self._analyze_dependency_health(project, trace))

        return findings

    def _analyze_external_deps(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze external dependencies."""
        findings: list[Finding] = []

        deps = project.external_dependencies
        if not deps:
            return findings

        # Count by source
        by_source: dict[str, list[str]] = defaultdict(list)
        for d in deps:
            by_source[d.source_file or "unknown"].append(d.name)

        # High external dependency count
        if len(deps) > 50:
            findings.append(self._create_finding(
                claim=f"Repository has {len(deps)} external dependencies, "
                      f"which may indicate high coupling to external libraries",
                evidence=[
                    self._create_evidence(
                        EvidenceType.DEPENDENCY_DECLARATION,
                        f"{len(deps)} dependencies from {', '.join(by_source.keys())}",
                        confidence=0.9,
                    )
                ],
                category=FindingCategory.DEPENDENCY,
                severity=FindingSeverity.MEDIUM,
                reasoning="High dependency count increases maintenance burden and supply chain risk.",
                tags=["external-dependencies", "supply-chain"],
            ))

        # Dev dependencies
        dev_deps = [d for d in deps if d.is_development]
        prod_deps = [d for d in deps if not d.is_development]
        if dev_deps and prod_deps:
            ratio = len(dev_deps) / len(deps)
            if ratio > 0.5:
                findings.append(self._create_finding(
                    claim=f"Development dependencies ({len(dev_deps)}) outnumber "
                          f"production dependencies ({len(prod_deps)}) — ratio: {ratio:.0%}",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.DEPENDENCY_DECLARATION,
                            f"Dev deps: {', '.join(d.name for d in dev_deps[:10])}",
                            confidence=0.8,
                        )
                    ],
                    category=FindingCategory.DEPENDENCY,
                    severity=FindingSeverity.LOW,
                    reasoning="High dev dependency ratio may indicate heavy tooling.",
                    tags=["dependency-ratio"],
                ))

        return findings

    def _analyze_internal_deps(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze internal dependency structure."""
        findings: list[Finding] = []

        graph = project.dependency_graph
        if not graph.nodes:
            return findings

        # Find highly depended-upon files (high fan-in)
        fan_in_map: dict[str, int] = {}
        for node_id in graph.nodes:
            fan_in_map[node_id] = graph.fan_in(node_id)

        most_depended = sorted(fan_in_map.items(), key=lambda x: -x[1])[:10]

        if most_depended and most_depended[0][1] > 5:
            findings.append(self._create_finding(
                claim=f"Most depended-upon file: {most_depended[0][0]} "
                      f"(referenced by {most_depended[0][1]} other components)",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Top depended-upon: {', '.join(f'{n} ({c} refs)' for n, c in most_depended[:5])}",
                        confidence=0.9,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Files with high fan-in are critical components that affect many others.",
                tags=["fan-in", "critical-components"],
            ))
            trace.add_hypothesis(f"Found critical component: {most_depended[0][0]}")

        # Find files that depend on many others (high fan-out)
        fan_out_map: dict[str, int] = {}
        for node_id in graph.nodes:
            fan_out_map[node_id] = graph.fan_out(node_id)

        most_dependent = sorted(fan_out_map.items(), key=lambda x: -x[1])[:10]

        if most_dependent and most_dependent[0][1] > 10:
            findings.append(self._create_finding(
                claim=f"Most dependent file: {most_dependent[0][0]} "
                      f"(depends on {most_dependent[0][1]} other components)",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Top dependent: {', '.join(f'{n} ({c} deps)' for n, c in most_dependent[:5])}",
                        confidence=0.9,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.MEDIUM,
                reasoning="Files with high fan-out are fragile — changes to dependencies can cascade.",
                tags=["fan-out", "fragile-components"],
            ))

        return findings

    def _analyze_dependency_health(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze overall dependency health."""
        findings: list[Finding] = []

        graph = project.dependency_graph

        # Check for orphaned files (no imports, not imported)
        if graph.nodes:
            orphans = []
            for node_id, attrs in graph.nodes.items():
                if attrs.get("type") == "File":
                    if graph.fan_in(node_id) == 0 and graph.fan_out(node_id) == 0:
                        orphans.append(node_id)

            if orphans and len(orphans) < 20:
                findings.append(self._create_finding(
                    claim=f"Found {len(orphans)} orphaned file(s) with no detected dependencies",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.STATIC_ANALYSIS,
                            f"Orphans: {', '.join(o.replace('file:', '') for o in orphans[:10])}",
                            confidence=0.6,
                        )
                    ],
                    category=FindingCategory.ARCHITECTURE,
                    severity=FindingSeverity.LOW,
                    reasoning="Orphaned files may be dead code or have undetected dynamic dependencies.",
                    tags=["orphans", "dead-code"],
                ))

        return findings
