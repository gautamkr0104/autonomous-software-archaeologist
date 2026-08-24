"""Architecture Agent.

Infers architectural components and boundaries by analyzing:
  - Module structure
  - Dependency directions
  - Coupling patterns
  - Component boundaries
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from asa.agents.base import AgentTrace, BaseAgent
from asa.core.evidence import Evidence, EvidenceType, Finding
from asa.core.models import ProjectAnalysis
from asa.core.types import FindingCategory, FindingSeverity


class ArchitectureAgent(BaseAgent):
    """Infers architectural components and boundaries."""

    name = "architecture"
    description = "Analyzes architectural structure, boundaries, and patterns"

    async def _execute(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        findings: list[Finding] = []

        # 1. Module structure analysis
        findings.extend(self._analyze_modules(project, trace))

        # 2. Dependency direction analysis
        findings.extend(self._analyze_dependency_direction(project, trace))

        # 3. Coupling analysis
        findings.extend(self._analyze_coupling(project, trace))

        # 4. Layer detection
        findings.extend(self._detect_layers(project, trace))

        # 5. Entry points
        findings.extend(self._find_entry_points(project, trace))

        # 6. Architectural patterns
        findings.extend(self._detect_patterns(project, trace))

        return findings

    def _analyze_modules(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze the module structure."""
        findings: list[Finding] = []

        if not project.modules:
            return findings

        # Module size distribution
        module_sizes = {m.name: len(m.files) for m in project.modules}
        large_modules = {k: v for k, v in module_sizes.items() if v > 10}

        if large_modules:
            findings.append(self._create_finding(
                claim=f"Found {len(large_modules)} large modules (>10 files) that may need decomposition",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Large modules: {', '.join(f'{k} ({v} files)' for k, v in sorted(large_modules.items(), key=lambda x: -x[1])[:5])}",
                        confidence=0.85,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.MEDIUM,
                reasoning="Large modules may indicate high coupling or need for decomposition.",
                tags=["modules", "decomposition"],
            ))
            trace.add_hypothesis(f"Found {len(large_modules)} potentially oversized modules")

        # Submodule hierarchy
        root_modules = [m for m in project.modules if not any(
            m.name.startswith(other.name + ".")
            for other in project.modules
            if other != m
        )]

        if len(root_modules) > 1:
            findings.append(self._create_finding(
                claim=f"Repository has {len(root_modules)} top-level modules, "
                      f"suggesting a {'distributed' if len(root_modules) > 3 else 'modular'} architecture",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Top-level modules: {', '.join(m.name for m in root_modules[:10])}",
                        confidence=0.7,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Number and naming of top-level modules suggests architectural style.",
                tags=["architecture-style"],
            ))

        return findings

    def _analyze_dependency_direction(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze whether dependencies flow in a consistent direction."""
        findings: list[Finding] = []

        graph = project.dependency_graph
        if not graph.nodes or not graph.edges:
            return findings

        # Count cross-module imports
        module_imports: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for edge in graph.edges:
            if edge.relationship.value == "IMPORTS":
                src = edge.source_id.split(":")[1] if ":" in edge.source_id else ""
                tgt = edge.target_id.split(":")[1] if ":" in edge.target_id else ""
                if src and tgt:
                    src_mod = os.path.dirname(src)
                    tgt_mod = os.path.dirname(tgt)
                    if src_mod != tgt_mod:
                        module_imports[src_mod][tgt_mod] += 1

        # Check for circular dependencies
        if module_imports:
            circular = []
            for mod_a, targets in module_imports.items():
                for mod_b in targets:
                    if mod_b in module_imports and mod_a in module_imports[mod_b]:
                        pair = tuple(sorted([mod_a, mod_b]))
                        if pair not in circular:
                            circular.append(pair)

            if circular:
                findings.append(self._create_finding(
                    claim=f"Detected {len(circular)} potential circular module dependencies",
                    evidence=[
                        self._create_evidence(
                            EvidenceType.IMPORT_STATEMENT,
                            f"Circular: {a} ↔ {b}",
                            confidence=0.8,
                        )
                        for a, b in circular[:5]
                    ],
                    category=FindingCategory.ARCHITECTURE,
                    severity=FindingSeverity.HIGH,
                    reasoning="Circular dependencies indicate architectural boundary violations.",
                    tags=["circular-dependency", "architecture"],
                ))
                trace.add_hypothesis(f"Found {len(circular)} circular dependencies")

        return findings

    def _analyze_coupling(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Analyze coupling between components."""
        findings: list[Finding] = []

        graph = project.dependency_graph

        # Find highly coupled files (high fan-in + high fan-out)
        coupling_scores: dict[str, int] = {}
        for node_id in graph.nodes:
            fan_in = graph.fan_in(node_id)
            fan_out = graph.fan_out(node_id)
            coupling_scores[node_id] = fan_in + fan_out

        # Most coupled nodes
        most_coupled = sorted(coupling_scores.items(), key=lambda x: -x[1])[:5]
        if most_coupled and most_coupled[0][1] > 10:
            findings.append(self._create_finding(
                claim=f"Most coupled component: {most_coupled[0][0]} "
                      f"(coupling score: {most_coupled[0][1]})",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Top coupled: {', '.join(f'{n} (score={s})' for n, s in most_coupled)}",
                        confidence=0.85,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                severity=FindingSeverity.MEDIUM,
                reasoning="High coupling indicates components that are hard to modify independently.",
                tags=["coupling", "maintainability"],
            ))

        return findings

    def _detect_layers(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Detect architectural layers."""
        findings: list[Finding] = []

        # Check for common layer patterns
        layer_indicators = {
            "api": ["route", "controller", "handler", "view", "endpoint"],
            "service": ["service", "usecase", "business", "logic"],
            "repository": ["repository", "dao", "data", "model", "entity"],
            "infrastructure": ["infra", "config", "util", "helper", "adapter"],
        }

        detected_layers: dict[str, list[str]] = defaultdict(list)

        for fa in project.file_analyses:
            path_lower = fa.file_path.lower()
            for layer, keywords in layer_indicators.items():
                if any(kw in path_lower for kw in keywords):
                    detected_layers[layer].append(fa.file_path)

        if len(detected_layers) >= 3:
            findings.append(self._create_finding(
                claim=f"Detected {len(detected_layers)} architectural layers: "
                      f"{', '.join(detected_layers.keys())}",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Layer '{layer}': {len(files)} files",
                        confidence=0.6,
                    )
                    for layer, files in detected_layers.items()
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Layer detection based on file naming conventions and directory structure.",
                tags=["layers", "architecture-style"],
            ))

        return findings

    def _find_entry_points(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Find application entry points."""
        findings: list[Finding] = []

        entry_patterns = [
            "main.py", "app.py", "server.py", "index.py",
            "main.js", "index.js", "server.js", "app.js",
            "main.ts", "index.ts", "server.ts", "app.ts",
            "__main__.py", "manage.py", "wsgi.py", "asgi.py",
        ]

        entry_points: list[str] = []
        for fa in project.file_analyses:
            basename = os.path.basename(fa.file_path)
            if basename in entry_patterns:
                entry_points.append(fa.file_path)

        # Also check for files with main functions
        for fa in project.file_analyses:
            for func in fa.functions:
                if func.name == "main" or func.name == "__main__":
                    entry_points.append(f"{fa.file_path}:{func.name}")

        if entry_points:
            findings.append(self._create_finding(
                claim=f"Found {len(entry_points)} application entry point(s)",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        f"Entry point: {ep}",
                        source_file=ep.split(":")[0],
                        confidence=0.9,
                    )
                    for ep in entry_points[:10]
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Entry points identified by file name conventions and main function detection.",
                tags=["entry-points"],
            ))

        return findings

    def _detect_patterns(
        self, project: ProjectAnalysis, trace: AgentTrace,
    ) -> list[Finding]:
        """Detect architectural patterns."""
        findings: list[Finding] = []

        # Check for MVC pattern
        has_controllers = any("controller" in fa.file_path.lower() for fa in project.file_analyses)
        has_models = any("model" in fa.file_path.lower() for fa in project.file_analyses)
        has_views = any("view" in fa.file_path.lower() or "template" in fa.file_path.lower()
                       for fa in project.file_analyses)

        if has_controllers and has_models:
            findings.append(self._create_finding(
                claim="Repository appears to follow MVC (Model-View-Controller) pattern",
                evidence=[
                    self._create_evidence(
                        EvidenceType.STATIC_ANALYSIS,
                        "Detected controller, model, and view components",
                        confidence=0.6,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="MVC pattern detected from naming conventions in file paths.",
                tags=["pattern", "mvc"],
            ))

        # Check for microservices indicators
        service_indicators = ["docker-compose", "kubernetes", "k8s", "helm"]
        has_service_infra = any(
            any(ind in fa.file_path.lower() for ind in service_indicators)
            for fa in project.file_analyses
        )
        docker_files = [fa for fa in project.file_analyses
                       if "dockerfile" in os.path.basename(fa.file_path).lower()
                       or "docker-compose" in fa.file_path.lower()]

        if len(docker_files) > 2:
            findings.append(self._create_finding(
                claim=f"Repository contains {len(docker_files)} Docker files, "
                      f"suggesting a microservices or containerized architecture",
                evidence=[
                    self._create_evidence(
                        EvidenceType.CONFIGURATION_VALUE,
                        f"Docker files: {', '.join(f.file_path for f in docker_files[:5])}",
                        confidence=0.75,
                    )
                ],
                category=FindingCategory.ARCHITECTURE,
                reasoning="Multiple Dockerfiles suggest separate deployable services.",
                tags=["pattern", "microservices", "containers"],
            ))

        return findings
