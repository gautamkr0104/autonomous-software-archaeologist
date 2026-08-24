import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { ZoomIn, Filter, Info } from 'lucide-react';
import { listAnalyses, getGraph } from '../services/api';

const NODE_COLORS: Record<string, string> = {
  File: '#6366f1',
  Module: '#8b5cf6',
  Class: '#06b6d4',
  Function: '#22c55e',
  ExternalService: '#f59e0b',
  Test: '#ec4899',
  Configuration: '#64748b',
};

const RELATIONSHIP_COLORS: Record<string, string> = {
  IMPORTS: '#6366f1',
  CALLS: '#22c55e',
  INHERITS: '#f59e0b',
  IMPLEMENTS: '#06b6d4',
  DEPENDS_ON: '#ef4444',
  TESTED_BY: '#ec4899',
  CONTAINS: '#64748b',
};

function buildFlowElements(
  nodes: { id: string; label: string; type: string; properties: Record<string, unknown> }[],
  edges: { id: string; source: string; target: string; label: string; confidence: number }[],
) {
  const flowNodes: Node[] = nodes.slice(0, 200).map((n, i) => ({
    id: n.id,
    data: { label: n.label || n.id.split(':').pop() || n.id },
    position: { x: (i % 10) * 180, y: Math.floor(i / 10) * 120 },
    style: {
      background: NODE_COLORS[n.type] || '#64748b',
      color: 'white',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      border: '1px solid rgba(255,255,255,0.1)',
    },
  }));

  const flowEdges: Edge[] = edges.slice(0, 300).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.confidence < 0.8,
    style: {
      stroke: RELATIONSHIP_COLORS[e.label] || '#4b5563',
      opacity: e.confidence,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: RELATIONSHIP_COLORS[e.label] || '#4b5563',
    },
  }));

  return { flowNodes, flowEdges };
}

export default function ArchitectureGraphPage() {
  const [selectedType, setSelectedType] = useState<string>('');
  const [minConfidence, setMinConfidence] = useState(0);

  const { data: analyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  });

  const latestId = analyses?.[0]?.id;

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['graph', latestId, selectedType, minConfidence],
    queryFn: () =>
      getGraph(latestId!, {
        node_type: selectedType || undefined,
        min_confidence: minConfidence,
      }),
    enabled: !!latestId,
  });

  const { flowNodes, flowEdges } = useMemo(
    () =>
      graphData
        ? buildFlowElements(graphData.nodes, graphData.edges)
        : { flowNodes: [], flowEdges: [] },
    [graphData],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Update when data changes
  useMemo(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const nodeTypes = [
    '',
    'File',
    'Module',
    'Class',
    'Function',
    'ExternalService',
  ];

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-gray-900/50 px-6 py-3">
        <h2 className="text-lg font-semibold text-white">Architecture Graph</h2>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            className="input"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="">All Types</option>
            {nodeTypes.filter(Boolean).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Min Confidence:</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            className="w-24"
          />
          <span className="text-xs text-gray-400">{minConfidence}</span>
        </div>

        {graphData && (
          <div className="ml-auto flex items-center gap-4 text-xs text-gray-500">
            <span>{graphData.nodes.length} nodes</span>
            <span>{graphData.edges.length} edges</span>
          </div>
        )}
      </div>

      {/* Graph */}
      <div className="flex-1">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#374151" gap={20} />
            <Controls />
            <MiniMap
              nodeColor={(n) => NODE_COLORS[n.type as string] || '#64748b'}
              maskColor="rgba(0,0,0,0.7)"
            />
          </ReactFlow>
        )}
      </div>

      {/* Legend */}
      <div className="border-t border-gray-800 bg-gray-900/50 px-6 py-2">
        <div className="flex flex-wrap gap-3">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <div
                className="h-3 w-3 rounded"
                style={{ background: color }}
              />
              <span className="text-xs text-gray-500">{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
