"""Core data models representing repository analysis results."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from asa.core.types import (
    AgentStatus,
    AnalysisPhase,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    NodeType,
    RelationshipType,
)


# ---------------------------------------------------------------------------
# Source locations
# ---------------------------------------------------------------------------

class SourceLocation(BaseModel):
    """Precise location inside a source file."""

    file_path: str
    line_start: int
    line_end: int | None = None
    column_start: int | None = None
    column_end: int | None = None
    byte_offset: int | None = None

    def to_display(self) -> str:
        suffix = f":{self.line_start}" if self.line_start else ""
        if self.line_end and self.line_end != self.line_start:
            suffix += f"-{self.line_end}"
        return f"{self.file_path}{suffix}"


class SourceRange(BaseModel):
    """Range between two source locations (used for diffs)."""

    start: SourceLocation
    end: SourceLocation


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------

class SymbolInfo(BaseModel):
    """A named code symbol (class, function, variable, etc.)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    qualified_name: str = ""
    symbol_type: NodeType
    location: SourceLocation
    docstring: str | None = None
    annotations: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FunctionInfo(SymbolInfo):
    """Detailed information about a function or method."""

    symbol_type: NodeType = NodeType.FUNCTION
    parameters: list[dict[str, str]] = Field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    is_static: bool = False
    is_class_method: bool = False
    is_property: bool = False
    decorators: list[str] = Field(default_factory=list)
    calls: list[str] = Field(default_factory=list)
    raises: list[str] = Field(default_factory=list)
    complexity_estimate: int | None = None


class ClassInfo(SymbolInfo):
    """Detailed information about a class."""

    symbol_type: NodeType = NodeType.CLASS
    bases: list[str] = Field(default_factory=list)
    implements: list[str] = Field(default_factory=list)
    methods: list[FunctionInfo] = Field(default_factory=list)
    class_variables: list[SymbolInfo] = Field(default_factory=list)
    inner_classes: list[str] = Field(default_factory=list)
    is_abstract: bool = False
    decorators: list[str] = Field(default_factory=list)


class ImportInfo(BaseModel):
    """An import statement with its details."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module: str
    names: list[str] = Field(default_factory=list)
    is_relative: bool = False
    is_wildcard: bool = False
    location: SourceLocation
    is_dynamic: bool = False


class ExportInfo(BaseModel):
    """An exported symbol."""

    name: str
    symbol_type: NodeType
    location: SourceLocation
    is_default: bool = False


# ---------------------------------------------------------------------------
# File analysis
# ---------------------------------------------------------------------------

class FileAnalysis(BaseModel):
    """Complete static analysis result for a single file."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    language: str
    size_bytes: int = 0
    last_modified: datetime | None = None

    # Symbols
    classes: list[ClassInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    imports: list[ImportInfo] = Field(default_factory=list)
    exports: list[ExportInfo] = Field(default_factory=list)

    # Structure
    global_variables: list[SymbolInfo] = Field(default_factory=list)
    constants: list[SymbolInfo] = Field(default_factory=list)

    # Metrics
    lines_of_code: int = 0
    lines_of_comments: int = 0
    lines_blank: int = 0
    cyclomatic_complexity: int | None = None
    halstead_volume: float | None = None

    # Configuration
    environment_variables: list[str] = Field(default_factory=list)
    configuration_keys: list[str] = Field(default_factory=list)

    # Metadata
    is_test: bool = False
    is_config: bool = False
    is_generated: bool = False
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Module info
# ---------------------------------------------------------------------------

class ModuleInfo(BaseModel):
    """Logical module / package grouping."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    path: str
    files: list[str] = Field(default_factory=list)
    submodules: list[str] = Field(default_factory=list)
    public_api: list[str] = Field(default_factory=list)
    language: str = ""
    description: str | None = None


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------

class DependencyEdge(BaseModel):
    """A single edge in the dependency graph with full provenance."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    relationship: RelationshipType
    evidence_locations: list[SourceLocation] = Field(default_factory=list)
    evidence_description: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DependencyGraph(BaseModel):
    """Graph of all detected relationships in a repository."""

    nodes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    edges: list[DependencyEdge] = Field(default_factory=list)

    def add_node(self, node_id: str, node_type: NodeType, **attrs: Any) -> None:
        self.nodes[node_id] = {"type": node_type.value, **attrs}

    def add_edge(self, edge: DependencyEdge) -> None:
        self.edges.append(edge)

    def get_edges_from(self, node_id: str) -> list[DependencyEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[DependencyEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def fan_in(self, node_id: str) -> int:
        return len(self.get_edges_to(node_id))

    def fan_out(self, node_id: str) -> int:
        return len(self.get_edges_from(node_id))


# ---------------------------------------------------------------------------
# Repository info
# ---------------------------------------------------------------------------

class RepositoryInfo(BaseModel):
    """Metadata about the ingested repository."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str | None = None
    local_path: str
    name: str
    description: str | None = None
    default_branch: str = "main"
    languages: dict[str, float] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    commit_count: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    commit_ref: str | None = None


class CommitInfo(BaseModel):
    """A single git commit."""

    sha: str
    message: str
    author: str
    author_email: str = ""
    date: datetime
    files_changed: list[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


class GitHistory(BaseModel):
    """Aggregated git history for a repository."""

    commits: list[CommitInfo] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    contributors: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analysis results
# ---------------------------------------------------------------------------

class FileDependency(BaseModel):
    """Dependency information for a specific file/package."""

    name: str
    version: str | None = None
    is_local: bool = False
    is_development: bool = False
    source_file: str | None = None


class AnalysisResult(BaseModel):
    """Result from a single analysis phase."""

    phase: AnalysisPhase
    status: AgentStatus = AgentStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    files_analyzed: int = 0
    symbols_extracted: int = 0
    relationships_found: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectAnalysis(BaseModel):
    """Top-level container for a complete repository analysis."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository: RepositoryInfo
    file_analyses: list[FileAnalysis] = Field(default_factory=list)
    modules: list[ModuleInfo] = Field(default_factory=list)
    dependency_graph: DependencyGraph = Field(default_factory=DependencyGraph)
    git_history: GitHistory = Field(default_factory=GitHistory)
    phase_results: list[AnalysisResult] = Field(default_factory=list)
    external_dependencies: list[FileDependency] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @property
    def total_symbols(self) -> int:
        count = 0
        for fa in self.file_analyses:
            count += len(fa.classes) + len(fa.functions) + len(fa.global_variables)
        return count

    @property
    def total_relationships(self) -> int:
        return len(self.dependency_graph.edges)

    def get_file(self, path: str) -> FileAnalysis | None:
        for fa in self.file_analyses:
            if fa.file_path == path:
                return fa
        return None
