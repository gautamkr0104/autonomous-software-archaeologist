import { useQuery } from '@tanstack/react-query';
import {
  GitBranch,
  Files,
  Layers,
  Link2,
  Users,
  Clock,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { listAnalyses, getAnalysis } from '../services/api';
import type { ProjectAnalysis } from '../types';

function StatCard({
  icon: Icon,
  label,
  value,
  color = 'text-gray-300',
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="card flex items-center gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-600/20">
        <Icon className="h-6 w-6 text-indigo-400" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      </div>
    </div>
  );
}

function LanguageBar({ languages }: { languages: Record<string, number> }) {
  const sorted = Object.entries(languages)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  const colors = [
    'bg-indigo-500',
    'bg-purple-500',
    'bg-cyan-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-orange-500',
    'bg-pink-500',
    'bg-teal-500',
  ];

  return (
    <div className="space-y-3">
      {sorted.map(([lang, pct], i) => (
        <div key={lang} className="flex items-center gap-3">
          <span className="w-24 text-sm text-gray-400">{lang}</span>
          <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
            <div
              className={`h-full rounded-full ${colors[i % colors.length]}`}
              style={{ width: `${pct * 100}%` }}
            />
          </div>
          <span className="w-12 text-right text-xs text-gray-500">
            {(pct * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function DependencyList({
  deps,
}: {
  deps: { name: string; version?: string }[];
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {deps.slice(0, 30).map((dep) => (
        <span key={dep.name} className="badge bg-gray-800 text-gray-300">
          {dep.name}
          {dep.version && (
            <span className="ml-1 text-gray-600">{dep.version}</span>
          )}
        </span>
      ))}
      {deps.length > 30 && (
        <span className="badge bg-gray-800 text-gray-500">
          +{deps.length - 30} more
        </span>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const { data: analyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  });

  const latestId = analyses?.[0]?.id;
  const { data, isLoading } = useQuery({
    queryKey: ['analysis', latestId],
    queryFn: () => getAnalysis(latestId!),
    enabled: !!latestId,
  });

  const project = data?.result as ProjectAnalysis | undefined;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          <p className="mt-4 text-gray-500">Loading analysis...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Shield className="mx-auto h-16 w-16 text-gray-700" />
          <h2 className="mt-4 text-xl font-semibold text-gray-300">
            No Analysis Available
          </h2>
          <p className="mt-2 text-gray-500">
            Run an analysis from the "Analyze" page to get started.
          </p>
        </div>
      </div>
    );
  }

  const { repository, file_analyses, modules, external_dependencies, git_history, dependency_graph } =
    project;

  const totalLoc = file_analyses.reduce((sum, f) => sum + f.lines_of_code, 0);
  const totalClasses = file_analyses.reduce((sum, f) => sum + f.classes.length, 0);
  const totalFunctions = file_analyses.reduce((sum, f) => sum + f.functions.length, 0);

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">
          {repository.name}
        </h1>
        {repository.description && (
          <p className="mt-1 text-gray-500">{repository.description}</p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          {repository.frameworks.map((fw) => (
            <span key={fw} className="badge bg-purple-500/20 text-purple-400">
              {fw}
            </span>
          ))}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Files} label="Files" value={repository.total_files} />
        <StatCard icon={Layers} label="Modules" value={modules.length} />
        <StatCard
          icon={Link2}
          label="Dependencies"
          value={external_dependencies.length}
        />
        <StatCard
          icon={Users}
          label="Contributors"
          value={Object.keys(git_history.contributors).length}
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={GitBranch} label="Commits" value={repository.commit_count} />
        <StatCard icon={Files} label="Lines of Code" value={totalLoc.toLocaleString()} />
        <StatCard icon={Layers} label="Classes" value={totalClasses} />
        <StatCard icon={Layers} label="Functions" value={totalFunctions} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Languages */}
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">Languages</h3>
          <LanguageBar languages={repository.languages} />
        </div>

        {/* Graph summary */}
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">
            Dependency Graph
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Nodes</p>
              <p className="text-2xl font-bold text-white">
                {Object.keys(dependency_graph.nodes).length}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Edges</p>
              <p className="text-2xl font-bold text-white">
                {dependency_graph.edges.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* External dependencies */}
      {external_dependencies.length > 0 && (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-white">
            External Dependencies ({external_dependencies.length})
          </h3>
          <DependencyList deps={external_dependencies} />
        </div>
      )}
    </div>
  );
}
