"""Tests for core data models."""

import pytest
from asa.core.models import (
    DependencyEdge,
    DependencyGraph,
    FileAnalysis,
    FunctionInfo,
    SourceLocation,
    SymbolInfo,
)
from asa.core.types import NodeType, RelationshipType


class TestSourceLocation:
    def test_basic_location(self):
        loc = SourceLocation(file_path="test.py", line_start=10, line_end=20)
        assert loc.file_path == "test.py"
        assert loc.line_start == 10
        assert loc.line_end == 20

    def test_to_display(self):
        loc = SourceLocation(file_path="test.py", line_start=10, line_end=20)
        display = loc.to_display()
        assert "test.py" in display
        assert "10" in display

    def test_to_display_same_line(self):
        loc = SourceLocation(file_path="test.py", line_start=5)
        display = loc.to_display()
        assert "5" in display
        assert "-" not in display


class TestDependencyGraph:
    def test_add_node(self):
        graph = DependencyGraph()
        graph.add_node("node1", NodeType.FILE, name="test.py")
        assert "node1" in graph.nodes
        assert graph.nodes["node1"]["type"] == "File"

    def test_add_edge(self):
        graph = DependencyGraph()
        graph.add_node("a", NodeType.FILE)
        graph.add_node("b", NodeType.FILE)
        edge = DependencyEdge(
            source_id="a",
            target_id="b",
            relationship=RelationshipType.IMPORTS,
        )
        graph.add_edge(edge)
        assert len(graph.edges) == 1

    def test_fan_in_fan_out(self):
        graph = DependencyGraph()
        graph.add_node("a", NodeType.FILE)
        graph.add_node("b", NodeType.FILE)
        graph.add_node("c", NodeType.FILE)

        graph.add_edge(DependencyEdge(
            source_id="a", target_id="b", relationship=RelationshipType.CALLS,
        ))
        graph.add_edge(DependencyEdge(
            source_id="c", target_id="b", relationship=RelationshipType.CALLS,
        ))

        assert graph.fan_in("b") == 2
        assert graph.fan_out("a") == 1
        assert graph.fan_in("a") == 0

    def test_get_edges_from(self):
        graph = DependencyGraph()
        graph.add_node("a", NodeType.FILE)
        graph.add_node("b", NodeType.FILE)
        graph.add_node("c", NodeType.FILE)

        graph.add_edge(DependencyEdge(
            source_id="a", target_id="b", relationship=RelationshipType.CALLS,
        ))
        graph.add_edge(DependencyEdge(
            source_id="a", target_id="c", relationship=RelationshipType.IMPORTS,
        ))

        edges = graph.get_edges_from("a")
        assert len(edges) == 2


class TestFileAnalysis:
    def test_file_analysis_creation(self):
        fa = FileAnalysis(
            file_path="test.py",
            language="python",
            lines_of_code=100,
        )
        assert fa.file_path == "test.py"
        assert fa.language == "python"
        assert fa.lines_of_code == 100
        assert fa.classes == []
        assert fa.functions == []
        assert fa.imports == []

    def test_file_analysis_with_symbols(self):
        func = FunctionInfo(
            name="hello",
            qualified_name="hello",
            symbol_type=NodeType.FUNCTION,
            location=SourceLocation(file_path="test.py", line_start=1),
        )
        fa = FileAnalysis(
            file_path="test.py",
            language="python",
            functions=[func],
        )
        assert len(fa.functions) == 1
        assert fa.functions[0].name == "hello"
