"""Dependency graph builder.

Constructs a comprehensive dependency graph from file analyses.
Every edge contains provenance (source file, line number).
"""

from __future__ import annotations

import os
from typing import Any

import networkx as nx

from asa.core.logging import get_logger
from asa.core.models import (
    DependencyEdge,
    DependencyGraph,
    FileAnalysis,
    ImportInfo,
    ModuleInfo,
    ProjectAnalysis,
    RepositoryInfo,
    SourceLocation,
)
from asa.core.types import NodeType, RelationshipType

logger = get_logger("asa.graph")


class DependencyGraphBuilder:
    """Constructs the dependency graph from analysis results."""

    def __init__(self) -> None:
        self.graph = DependencyGraph()
        self._file_id_map: dict[str, str] = {}  # file_path -> node_id
        self._module_id_map: dict[str, str] = {}  # module_name -> node_id
        self._symbol_id_map: dict[str, str] = {}  # qualified_name -> node_id

    def build(self, analysis: ProjectAnalysis) -> DependencyGraph:
        """Build the complete dependency graph from a project analysis."""
        logger.info("graph.build.start", files=len(analysis.file_analyses))

        # Phase 1: Add file nodes
        for fa in analysis.file_analyses:
            self._add_file_node(fa)

        # Phase 2: Add module nodes
        for mod in analysis.modules:
            self._add_module_node(mod)

        # Phase 3: Add import relationships
        for fa in analysis.file_analyses:
            self._add_import_edges(fa, analysis)

        # Phase 4: Add function call relationships
        for fa in analysis.file_analyses:
            self._add_call_edges(fa, analysis)

        # Phase 5: Add class inheritance relationships
        for fa in analysis.file_analyses:
            self._add_inheritance_edges(fa, analysis)

        # Phase 6: Add test relationships
        for fa in analysis.file_analyses:
            if fa.is_test:
                self._add_test_edges(fa, analysis)

        # Phase 7: Add containment relationships (file -> module)
        for mod in analysis.modules:
            self._add_containment_edges(mod)

        logger.info(
            "graph.build.complete",
            nodes=len(self.graph.nodes),
            edges=len(self.graph.edges),
        )

        return self.graph

    def get_networkx_graph(self) -> nx.DiGraph:
        """Convert to a NetworkX directed graph for algorithmic analysis."""
        G = nx.DiGraph()
        for node_id, attrs in self.graph.nodes.items():
            G.add_node(node_id, **attrs)
        for edge in self.graph.edges:
            G.add_edge(
                edge.source_id,
                edge.target_id,
                relationship=edge.relationship.value,
                confidence=edge.confidence,
                evidence=edge.evidence_description,
            )
        return G

    def calculate_metrics(self) -> dict[str, Any]:
        """Calculate graph metrics."""
        G = self.get_networkx_graph()
        metrics: dict[str, Any] = {}

        if not G.nodes:
            return metrics

        # Fan-in / fan-out
        fan_in = {n: G.in_degree(n) for n in G.nodes}
        fan_out = {n: G.out_degree(n) for n in G.nodes}
        metrics["avg_fan_in"] = sum(fan_in.values()) / len(fan_in) if fan_in else 0
        metrics["avg_fan_out"] = sum(fan_out.values()) / len(fan_out) if fan_out else 0
        metrics["max_fan_in"] = max(fan_in.values()) if fan_in else 0
        metrics["max_fan_out"] = max(fan_out.values()) if fan_out else 0

        # Most depended-upon nodes (highest fan-in)
        metrics["most_depended_upon"] = sorted(
            fan_in.items(), key=lambda x: -x[1]
        )[:10]

        # Most dependent nodes (highest fan-out)
        metrics["most_dependent"] = sorted(
            fan_out.items(), key=lambda x: -x[1]
        )[:10]

        # Connected components
        try:
            metrics["connected_components"] = nx.number_weakly_connected_components(G)
        except Exception:
            metrics["connected_components"] = 0

        # Cycles
        try:
            cycles = list(nx.simple_cycles(G))
            metrics["cycle_count"] = len(cycles)
            metrics["cycles"] = [[n for n in c[:5]] for c in cycles[:10]]
        except Exception:
            metrics["cycle_count"] = 0
            metrics["cycles"] = []

        # Centrality
        try:
            betweenness = nx.betweenness_centrality(G)
            metrics["highest_centrality"] = sorted(
                betweenness.items(), key=lambda x: -x[1]
            )[:10]
        except Exception:
            metrics["highest_centrality"] = []

        metrics["total_nodes"] = len(G.nodes)
        metrics["total_edges"] = len(G.edges)
        metrics["density"] = nx.density(G) if len(G.nodes) > 1 else 0

        return metrics

    def _add_file_node(self, fa: FileAnalysis) -> str:
        """Add a file as a node."""
        node_id = f"file:{fa.file_path}"
        self._file_id_map[fa.file_path] = node_id
        self.graph.add_node(
            node_id,
            NodeType.FILE,
            name=os.path.basename(fa.file_path),
            path=fa.file_path,
            language=fa.language,
            is_test=fa.is_test,
            is_config=fa.is_config,
            lines_of_code=fa.lines_of_code,
            classes=len(fa.classes),
            functions=len(fa.functions),
        )

        # Also add symbol nodes
        for cls in fa.classes:
            symbol_id = f"class:{fa.file_path}:{cls.name}"
            self._symbol_id_map[cls.qualified_name or cls.name] = symbol_id
            self.graph.add_node(
                symbol_id,
                NodeType.CLASS,
                name=cls.name,
                path=fa.file_path,
                line=cls.location.line_start,
            )
            self.graph.add_edge(DependencyEdge(
                source_id=node_id,
                target_id=symbol_id,
                relationship=RelationshipType.CONTAINS,
                evidence_locations=[cls.location.model_dump()],
                evidence_description=f"Class {cls.name} defined in {fa.file_path}",
            ))

        for func in fa.functions:
            symbol_id = f"function:{fa.file_path}:{func.name}"
            self._symbol_id_map[func.qualified_name or func.name] = symbol_id
            self.graph.add_node(
                symbol_id,
                        NodeType.FUNCTION,
                        name=func.name,
                path=fa.file_path,
                line=func.location.line_start,
                is_async=func.is_async,
            )
            self.graph.add_edge(DependencyEdge(
                source_id=node_id,
                target_id=symbol_id,
                relationship=RelationshipType.CONTAINS,
                evidence_locations=[func.location.model_dump()],
                evidence_description=f"Function {func.name} defined in {fa.file_path}",
            ))

        return node_id

    def _add_module_node(self, mod: ModuleInfo) -> str:
        """Add a module as a node."""
        node_id = f"module:{mod.name}"
        self._module_id_map[mod.name] = node_id
        self.graph.add_node(
            node_id,
            NodeType.MODULE,
            name=mod.name,
            path=mod.path,
            files=mod.files,
        )
        return node_id

    def _add_import_edges(self, fa: FileAnalysis, project: ProjectAnalysis) -> None:
        """Add edges for import relationships."""
        source_id = f"file:{fa.file_path}"

        for imp in fa.imports:
            target_path = self._resolve_import(imp, fa, project)
            if target_path:
                target_id = f"file:{target_path}"
                if target_id in self.graph.nodes:
                    self.graph.add_edge(DependencyEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relationship=RelationshipType.IMPORTS,
                        evidence_locations=[imp.location.model_dump()],
                        evidence_description=f"import {imp.module} from {fa.file_path}",
                    ))
            else:
                # External dependency
                ext_id = f"external:{imp.module}"
                if ext_id not in self.graph.nodes:
                    self.graph.add_node(
                        ext_id,
                        NodeType.EXTERNAL_SERVICE,
                        name=imp.module,
                    )
                self.graph.add_edge(DependencyEdge(
                    source_id=source_id,
                    target_id=ext_id,
                    relationship=RelationshipType.DEPENDS_ON,
                    evidence_locations=[imp.location.model_dump()],
                    evidence_description=f"External dependency: {imp.module}",
                    confidence=0.9,
                ))

    def _add_call_edges(self, fa: FileAnalysis, project: ProjectAnalysis) -> None:
        """Add edges for function call relationships."""
        source_id = f"file:{fa.file_path}"

        for func in fa.functions:
            func_id = f"function:{fa.file_path}:{func.name}"
            for call_name in func.calls:
                # Try to resolve the call target
                target_id = self._symbol_id_map.get(call_name)
                if not target_id:
                    # Check file-level functions
                    target_id = f"function:{fa.file_path}:{call_name}"

                if target_id in self.graph.nodes and target_id != func_id:
                    self.graph.add_edge(DependencyEdge(
                        source_id=func_id,
                        target_id=target_id,
                        relationship=RelationshipType.CALLS,
                        evidence_locations=[func.location.model_dump()],
                        evidence_description=f"{func.name}() calls {call_name}()",
                        confidence=0.8,
                    ))

    def _add_inheritance_edges(self, fa: FileAnalysis, project: ProjectAnalysis) -> None:
        """Add edges for class inheritance."""
        for cls in fa.classes:
            cls_id = f"class:{fa.file_path}:{cls.name}"
            for base_name in cls.bases:
                base_id = self._symbol_id_map.get(base_name)
                if base_id and base_id != cls_id:
                    self.graph.add_edge(DependencyEdge(
                        source_id=cls_id,
                        target_id=base_id,
                        relationship=RelationshipType.INHERITS,
                        evidence_locations=[cls.location.model_dump()],
                        evidence_description=f"{cls.name} inherits from {base_name}",
                    ))

    def _add_test_edges(self, fa: FileAnalysis, project: ProjectAnalysis) -> None:
        """Add test coverage relationships."""
        source_id = f"file:{fa.file_path}"

        # Find what the test is testing
        basename = os.path.basename(fa.file_path).replace("test_", "").replace("_test", "")
        for other_fa in project.file_analyses:
            if other_fa.file_path != fa.file_path:
                other_base = os.path.basename(other_fa.file_path)
                if other_base.startswith(basename) or basename.startswith(other_base.replace(".py", "").replace(".js", "")):
                    target_id = f"file:{other_fa.file_path}"
                    self.graph.add_edge(DependencyEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relationship=RelationshipType.TESTED_BY,
                        evidence_description=f"Test file {fa.file_path} tests {other_fa.file_path}",
                        confidence=0.7,
                    ))

    def _add_containment_edges(self, mod: ModuleInfo) -> None:
        """Add containment edges for module -> files."""
        module_id = f"module:{mod.name}"
        for file_path in mod.files:
            file_id = f"file:{file_path}"
            if file_id in self.graph.nodes:
                self.graph.add_edge(DependencyEdge(
                    source_id=module_id,
                    target_id=file_id,
                    relationship=RelationshipType.CONTAINS,
                    evidence_description=f"Module {mod.name} contains {file_path}",
                ))

    def _resolve_import(
        self,
        imp: ImportInfo,
        fa: FileAnalysis,
        project: ProjectAnalysis,
    ) -> str | None:
        """Try to resolve an import to a local file path."""
        if imp.is_relative:
            # Resolve relative import
            from_dir = os.path.dirname(fa.file_path)
            module = imp.module.lstrip(".")
            parts = module.split(".") if module else []

            candidate = from_dir
            for part in parts:
                candidate = os.path.join(candidate, part)

            # Check various extensions
            for ext in [".py", ".js", ".ts", ".tsx", ".jsx", "/__init__.py", "/index.js", "/index.ts"]:
                path = candidate + ext
                for file_anal in project.file_analyses:
                    if file_anal.file_path.endswith(path) or file_anal.file_path == path:
                        return file_anal.file_path
        else:
            # Try to match against known files
            module_parts = imp.module.split(".")
            for file_anal in project.file_analyses:
                rel = file_anal.file_path  # already relative
                rel_parts = rel.replace("\\", "/").replace(".py", "").replace(".js", "").replace(".ts", "").split("/")

                # Match module path to file path
                if module_parts[-1] == rel_parts[-1] or module_parts == rel_parts:
                    return file_anal.file_path
                # __init__.py match
                if rel_parts[-1] == "__init__" and module_parts[:-1] == rel_parts[:-1]:
                    return file_anal.file_path

        return None
