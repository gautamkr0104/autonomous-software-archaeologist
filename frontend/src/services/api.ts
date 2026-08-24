/** API client for the ASA backend. */

import axios from 'axios';
import type {
  ProjectAnalysis,
  Finding,
  GraphNode,
  GraphEdge,
  GraphMetrics,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// --- Analysis ---

export async function startAnalysis(params: {
  url?: string;
  local_path?: string;
  commit_ref?: string;
  branch?: string;
}): Promise<{ id: string; status: string; message: string }> {
  const { data } = await api.post('/analysis/start', params);
  return data;
}

export async function getAnalysis(id: string): Promise<{
  status: string;
  result?: ProjectAnalysis;
  error?: string;
}> {
  const { data } = await api.get(`/analysis/${id}`);
  return data;
}

export async function listAnalyses(): Promise<
  { id: string; status: string }[]
> {
  const { data } = await api.get('/analysis/');
  return data;
}

// --- Findings ---

export async function listFindings(params?: {
  category?: string;
  severity?: string;
  status?: string;
  min_confidence?: number;
  limit?: number;
}): Promise<Finding[]> {
  const { data } = await api.get('/findings/', { params });
  return data;
}

export async function getFinding(id: string): Promise<Finding> {
  const { data } = await api.get(`/findings/${id}`);
  return data;
}

export async function verifyFinding(
  id: string,
  accepted: boolean,
): Promise<Finding> {
  const { data } = await api.post(
    `/findings/${id}/verify`,
    null,
    { params: { accepted } },
  );
  return data;
}

// --- Graph ---

export async function getGraph(
  analysisId: string,
  params?: { node_type?: string; min_confidence?: number; limit?: number },
): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; metrics: GraphMetrics }> {
  const { data } = await api.get(`/graph/${analysisId}`, { params });
  return data;
}

export async function getNodeNeighbors(
  analysisId: string,
  nodeId: string,
  depth?: number,
): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const { data } = await api.get(`/graph/${analysisId}/node/${nodeId}`, {
    params: { depth },
  });
  return data;
}

export async function getGraphMetrics(
  analysisId: string,
): Promise<GraphMetrics> {
  const { data } = await api.get(`/graph/${analysisId}/metrics`);
  return data;
}

// --- Investigation ---

export async function askQuestion(
  question: string,
  analysisId?: string,
): Promise<{
  question: string;
  answer: string;
  confidence: number;
  evidence: unknown[];
  sources: string[];
  reasoning: string;
}> {
  const { data } = await api.post('/investigate/ask', {
    question,
    analysis_id: analysisId,
  });
  return data;
}

// --- Health ---

export async function getHealth(): Promise<{
  status: string;
  version: string;
}> {
  const { data } = await api.get('/health');
  return data;
}

export async function getStatus(): Promise<{
  status: string;
  tree_sitter: { available: boolean; languages: string[] };
  features: Record<string, boolean>;
}> {
  const { data } = await api.get('/status');
  return data;
}
