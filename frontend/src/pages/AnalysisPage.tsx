import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { GitBranch, Play, Clock, CheckCircle, XCircle } from 'lucide-react';
import { startAnalysis, getAnalysis } from '../services/api';

export default function AnalysisPage() {
  const queryClient = useQueryClient();
  const [source, setSource] = useState('');
  const [commitRef, setCommitRef] = useState('');
  const [branch, setBranch] = useState('');
  const [activeAnalysis, setActiveAnalysis] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ['analysis', activeAnalysis],
    queryFn: () => getAnalysis(activeAnalysis!),
    enabled: !!activeAnalysis,
    refetchInterval: (data) =>
      data?.status === 'completed' || data?.status === 'failed' ? false : 2000,
  });

  const mutation = useMutation({
    mutationFn: startAnalysis,
    onSuccess: (data) => {
      setActiveAnalysis(data.id);
      queryClient.invalidateQueries({ queryKey: ['analyses'] });
    },
  });

  const handleSubmit = () => {
    if (!source.trim()) return;

    const isUrl = source.startsWith('http') || source.startsWith('git@');
    mutation.mutate({
      url: isUrl ? source : undefined,
      local_path: isUrl ? undefined : source,
      commit_ref: commitRef || undefined,
      branch: branch || undefined,
    });
  };

  const isRunning = status?.status === 'running' || status?.status === 'pending';

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Analyze Repository</h1>
        <p className="mt-1 text-gray-500">
          Enter a GitHub URL or local path to begin analysis.
        </p>
      </div>

      {/* Input form */}
      <div className="card space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-1">
            Repository Source
          </label>
          <input
            type="text"
            className="input w-full"
            placeholder="https://github.com/user/repo or /path/to/local/repo"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Branch (optional)
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Commit (optional)
            </label>
            <input
              type="text"
              className="input w-full"
              placeholder="abc123"
              value={commitRef}
              onChange={(e) => setCommitRef(e.target.value)}
            />
          </div>
        </div>

        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleSubmit}
          disabled={!source.trim() || isRunning}
        >
          {isRunning ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Start Analysis
            </>
          )}
        </button>
      </div>

      {/* Status */}
      {status && (
        <div className="card">
          <div className="flex items-center gap-3">
            {status.status === 'completed' && (
              <CheckCircle className="h-5 w-5 text-green-400" />
            )}
            {status.status === 'failed' && (
              <XCircle className="h-5 w-5 text-red-400" />
            )}
            {(status.status === 'running' || status.status === 'pending') && (
              <Clock className="h-5 w-5 text-yellow-400 animate-pulse" />
            )}
            <div>
              <p className="font-medium text-white">
                Analysis {status.status}
              </p>
              {status.error && (
                <p className="text-sm text-red-400">{status.error}</p>
              )}
              {status.result && (
                <p className="text-sm text-gray-500">
                  {status.result.file_analyses?.length ?? 0} files analyzed
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
