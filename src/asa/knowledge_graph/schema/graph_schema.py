"""Knowledge graph schema.

Defines the entity-relationship model for the persistent knowledge graph.
Supports PostgreSQL initially with Neo4j abstraction layer for future use.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from asa.core.types import NodeType, RelationshipType


# ---------------------------------------------------------------------------
# Entity definitions
# ---------------------------------------------------------------------------

class KGNode(BaseModel):
    """A node in the knowledge graph."""

    id: str
    node_type: NodeType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KGEdge(BaseModel):
    """An edge (relationship) in the knowledge graph."""

    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    properties: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KGPath(BaseModel):
    """A path between two nodes in the graph."""

    nodes: list[str]
    edges: list[str]
    length: int


class KGSubgraph(BaseModel):
    """A subgraph with its nodes and edges."""

    nodes: list[KGNode]
    edges: list[KGEdge]
    root_node: str | None = None


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

class KnowledgeGraphSchema:
    """Defines and manages the knowledge graph schema.

    Initially backed by in-memory storage with future PostgreSQL/Neo4j support.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, KGNode] = {}
        self._edges: dict[str, KGEdge] = {}
        self._adjacency: dict[str, set[str]] = {}  # node_id -> set of edge_ids
        self._reverse_adj: dict[str, set[str]] = {}

    # -- Node operations --

    def add_node(self, node: KGNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = set()
        if node.id not in self._reverse_adj:
            self._reverse_adj[node.id] = set()

    def get_node(self, node_id: str) -> KGNode | None:
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> list[KGNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def update_node(self, node_id: str, **properties: Any) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.properties.update(properties)
        node.updated_at = datetime.utcnow()
        return True

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False

        # Remove associated edges
        edge_ids = self._adjacency.get(node_id, set()).copy()
        edge_ids.update(self._reverse_adj.get(node_id, set()))
        for eid in edge_ids:
            self._remove_edge_by_id(eid)

        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        self._reverse_adj.pop(node_id, None)
        return True

    # -- Edge operations --

    def add_edge(self, edge: KGEdge) -> None:
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, set()).add(edge.id)
        self._reverse_adj.setdefault(edge.target_id, set()).add(edge.id)

    def get_edge(self, edge_id: str) -> KGEdge | None:
        return self._edges.get(edge_id)

    def get_edges_from(self, node_id: str) -> list[KGEdge]:
        edge_ids = self._adjacency.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_edges_to(self, node_id: str) -> list[KGEdge]:
        edge_ids = self._reverse_adj.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_neighbors(self, node_id: str, depth: int = 1) -> KGSubgraph:
        """Get neighbors up to specified depth via BFS."""
        visited_nodes: set[str] = {node_id}
        visited_edges: set[str] = set()
        frontier = {node_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for edge in self.get_edges_from(nid):
                    if edge.target_id not in visited_nodes:
                        visited_nodes.add(edge.target_id)
                        next_frontier.add(edge.target_id)
                    visited_edges.add(edge.id)

                for edge in self.get_edges_to(nid):
                    if edge.source_id not in visited_nodes:
                        visited_nodes.add(edge.source_id)
                        next_frontier.add(edge.source_id)
                    visited_edges.add(edge.id)

            frontier = next_frontier

        return KGSubgraph(
            nodes=[self._nodes[nid] for nid in visited_nodes if nid in self._nodes],
            edges=[self._edges[eid] for eid in visited_edges if eid in self._edges],
            root_node=node_id,
        )

    def remove_edge(self, edge_id: str) -> bool:
        return self._remove_edge_by_id(edge_id)

    # -- Query operations --

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> KGPath | None:
        """Find shortest path between two nodes."""
        from collections import deque

        queue: deque[tuple[str, list[str], list[str]]] = deque()
        queue.append((source_id, [source_id], []))
        visited = {source_id}

        while queue:
            current, path_nodes, path_edges = queue.popleft()
            if current == target_id:
                return KGPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    length=len(path_edges),
                )
            if len(path_nodes) > max_depth:
                continue

            for edge in self.get_edges_from(current):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((
                        edge.target_id,
                        path_nodes + [edge.target_id],
                        path_edges + [edge.id],
                    ))

            for edge in self.get_edges_to(current):
                if edge.source_id not in visited:
                    visited.add(edge.source_id)
                    queue.append((
                        edge.source_id,
                        path_nodes + [edge.source_id],
                        path_edges + [edge.id],
                    ))

        return None

    def fan_in(self, node_id: str) -> int:
        return len(self._reverse_adj.get(node_id, set()))

    def fan_out(self, node_id: str) -> int:
        return len(self._adjacency.get(node_id, set()))

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def to_networkx(self) -> Any:
        """Export to NetworkX DiGraph for algorithmic analysis."""
        import networkx as nx

        G = nx.DiGraph()
        for nid, node in self._nodes.items():
            G.add_node(nid, type=node.node_type.value, name=node.name, **node.properties)
        for eid, edge in self._edges.items():
            G.add_edge(
                edge.source_id,
                edge.target_id,
                relationship=edge.relationship.value,
                confidence=edge.confidence,
            )
        return G

    # -- Internal --

    def _remove_edge_by_id(self, edge_id: str) -> bool:
        edge = self._edges.get(edge_id)
        if edge is None:
            return False

        self._adjacency.get(edge.source_id, set()).discard(edge_id)
        self._reverse_adj.get(edge.target_id, set()).discard(edge_id)
        del self._edges[edge_id]
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        type_counts: dict[str, int] = {}
        for node in self._nodes.values():
            t = node.node_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        rel_counts: dict[str, int] = {}
        for edge in self._edges.values():
            r = edge.relationship.value
            rel_counts[r] = rel_counts.get(r, 0) + 1

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "node_types": type_counts,
            "relationship_types": rel_counts,
        }
