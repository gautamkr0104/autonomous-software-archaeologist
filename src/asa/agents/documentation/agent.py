"""Documentation Agent.

Generates documentation based only on verified repository evidence.
Does not fabricate information.
"""

from __future__ import annotations

import os
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class DocumentationAgent(BaseAgent):
    """Generates documentation findings based on repository evidence."""

    name = "documentation"
    description = "Analyzes and generates documentation based on verified evidence"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        findings.extend(self._check_readme(project, trace))
        findings.extend(self._check_docstrings(project, trace))
        findings.extend(self._check_api_docs(project, trace))

        return findings

    def _check_readme(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check README quality."""
        findings: list[Finding] = []

        has_readme = False
        readme_path = None
        for name in ["README.md", "README.rst", "README.txt", "README"]:
            path = os.path.join(project.repository.local_path, name)
            if os.path.exists(path):
                has_readme = True
                readme_path = name
                break

        if has_readme:
            findings.append(self._create_finding(
                claim=f"Repository has a README file ({readme_path})",
                evidence=[
                    self._create_evidence(
                        EvidenceType.FILE_PATH,
                        f"README found at {readme_path}",
                        source_file=readme_path,
                        confidence=1.0,
                    )
                ],
                category=FindingCategory.DOCUMENTATION,
                reasoning="README presence confirmed by file system check.",
                tags=["readme", "documentation"],
            ))
        else:
            findings.append(self._create_finding(
                claim="Repository is missing a README file",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        "No README.md, README.rst, README.txt, or README found",
                        confidence=1.0,
                    )
                ],
                category=FindingCategory.DOCUMENTATION,
                severity=FindingSeverity.MEDIUM,
                reasoning="Standard documentation file not found.",
                tags=["readme", "missing-docs"],
            ))

        return findings

    def _check_docstrings(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check docstring coverage."""
        findings: list[Finding] = []

        total_classes = 0
        documented_classes = 0
        total_functions = 0
        documented_functions = 0

        for fa in project.file_analyses:
            for cls in fa.classes:
                total_classes += 1
                if cls.docstring:
                    documented_classes += 1

            for func in fa.functions:
                total_functions += 1
                if func.docstring:
                    documented_functions += 1

        total_symbols = total_classes + total_functions
        documented = documented_classes + documented_functions

        if total_symbols > 0:
            coverage = documented / total_symbols
            findings.append(self._create_finding(
                claim=f"Docstring coverage: {documented}/{total_symbols} symbols "
                      f"({coverage:.0%}) have documentation",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Classes: {documented_classes}/{total_classes} documented, "
                        f"Functions: {documented_functions}/{total_functions} documented",
                        confidence=0.95,
                    )
                ],
                category=FindingCategory.DOCUMENTATION,
                severity=FindingSeverity.INFO if coverage > 0.3 else FindingSeverity.LOW,
                reasoning="Docstring coverage measured by checking for non-empty docstrings on classes and functions.",
                tags=["docstrings", "documentation-coverage"],
            ))

        return findings

    def _check_api_docs(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check for API documentation."""
        findings: list[Finding] = []

        # Look for API documentation files
        api_doc_patterns = [
            "docs/", "doc/", "documentation/",
            "openapi", "swagger", "api-doc",
            "CHANGELOG", "CONTRIBUTING", "LICENSE",
        ]

        doc_files: list[str] = []
        for fa in project.file_analyses:
            path_lower = fa.file_path.lower()
            for pattern in api_doc_patterns:
                if pattern in path_lower:
                    doc_files.append(fa.file_path)
                    break

        if doc_files:
            findings.append(self._create_finding(
                claim=f"Repository has {len(doc_files)} documentation-related files",
                evidence=[
                    self._create_evidence(
                        EvidenceType.FILE_PATH,
                        f"Doc files: {', '.join(doc_files[:10])}",
                        confidence=0.9,
                    )
                ],
                category=FindingCategory.DOCUMENTATION,
                reasoning="Documentation files identified by path patterns.",
                tags=["api-docs", "documentation"],
            ))

        return findings
