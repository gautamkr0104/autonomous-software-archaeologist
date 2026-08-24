/** Types matching the ASA backend models. */

export interface SourceLocation {
  file_path: string;
  line_start: number;
  line_end?: number;
  column_start?: number;
  column_end?: number;
}

export interface SymbolInfo {
  id: string;
  name: string;
  qualified_name: string;
  symbol_type: string;
  location: SourceLocation;
  docstring?: string;
}

export interface FunctionInfo extends SymbolInfo {
  parameters: { name: string; has_default?: string }[];
  return_type?: string;
  is_async: boolean;
  decorators: string[];
  calls: string[];
}

export interface ClassInfo extends SymbolInfo {
  bases: string[];
  implements: string[];
  methods: FunctionInfo[];
  is_abstract: boolean;
  decorators: string[];
}

export interface ImportInfo {
  id: string;
  module: string;
  names: string[];
  is_relative: boolean;
  is_wildcard: boolean;
  location: SourceLocation;
}

export interface FileAnalysis {
  id: string;
  file_path: string;
  language: string;
  size_bytes: number;
  classes: ClassInfo[];
  functions: FunctionInfo[];
  imports: ImportInfo[];
  lines_of_code: number;
  lines_of_comments: number;
  is_test: boolean;
  is_config: boolean;
}

export interface RepositoryInfo {
  id: string;
  url?: string;
  name: string;
  description?: string;
  default_branch: string;
  languages: Record<string, number>;
  frameworks: string[];
  total_files: number;
  total_size_bytes: number;
  commit_count: number;
  analyzed_at: string;
}

export interface DependencyEdge {
  id: string;
  source_id: string;
  target_id: string;
  relationship: string;
  evidence_locations: SourceLocation[];
  evidence_description: string;
  confidence: number;
}

export interface DependencyGraph {
  nodes: Record<string, { type: string; [key: string]: unknown }>;
  edges: DependencyEdge[];
}

export interface GitHistory {
  commits: CommitInfo[];
  branches: string[];
  tags: string[];
  contributors: Record<string, number>;
}

export interface CommitInfo {
  sha: string;
  message: string;
  author: string;
  date: string;
  files_changed: string[];
  insertions: number;
  deletions: number;
}

export interface ModuleInfo {
  id: string;
  name: string;
  path: string;
  files: string[];
  submodules: string[];
}

export interface Evidence {
  id: string;
  evidence_type: string;
  description: string;
  source_file?: string;
  source_location?: SourceLocation;
  content_snippet?: string;
  confidence: number;
  collected_by: string;
}

export interface Finding {
  id: string;
  claim: string;
  evidence: Evidence[];
  confidence: number;
  confidence_level: string;
  status: 'verified' | 'uncertain' | 'rejected' | 'pending';
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  source_files: string[];
  reasoning: string;
  created_by: string;
}

export interface ProjectAnalysis {
  id: string;
  repository: RepositoryInfo;
  file_analyses: FileAnalysis[];
  modules: ModuleInfo[];
  dependency_graph: DependencyGraph;
  git_history: GitHistory;
  external_dependencies: { name: string; version?: string; is_development: boolean }[];
  created_at: string;
  completed_at?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  confidence: number;
}

export interface GraphMetrics {
  total_nodes: number;
  total_edges: number;
  avg_fan_in: number;
  avg_fan_out: number;
  connected_components: number;
  cycle_count: number;
  density: number;
  most_depended_upon: [string, number][];
  highest_centrality: [string, number][];
}
