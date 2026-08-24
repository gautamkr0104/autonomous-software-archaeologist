import { Routes, Route, NavLink } from 'react-router-dom';
import {
  GitBranch,
  LayoutDashboard,
  Search,
  Network,
  FileWarning,
  MessageSquare,
  Activity,
} from 'lucide-react';
import OverviewPage from './pages/OverviewPage';
import ArchitectureGraphPage from './pages/ArchitectureGraphPage';
import CodeExplorerPage from './pages/CodeExplorerPage';
import FindingsPage from './pages/FindingsPage';
import InvestigationPage from './pages/InvestigationPage';
import AnalysisPage from './pages/AnalysisPage';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/analyze', label: 'Analyze', icon: GitBranch },
  { to: '/graph', label: 'Architecture Graph', icon: Network },
  { to: '/code', label: 'Code Explorer', icon: Search },
  { to: '/findings', label: 'Findings', icon: FileWarning },
  { to: '/investigate', label: 'AI Investigation', icon: MessageSquare },
];

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-gray-800 bg-gray-900/80">
        <div className="flex items-center gap-2 border-b border-gray-800 p-4">
          <Activity className="h-6 w-6 text-indigo-400" />
          <div>
            <h1 className="text-lg font-bold text-white">ASA</h1>
            <p className="text-xs text-gray-500">Software Archaeologist</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-400'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-800 p-4">
          <p className="text-xs text-gray-600">ASA v0.1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/analyze" element={<AnalysisPage />} />
          <Route path="/graph" element={<ArchitectureGraphPage />} />
          <Route path="/code" element={<CodeExplorerPage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/investigate" element={<InvestigationPage />} />
        </Routes>
      </main>
    </div>
  );
}
