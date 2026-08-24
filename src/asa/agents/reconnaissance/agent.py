"""Reconnaissance Agent.

Determines what the repository contains:
  - Languages and frameworks
  - Package managers
  - Entry points
  - Build system
  - Configuration files
  - Test infrastructure
"""

from __future__ import annotations

import os
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class ReconnaissanceAgent(BaseAgent):
    """Analyzes what a repository contains at a high level."""

    name = "reconnaissance"
    description = "Determines repository contents, languages, and structure"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []
        repo = project.repository

        # 1. Language distribution finding
        if repo.languages:
            evidence = [
                self._create_evidence(
                    EvidenceType.STATIC_ANALYSIS,
                    f"Language detection found: {', '.join(f'{k}: {v*100:.1f}%' for k, v in list(repo.languages.items())[:5])}",
                    confidence=0.95,
                )
            ]
            findings.append(self._create_finding(
                claim=f"Repository uses {len(repo.languages)} programming language(s), "
                      f"primarily {list(repo.languages.keys())[0] if repo.languages else 'unknown'}",
                evidence=evidence,
                category=FindingCategory.ARCHITECTURE,
                reasoning="Language detection based on file extension analysis across all source files.",
                tags=["languages", "reconnaissance"],
            ))
            trace.add_hypothesis(f"Primary language: {list(repo.languages.keys())[0]}")

        # 2. Framework detection
        if repo.frameworks:
            evidence = [
                self._create_evidence(
                    EvidenceType.STATIC_ANALYSIS,
                    f"Framework patterns detected: {', '.join(repo.frameworks)}",
                    confidence=0.8,
                )
            ]
            findings.append(self._create_finding(
                claim=f"Repository uses frameworks: {', '.join(repo.frameworks)}",
                evidence=evidence,
                category=FindingCategory.ARCHITECTURE,
                reasoning="Framework detection based on file patterns, imports, and configuration files.",
                tags=["frameworks", "reconnaissance"],
            ))

        # 3. Project size and complexity
        total_loc = sum(fa.lines_of_code for fa in project.file_analyses)
        total_classes = sum(len(fa.classes) for fa in project.file_analyses)
        total_functions = sum(len(fa.functions) for fa in project.file_analyses)

        evidence = [
            self._create_evidence(
                EvidenceType.STATIC_ANALYSIS,
                f"Total lines of code: {total_loc}",
                confidence=1.0,
            ),
            self._create_evidence(
                EvidenceType.STATIC_ANALYSIS,
                f"Total classes: {total_classes}, functions: {total_functions}",
                confidence=1.0,
            ),
        ]

        complexity = "small"
        if total_loc > 100_000:
            complexity = "very large"
        elif total_loc > 50_000:
            complexity = "large"
        elif total_loc > 10_000:
            complexity = "medium"

        findings.append(self._create_finding(
            claim=f"Repository is {complexity} with {total_loc:,} lines of code, "
                  f"{total_classes} classes, {total_functions} functions",
            evidence=evidence,
            category=FindingCategory.ARCHITECTURE,
            reasoning="Size classification based on total lines of code across all files.",
            tags=["size", "complexity", "reconnaissance"],
        ))

        # 4. Test infrastructure
        test_files = [fa for fa in project.file_analyses if fa.is_test]
        if test_files:
            evidence = [
                self._create_evidence(
                    EvidenceType.TEST_COVERAGE,
                    f"Found {len(test_files)} test files",
                    confidence=0.9,
                )
            ]
            findings.append(self._create_finding(
                claim=f"Repository has test infrastructure with {len(test_files)} test files",
                evidence=evidence,
                category=FindingCategory.ARCHITECTURE,
                reasoning="Test files identified by naming conventions and directory patterns.",
                tags=["testing", "reconnaissance"],
            ))

        # 5. Configuration complexity
        config_files = [fa for fa in project.file_analyses if fa.is_config]
        if config_files:
            findings.append(self._create_finding(
                claim=f"Repository has {len(config_files)} configuration files",
                evidence=[
                    self._create_evidence(
                        EvidenceType.CONFIGURATION_VALUE,
                        f"Configuration files: {', '.join(os.path.basename(f.file_path) for f in config_files[:10])}",
                        confidence=0.95,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                tags=["configuration", "reconnaissance"],
            ))

        # 6. External dependencies
        if project.external_dependencies:
            findings.append(self._create_finding(
                claim=f"Repository depends on {len(project.external_dependencies)} external packages",
                evidence=[
                    self._create_evidence(
                        EvidenceType.DEPENDENCY_DECLARATION,
                        f"External packages: {', '.join(d.name for d in project.external_dependencies[:20])}",
                        confidence=0.95,
                    )
                ],
                category=FindingCategory.DEPENDENCY,
                tags=["dependencies", "reconnaissance"],
            ))

        return findings
