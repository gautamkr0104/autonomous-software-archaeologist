"""History Agent.

Analyzes how architecture changed across Git history:
  - Major architectural changes
  - Dependency volatility
  - Code churn
  - Contributors patterns
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class HistoryAgent(BaseAgent):
    """Analyzes repository evolution and architectural changes over time."""

    name = "history"
    description = "Analyzes git history for architectural evolution patterns"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        findings.extend(self._analyze_commit_patterns(project, trace))
        findings.extend(self._analyze_contributors(project, trace))
        findings.extend(self._analyze_churn(project, trace))

        return findings

    def _analyze_commit_patterns(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze commit patterns and repository age."""
        findings: list[Finding] = []
        history = project.git_history

        if not history.commits:
            return findings

        # Repository age
        first = history.commits[-1].date if history.commits else None
        last = history.commits[0].date if history.commits else None

        if first and last:
            age_days = (last - first).days
            findings.append(self._create_finding(
                claim=f"Repository has {len(history.commits)} commits spanning {age_days} days "
                      f"(~{age_days // 365} years)",
                evidence=[
                    self._create_evidence(
                        EvidenceType.GIT_COMMIT,
                        f"First commit: {first.isoformat()}, Last: {last.isoformat()}",
                        confidence=1.0,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Repository age and commit density indicate project maturity.",
                tags=["history", "maturity"],
            ))

        # Commit size distribution
        if history.commits:
            sizes = [c.insertions + c.deletions for c in history.commits]
            avg_size = sum(sizes) / len(sizes)
            large_commits = sum(1 for s in sizes if s > 500)

            if large_commits > 0:
                findings.append(self._create_finding(
                    claim=f"{large_commits} commits changed >500 lines "
                          f"(avg commit size: {avg_size:.0f} lines)",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.GIT_COMMIT,
                            f"Large commits: {large_commits}/{len(history.commits)}",
                            confidence=0.9,
                        )
                    ],
                    category=FindingCategory.ARCHITECTURE,
                    severity=FindingSeverity.LOW,
                    reasoning="Large commits may indicate architectural changes or refactoring.",
                    tags=["commit-patterns"],
                ))

        return findings

    def _analyze_contributors(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze contributor distribution."""
        findings: list[Finding] = []
        history = project.git_history

        if not history.contributors:
            return findings

        total_commits = sum(history.contributors.values())
        top_contributor = max(history.contributors.items(), key=lambda x: x[1])

        # Bus factor estimation
        sorted_contributors = sorted(history.contributors.items(), key=lambda x: -x[1])
        cumulative = 0
        bus_factor = 0
        for name, count in sorted_contributors:
            cumulative += count
            bus_factor += 1
            if cumulative >= total_commits * 0.5:
                break

        if bus_factor <= 2 and len(history.contributors) > 2:
            findings.append(self._create_finding(
                claim=f"Low bus factor ({bus_factor}) — top contributor '{top_contributor[0]}' "
                      f"owns {top_contributor[1]}/{total_commits} commits ({top_contributor[1]/total_commits:.0%})",
                evidence=[
                    self._create_evidence(
                        EvidenceType.GIT_COMMIT,
                        f"Contributors: {len(history.contributors)}, "
                        f"bus factor: {bus_factor}",
                        confidence=0.8,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.MEDIUM,
                reasoning="Low bus factor indicates knowledge concentration risk.",
                tags=["bus-factor", "contributors"],
            ))
            trace.add_hypothesis(f"Bus factor: {bus_factor}")

        return findings

    def _analyze_churn(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze code churn patterns."""
        findings: list[Finding] = []
        history = project.git_history

        if not history.commits:
            return findings

        # File churn analysis
        file_churn: dict[str, int] = defaultdict(int)
        for commit in history.commits:
            for f in commit.files_changed:
                file_churn[f] += 1

        if file_churn:
            high_churn = {f: c for f, c in file_churn.items() if c > 10}

            if high_churn:
                top_churn = sorted(high_churn.items(), key=lambda x: -x[1])[:5]
                findings.append(self._create_finding(
                    claim=f"High-churn files ({len(high_churn)} files changed >10 times) "
                          f"— may indicate architectural hotspots",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.GIT_COMMIT,
                            f"High churn: {', '.join(f'{os.path.basename(f)} ({c}x)' for f, c in top_churn)}",
                            confidence=0.8,
                        )
                    ],
                    category=FindingCategory.ARCHITECTURE,
                    severity=FindingSeverity.MEDIUM,
                    reasoning="High-churn files are often architectural hotspots or areas of instability.",
                    tags=["churn", "hotspots"],
                ))

        return findings
