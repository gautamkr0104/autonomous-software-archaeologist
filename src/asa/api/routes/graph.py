"""Graph API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# In-memory graph store
_graph_store: dict[str, dict] = {}


class GraphNode(BaseModel):
    """A node in the graph visualization."""

    id: str
    label: str
    type: str
    properties: dict = {}


class GraphEdge(BaseModel):
    """An edge in the graph visualization."""

    id: str
    source: str
    target: str
    label: str
    confidence: float = 1.0


class GraphResponse(BaseModel):
    """Graph data for visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metrics: dict = {}


class GraphMetrics(BaseModel):
    """Graph analysis metrics."""

    total_nodes: int
    total_edges: int
    avg_fan_in: float
    avg_fan_out: float
    connected_components: int
    cycle_count: int
    most_depended_upon: list[tuple[str, int]]
    highest_centrality: list[tuple[str, float]]


@router.get("/{analysis_id}")
async def get_graph(
    analysis_id: str,
    node_type: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(500, ge=1, le=2000),
) -> GraphResponse:
    """Get the dependency graph for visualization."""
    if analysis_id not in _graph_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

    graph_data = _graph_store[analysis_id]
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # Filter by node type
    if node_type:
        nodes = [n for n in nodes if n.get("type") == node_type]

    # Filter by confidence
    edges = [e for e in edges if e.get("confidence", 1.0) >= min_confidence]

    # Limit
    nodes = nodes[:limit]

    # Build response
    node_ids = {n["id"] for n in nodes}
    filtered_edges = [e for e in edges if e["source"] in node_ids or e["target"] in node_ids]

    return GraphResponse(
        nodes=[GraphNode(**n) for n in nodes],
        edges=[GraphEdge(**e) for e in filtered_edges],
        metrics=graph_data.get("metrics", {}),
    )


@router.get("/{analysis_id}/node/{node_id}")
async def get_node_neighbors(
    analysis_id: str,
    node_id: str,
    depth: int = Query(1, ge=1, le=3),
) -> dict:
    """Get a node and its neighbors up to specified depth."""
    if analysis_id not in _graph_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

    graph_data = _graph_store[analysis_id]
    nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
    edges = graph_data.get("edges", [])

    if node_id not in nodes:
        raise HTTPException(status_code=404, detail="Node not found")

    # BFS to find neighbors
    visited = {node_id}
    frontier = {node_id}
    result_nodes = [nodes[node_id]]
    result_edges = []

    for _ in range(depth):
        next_frontier = set()
        for nid in frontier:
            for e in edges:
                if e["source"] == nid and e["target"] not in visited:
                    visited.add(e["target"])
                    next_frontier.add(e["target"])
                    if e["target"] in nodes:
                        result_nodes.append(nodes[e["target"]])
                    result_edges.append(e)
                elif e["target"] == nid and e["source"] not in visited:
                    visited.add(e["source"])
                    next_frontier.add(e["source"])
                    if e["source"] in nodes:
                        result_nodes.append(nodes[e["source"]])
                    result_edges.append(e)
        frontier = next_frontier

    return {
        "nodes": result_nodes,
        "edges": result_edges,
    }


@router.get("/{analysis_id}/metrics")
async def get_graph_metrics(analysis_id: str) -> dict:
    """Get graph analysis metrics."""
    if analysis_id not in _graph_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return _graph_store[analysis_id].get("metrics", {})


def store_graph(analysis_id: str, graph_data: dict) -> None:
    """Store graph data for an analysis."""
    _graph_store[analysis_id] = graph_data
