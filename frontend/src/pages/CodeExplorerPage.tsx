import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FileText,
  ChevronRight,
  ChevronDown,
  Code,
  Box,
  Import,
  ArrowRight,
} from 'lucide-react';
import { listAnalyses, getAnalysis } from '../services/api';
import type { ProjectAnalysis, FileAnalysis, FunctionInfo, ClassInfo } from '../types';

function FileTree({
  files,
  onSelect,
  selected,
}: {
  files: FileAnalysis[];
  onSelect: (f: FileAnalysis) => void;
  selected: string;
}) {
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());

  // Build directory tree
  const dirs = new Map<string, FileAnalysis[]>();
  for (const f of files) {
    const parts = f.file_path.split('/');
    if (parts.length > 1) {
      const dir = parts[0];
      if (!dirs.has(dir)) dirs.set(dir, []);
      dirs.get(dir)!.push({ ...f, file_path: parts.slice(1).join('/') });
    } else {
      if (!dirs.has('__root__')) dirs.set('__root__', []);
      dirs.get('__root__')!.push(f);
    }
  }

  const toggleDir = (dir: string) => {
    const next = new Set(expandedDirs);
    if (next.has(dir)) next.delete(dir);
    else next.add(dir);
    setExpandedDirs(next);
  };

  return (
    <div className="overflow-y-auto text-sm">
      {Array.from(dirs.entries()).map(([dir, dirFiles]) => (
        <div key={dir}>
          {dir !== '__root__' && (
            <button
              className="flex w-full items-center gap-1 px-2 py-1 text-gray-400 hover:bg-gray-800"
              onClick={() => toggleDir(dir)}
            >
              {expandedDirs.has(dir) ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              <span className="font-mono">{dir}</span>
            </button>
          )}
          {(dir === '__root__' || expandedDirs.has(dir)) &&
            dirFiles.map((f) => (
              <button
                key={f.file_path}
                className={`flex w-full items-center gap-2 pl-6 pr-2 py-1 font-mono text-xs ${
                  selected === f.file_path
                    ? 'bg-indigo-600/20 text-indigo-400'
                    : 'text-gray-400 hover:bg-gray-800'
                }`}
                onClick={() => onSelect(f)}
              >
                <FileText className="h-3 w-3 shrink-0" />
                <span className="truncate">{f.file_path}</span>
              </button>
            ))}
        </div>
      ))}
    </div>
  );
}

function SymbolPanel({ file }: { file: FileAnalysis }) {
  return (
    <div className="space-y-4 overflow-y-auto p-4">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <FileText className="h-4 w-4" />
        <span className="font-mono">{file.file_path}</span>
        <span className="badge bg-gray-800">{file.language}</span>
        {file.is_test && <span className="badge bg-pink-500/20 text-pink-400">test</span>}
        {file.is_config && (
          <span className="badge bg-gray-500/20 text-gray-400">config</span>
        )}
      </div>

      <div className="flex gap-4 text-xs text-gray-500">
        <span>{file.lines_of_code} LOC</span>
        <span>{file.lines_of_comments} comments</span>
        <span>{file.classes.length} classes</span>
        <span>{file.functions.length} functions</span>
      </div>

      {/* Imports */}
      {file.imports.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500">
            Imports ({file.imports.length})
          </h4>
          <div className="space-y-1">
            {file.imports.map((imp) => (
              <div
                key={imp.id}
                className="flex items-center gap-2 rounded bg-gray-800/50 px-2 py-1 text-xs"
              >
                <Import className="h-3 w-3 text-indigo-400" />
                <span className="font-mono text-gray-300">
                  {imp.is_relative ? '.' : ''}
                  {imp.module}
                </span>
                {imp.names.length > 0 && (
                  <span className="text-gray-600">
                    {'{' + imp.names.join(', ') + '}'}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Classes */}
      {file.classes.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500">
            Classes ({file.classes.length})
          </h4>
          <div className="space-y-2">
            {file.classes.map((cls) => (
              <ClassCard key={cls.id} cls={cls} />
            ))}
          </div>
        </div>
      )}

      {/* Functions */}
      {file.functions.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500">
            Functions ({file.functions.length})
          </h4>
          <div className="space-y-1">
            {file.functions.map((fn) => (
              <FunctionCard key={fn.id} fn={fn} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ClassCard({ cls }: { cls: ClassInfo }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-gray-800 bg-gray-800/30">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs"
        onClick={() => setExpanded(!expanded)}
      >
        <Box className="h-3 w-3 text-cyan-400" />
        <span className="font-mono text-cyan-300">{cls.name}</span>
        {cls.bases.length > 0 && (
          <span className="text-gray-600">
            extends {cls.bases.join(', ')}
          </span>
        )}
        <span className="ml-auto text-gray-600">
          {cls.methods.length} methods
        </span>
      </button>
      {expanded && (
        <div className="border-t border-gray-800 px-3 py-2">
          {cls.methods.map((m) => (
            <FunctionCard key={m.id} fn={m} />
          ))}
        </div>
      )}
    </div>
  );
}

function FunctionCard({ fn }: { fn: FunctionInfo }) {
  return (
    <div className="flex items-center gap-2 rounded bg-gray-800/30 px-2 py-1 text-xs">
      <Code className="h-3 w-3 text-green-400" />
      {fn.is_async && <span className="text-purple-400">async</span>}
      <span className="font-mono text-green-300">{fn.name}</span>
      <span className="text-gray-600">
        ({fn.parameters.map((p) => p.name).join(', ')})
      </span>
      {fn.return_type && (
        <>
          <ArrowRight className="h-2 w-2 text-gray-600" />
          <span className="text-gray-500">{fn.return_type}</span>
        </>
      )}
    </div>
  );
}

export default function CodeExplorerPage() {
  const [selectedFile, setSelectedFile] = useState<FileAnalysis | null>(null);

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
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        No analysis available. Run an analysis first.
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* File tree sidebar */}
      <div className="w-72 border-r border-gray-800 bg-gray-900/50">
        <div className="border-b border-gray-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-white">Files</h3>
          <p className="text-xs text-gray-500">
            {project.file_analyses.length} files
          </p>
        </div>
        <FileTree
          files={project.file_analyses}
          onSelect={setSelectedFile}
          selected={selectedFile?.file_path ?? ''}
        />
      </div>

      {/* Symbol panel */}
      <div className="flex-1 overflow-y-auto">
        {selectedFile ? (
          <SymbolPanel file={selectedFile} />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-500">
            Select a file to explore
          </div>
        )}
      </div>
    </div>
  );
}
