import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  AlertTriangle,
  Zap,
  Layers,
  BookOpen,
  Link2,
  CheckCircle,
  XCircle,
  HelpCircle,
  Clock,
} from 'lucide-react';
import { listFindings, verifyFinding } from '../services/api';
import type { Finding } from '../types';

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  security: Shield,
  performance: Zap,
  architecture: Layers,
  maintainability: Layers,
  documentation: BookOpen,
  dependency: Link2,
  complexity: AlertTriangle,
  code_quality: Layers,
};

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];

const STATUS_ICONS: Record<string, React.ElementType> = {
  verified: CheckCircle,
  rejected: XCircle,
  uncertain: HelpCircle,
  pending: Clock,
};

function FindingCard({
  finding,
  onVerify,
}: {
  finding: Finding;
  onVerify: (id: string, accepted: boolean) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = CATEGORY_ICONS[finding.category] || Layers;
  const StatusIcon = STATUS_ICONS[finding.status] || Clock;

  return (
    <div className="card cursor-pointer transition-all hover:border-gray-700">
      <div onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start gap-3">
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              finding.severity === 'critical'
                ? 'bg-red-500/20'
                : finding.severity === 'high'
                ? 'bg-orange-500/20'
                : finding.severity === 'medium'
                ? 'bg-yellow-500/20'
                : 'bg-gray-700'
            }`}
          >
            <Icon
              className={`h-4 w-4 ${
                finding.severity === 'critical'
                  ? 'text-red-400'
                  : finding.severity === 'high'
                  ? 'text-orange-400'
                  : finding.severity === 'medium'
                  ? 'text-yellow-400'
                  : 'text-gray-400'
              }`}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white leading-snug">{finding.claim}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className={`badge severity-${finding.severity}`}>
                {finding.severity}
              </span>
              <span className={`badge badge-${finding.status}`}>
                <StatusIcon className="mr-1 h-3 w-3" />
                {finding.status}
              </span>
              <span className="text-xs text-gray-500">
                {finding.evidence.length} evidence
              </span>
              <span className="text-xs text-gray-500">
                {(finding.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 space-y-4 border-t border-gray-800 pt-4">
          {/* Evidence */}
          {finding.evidence.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500">
                Evidence
              </h4>
              <div className="space-y-2">
                {finding.evidence.map((ev) => (
                  <div
                    key={ev.id}
                    className="rounded bg-gray-800/50 p-3 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="badge bg-indigo-500/20 text-indigo-400">
                        {ev.evidence_type}
                      </span>
                      <span className="text-gray-400">{ev.description}</span>
                    </div>
                    {ev.source_file && (
                      <p className="mt-1 font-mono text-gray-600">
                        {ev.source_file}
                        {ev.source_location?.line_start
                          ? `:${ev.source_location.line_start}`
                          : ''}
                      </p>
                    )}
                    {ev.content_snippet && (
                      <pre className="mt-2 whitespace-pre-wrap rounded bg-gray-900 p-2 text-gray-400">
                        {ev.content_snippet}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {finding.reasoning && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">
                Reasoning
              </h4>
              <p className="text-sm text-gray-400">{finding.reasoning}</p>
            </div>
          )}

          {/* Source files */}
          {finding.source_files.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-gray-500">
                Source Files
              </h4>
              <div className="flex flex-wrap gap-1">
                {finding.source_files.map((f) => (
                  <span key={f} className="badge bg-gray-800 text-gray-400 font-mono text-xs">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Verify buttons */}
          <div className="flex gap-2">
            <button
              className="btn-secondary text-xs"
              onClick={() => onVerify(finding.id, true)}
            >
              <CheckCircle className="mr-1 inline h-3 w-3" />
              Accept
            </button>
            <button
              className="btn-secondary text-xs"
              onClick={() => onVerify(finding.id, false)}
            >
              <XCircle className="mr-1 inline h-3 w-3" />
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FindingsPage() {
  const queryClient = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ['findings', categoryFilter, severityFilter, statusFilter],
    queryFn: () =>
      listFindings({
        category: categoryFilter || undefined,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  const verifyMutation = useMutation({
    mutationFn: ({ id, accepted }: { id: string; accepted: boolean }) =>
      verifyFinding(id, accepted),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['findings'] });
    },
  });

  const sorted = [...findings].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Findings</h1>
        <p className="mt-1 text-gray-500">
          Evidence-backed architectural findings. Filter and verify.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="input"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="">All Categories</option>
          <option value="security">Security</option>
          <option value="performance">Performance</option>
          <option value="architecture">Architecture</option>
          <option value="maintainability">Maintainability</option>
          <option value="documentation">Documentation</option>
          <option value="dependency">Dependency</option>
          <option value="complexity">Complexity</option>
        </select>

        <select
          className="input"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="">All Severities</option>
          {SEVERITY_ORDER.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          className="input"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="verified">Verified</option>
          <option value="uncertain">Uncertain</option>
          <option value="rejected">Rejected</option>
          <option value="pending">Pending</option>
        </select>

        <span className="ml-auto text-sm text-gray-500 self-center">
          {sorted.length} findings
        </span>
      </div>

      {/* Findings list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      ) : sorted.length === 0 ? (
        <div className="py-12 text-center text-gray-500">
          No findings match the current filters.
        </div>
      ) : (
        <div className="space-y-4">
          {sorted.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              onVerify={(id, accepted) =>
                verifyMutation.mutate({ id, accepted })
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
