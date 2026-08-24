"""Performance Agent.

Identifies potential performance bottlenecks using static evidence.
Never fabricates runtime observations.
"""

from __future__ import annotations

import os
import re
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


PERFORMANCE_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "n_plus_one_import",
        "pattern": r"""^import\s+.*\n(?:.*\n)*?.*import\s+""",
        "severity": FindingSeverity.LOW,
        "description": "Multiple sequential imports may indicate missing __init__.py aggregation",
        "confidence": 0.4,
    },
    {
        "name": "nested_loops",
        "pattern": r"""for\s+\w+\s+in\s+.*:\s*\n\s+for\s+\w+\s+in""",
        "severity": FindingSeverity.MEDIUM,
        "description": "Nested loops may indicate O(n²) complexity",
        "confidence": 0.6,
    },
    {
        "name": "global_mutable",
        "pattern": r"""^[A-Z_]+\s*=\s*\[\]|^[A-Z_]+\s*=\s*\{\}""",
        "severity": FindingSeverity.LOW,
        "description": "Global mutable state can cause concurrency issues",
        "confidence": 0.5,
    },
    {
        "name": "synchronous_io_in_async",
        "pattern": r"""(?:async\s+def|await).*\b(?:open|read|write|request)\b(?![\s\S]*await)""",
        "severity": FindingSeverity.MEDIUM,
        "description": "Potential synchronous I/O in async context",
        "confidence": 0.4,
    },
]


class PerformanceAgent(BaseAgent):
    """Identifies potential performance concerns from static analysis."""

    name = "performance"
    description = "Identifies potential performance bottlenecks"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        findings.extend(self._scan_patterns(project, trace))
        findings.extend(self._analyze_complexity(project, trace))
        findings.extend(self._check_large_files(project, trace))

        return findings

    def _scan_patterns(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Scan for performance anti-patterns."""
        findings: list[Finding] = []

        for fa in project.file_analyses:
            if fa.is_test:
                continue

            try:
                file_path = os.path.join(project.repository.local_path, fa.file_path)
                if not os.path.exists(file_path):
                    continue
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue

            for pattern_def in PERFORMANCE_PATTERNS:
                try:
                    matches = list(re.finditer(pattern_def["pattern"], content, re.MULTILINE))
                except re.error:
                    continue

                for match in matches[:3]:  # Limit per pattern per file
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append(self._create_finding(
                        claim=f"{pattern_def['description']} in {fa.file_path}",
                        evidence=[
                            self._create_evidence(
                                EvidenceType.STATIC_ANALYSIS,
                                f"Performance pattern: {pattern_def['name']}",
                                source_file=fa.file_path,
                                line=line_num,
                                confidence=pattern_def["confidence"],
                            )
                        ],
                        category=FindingCategory.PERFORMANCE,
                        severity=pattern_def["severity"],
                        reasoning=f"Static analysis pattern match for {pattern_def['name']}.",
                        source_files=[fa.file_path],
                        tags=["performance", pattern_def["name"]],
                    ))

        return findings

    def _analyze_complexity(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze complexity metrics."""
        findings: list[Finding] = []

        # Find the most complex files (by function count as proxy)
        file_complexity: list[tuple[str, int]] = []
        for fa in project.file_analyses:
            # Estimate complexity by nesting levels, branches, etc.
            func_count = len(fa.functions)
            class_count = len(fa.classes)
            total_symbols = func_count + class_count
            if total_symbols > 0:
                file_complexity.append((fa.file_path, total_symbols))

        file_complexity.sort(key=lambda x: -x[1])

        if file_complexity and file_complexity[0][1] > 20:
            findings.append(self._create_finding(
                claim=f"Most complex file: {file_complexity[0][0]} "
                      f"({file_complexity[0][1]} symbols)",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Top complex files: {', '.join(f'{p} ({s})' for p, s in file_complexity[:5])}",
                        confidence=0.7,
                    )
                ],
                category=FindingCategory.COMPLEXITY,
                severity=FindingSeverity.MEDIUM,
                reasoning="High symbol count suggests complex file that may benefit from decomposition.",
                tags=["complexity", "large-files"],
            ))

        return findings

    def _check_large_files(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Check for unusually large files."""
        findings: list[Finding] = []

        large_files = [
            fa for fa in project.file_analyses
            if fa.lines_of_code > 500
        ]

        if large_files:
            large_files.sort(key=lambda f: -f.lines_of_code)
            findings.append(self._create_finding(
                claim=f"Found {len(large_files)} file(s) with >500 lines of code",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Large files: {', '.join(f'{f.file_path} ({f.lines_of_code} LOC)' for f in large_files[:5])}",
                        confidence=0.95,
                    )
                ],
                category=FindingCategory.COMPLEXITY,
                severity=FindingSeverity.LOW,
                reasoning="Large files are harder to maintain and test.",
                tags=["large-files", "maintainability"],
            ))

        return findings
