"""Tests for the knowledge graph schema."""

import pytest
from asa.knowledge_graph.schema.graph_schema import (
    KGEdge,
    KGNode,
    KGSubgraph,
    KnowledgeGraphSchema,
)
from asa.core.types import NodeType, RelationshipType


@pytest.fixture
def graph():
    return KnowledgeGraphSchema()


class TestKnowledgeGraphSchema:
    def test_add_node(self, graph):
        node = KGNode(id="n1", node_type=NodeType.FILE, name="test.py")
        graph.add_node(node)
        assert graph.node_count == 1
        assert graph.get_node("n1") is not None

    def test_add_edge(self, graph):
        graph.add_node(KGNode(id="n1", node_type=NodeType.FILE, name="a.py"))
        graph.add_node(KGNode(id="n2", node_type=NodeType.FILE, name="b.py"))
        edge = KGEdge(
            id="e1",
            source_id="n1",
            target_id="n2",
            relationship=RelationshipType.IMPORTS,
        )
        graph.add_edge(edge)
        assert graph.edge_count == 1

    def test_fan_in_fan_out(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))
        graph.add_node(KGNode(id="c", node_type=NodeType.FILE, name="c"))

        graph.add_edge(KGEdge(id="e1", source_id="a", target_id="b", relationship=RelationshipType.CALLS))
        graph.add_edge(KGEdge(id="e2", source_id="c", target_id="b", relationship=RelationshipType.CALLS))

        assert graph.fan_in("b") == 2
        assert graph.fan_out("a") == 1

    def test_get_neighbors(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))
        graph.add_node(KGNode(id="c", node_type=NodeType.FILE, name="c"))

        graph.add_edge(KGEdge(id="e1", source_id="a", target_id="b", relationship=RelationshipType.CALLS))
        graph.add_edge(KGEdge(id="e2", source_id="b", target_id="c", relationship=RelationshipType.IMPORTS))

        subgraph = graph.get_neighbors("a", depth=2)
        assert len(subgraph.nodes) == 3  # a, b, c
        assert len(subgraph.edges) == 2

    def test_find_path(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))
        graph.add_node(KGNode(id="c", node_type=NodeType.FILE, name="c"))

        graph.add_edge(KGEdge(id="e1", source_id="a", target_id="b", relationship=RelationshipType.CALLS))
        graph.add_edge(KGEdge(id="e2", source_id="b", target_id="c", relationship=RelationshipType.IMPORTS))

        path = graph.find_path("a", "c")
        assert path is not None
        assert path.length == 2
        assert path.nodes == ["a", "b", "c"]

    def test_find_path_no_route(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))

        path = graph.find_path("a", "b")
        assert path is None

    def test_remove_node(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))
        graph.add_edge(KGEdge(id="e1", source_id="a", target_id="b", relationship=RelationshipType.CALLS))

        assert graph.remove_node("a") is True
        assert graph.node_count == 1
        assert graph.edge_count == 0  # Edge was removed

    def test_get_nodes_by_type(self, graph):
        graph.add_node(KGNode(id="n1", node_type=NodeType.FILE, name="f.py"))
        graph.add_node(KGNode(id="n2", node_type=NodeType.CLASS, name="MyClass"))
        graph.add_node(KGNode(id="n3", node_type=NodeType.FILE, name="g.py"))

        files = graph.get_nodes_by_type(NodeType.FILE)
        assert len(files) == 2

    def test_stats(self, graph):
        graph.add_node(KGNode(id="n1", node_type=NodeType.FILE, name="f"))
        graph.add_edge(KGEdge(id="e1", source_id="n1", target_id="n1", relationship=RelationshipType.CONTAINS))

        stats = graph.get_stats()
        assert stats["total_nodes"] == 1
        assert stats["total_edges"] == 1
        assert "File" in stats["node_types"]

    def test_to_networkx(self, graph):
        graph.add_node(KGNode(id="a", node_type=NodeType.FILE, name="a"))
        graph.add_node(KGNode(id="b", node_type=NodeType.FILE, name="b"))
        graph.add_edge(KGEdge(id="e1", source_id="a", target_id="b", relationship=RelationshipType.CALLS))

        nx_graph = graph.to_networkx()
        assert len(nx_graph.nodes) == 2
        assert len(nx_graph.edges) == 1
