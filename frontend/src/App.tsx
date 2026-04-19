import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { useState, useEffect, type ReactNode } from 'react';
import { authApi } from './services/api';
import LoginPage from './components/auth/LoginPage';
import Dashboard from './components/dashboard/Dashboard';
import CaseList from './components/cases/CaseList';
import CaseDetail from './components/cases/CaseDetail';
import SubmissionWizard from './components/wizard/SubmissionWizard';
import SubmissionDetail from './components/wizard/SubmissionDetail';
import Deadlines from './components/deadlines/Deadlines';
import RFAAnalytics from './components/analytics/RFAAnalytics';

// ---------- Auth guard ----------

function RequireAuth({ children }: { children: ReactNode }) {
  if (!authApi.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// ---------- Placeholder ----------

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-navy-700 mb-2">{title}</h1>
      <p className="text-sm text-gray-500 mb-8">{description}</p>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
        <div className="text-5xl mb-4 text-gray-300">&#128679;</div>
        <p className="text-lg font-semibold text-gray-600">Coming Soon</p>
      </div>
    </div>
  );
}

// ---------- Nav items ----------

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/cases', label: 'Cases', icon: '📁' },
  { path: '/deadlines', label: 'Deadlines', icon: '⏰' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

// ---------- App Shell ----------

function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const user = authApi.getUser();

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <aside className={`${sidebarOpen ? 'w-64' : 'w-20'} flex flex-col bg-[#1a1a2e] text-white transition-all duration-200 flex-shrink-0`}>
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-[#2d2d4a]">
          <div className="w-9 h-9 rounded-lg bg-accent-500 flex items-center justify-center font-bold text-sm flex-shrink-0">
            RFA
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <div className="font-semibold text-sm leading-tight truncate">AIRA</div>
              <div className="text-[11px] text-gray-400 leading-tight">Intelligent Resolution</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive(item.path)
                  ? 'bg-accent-500 text-white'
                  : 'text-gray-300 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className="text-base flex-shrink-0 w-5 text-center">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Collapse */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="px-3 py-2 text-gray-400 hover:text-white text-xs flex items-center gap-2 mx-3 mb-2 rounded hover:bg-white/10 transition-colors"
        >
          <svg className={`w-4 h-4 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
          {sidebarOpen && <span>Collapse</span>}
        </button>

        {/* User */}
        <div className="border-t border-[#2d2d4a] px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-xs font-bold flex-shrink-0">
              {(user?.full_name || 'U').charAt(0)}
            </div>
            {sidebarOpen && (
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{user?.full_name || 'User'}</div>
                <div className="text-[11px] text-gray-400 truncate capitalize">{user?.role || ''}</div>
              </div>
            )}
          </div>
          <button
            onClick={() => { authApi.logout(); navigate('/login'); }}
            className="mt-2 text-xs text-gray-400 hover:text-red-300 transition-colors"
          >
            {sidebarOpen ? 'Sign Out' : 'Out'}
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}

// ---------- App ----------

export default function App() {
  useEffect(() => {
    if (!authApi.getUser()) {
      authApi.isAuthenticated(); // triggers dev bypass auto-login
    }
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><AppShell><Dashboard /></AppShell></RequireAuth>} />
      <Route path="/cases" element={<RequireAuth><AppShell><CaseList /></AppShell></RequireAuth>} />
      <Route path="/cases/:id" element={<RequireAuth><AppShell><CaseDetail /></AppShell></RequireAuth>} />
      <Route path="/submissions/new/:caseId" element={<RequireAuth><AppShell><SubmissionWizard /></AppShell></RequireAuth>} />
      <Route path="/submissions/:id" element={<RequireAuth><AppShell><SubmissionDetail /></AppShell></RequireAuth>} />
      <Route path="/deadlines" element={<RequireAuth><AppShell><Deadlines /></AppShell></RequireAuth>} />
      <Route path="/analytics" element={<RequireAuth><AppShell><RFAAnalytics /></AppShell></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><AppShell><PlaceholderPage title="Settings" description="Organization and account settings" /></AppShell></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
