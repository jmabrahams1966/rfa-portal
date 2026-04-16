import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { useState, useEffect, type ReactNode } from 'react';
import { authApi } from './services/api';
import LoginPage from './components/auth/LoginPage';
import Dashboard from './components/dashboard/Dashboard';
import CaseList from './components/cases/CaseList';
import CaseDetail from './components/cases/CaseDetail';
import SubmissionWizard from './components/wizard/SubmissionWizard';
import SubmissionDetail from './components/wizard/SubmissionDetail';

function RequireAuth({ children }: { children: ReactNode }) {
  if (!authApi.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const user = authApi.getUser();

  const handleLogout = () => {
    authApi.logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: DashboardIcon },
    { path: '/cases', label: 'Cases', icon: CasesIcon },
  ];

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-64' : 'w-20'} flex flex-col bg-navy-700 text-white transition-all duration-200 flex-shrink-0`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-navy-500">
          <div className="w-9 h-9 rounded-lg bg-accent-500 flex items-center justify-center font-bold text-sm flex-shrink-0">
            RFA
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <div className="font-semibold text-sm leading-tight truncate">RFA-2 Portal</div>
              <div className="text-[11px] text-navy-200 leading-tight">Workers' Comp Filing</div>
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
                  : 'text-navy-200 hover:bg-navy-600 hover:text-white'
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="px-3 py-2 text-navy-300 hover:text-white text-xs flex items-center gap-2 mx-3 mb-2 rounded hover:bg-navy-600 transition-colors"
        >
          <svg className={`w-4 h-4 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
          {sidebarOpen && <span>Collapse</span>}
        </button>

        {/* User */}
        <div className="border-t border-navy-500 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-navy-500 flex items-center justify-center text-xs font-bold flex-shrink-0">
              {user?.name?.charAt(0) || 'U'}
            </div>
            {sidebarOpen && (
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{user?.name || 'User'}</div>
                <div className="text-[11px] text-navy-300 truncate">{user?.organization || ''}</div>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className={`mt-2 text-xs text-navy-300 hover:text-red-300 transition-colors ${sidebarOpen ? '' : 'text-center w-full'}`}
          >
            {sidebarOpen ? 'Sign Out' : 'Out'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}

function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  );
}

function CasesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  );
}

export default function App() {
  const [_ready, setReady] = useState(false);

  useEffect(() => {
    // Auto-login in dev mode
    if (authApi.isAuthenticated() && !authApi.getUser()) {
      authApi.login('dev@rfaportal.com', 'dev').then(() => setReady(true));
    } else {
      setReady(true);
    }
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppShell><Dashboard /></AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/cases"
        element={
          <RequireAuth>
            <AppShell><CaseList /></AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/cases/:id"
        element={
          <RequireAuth>
            <AppShell><CaseDetail /></AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/submissions/new/:caseId"
        element={
          <RequireAuth>
            <AppShell><SubmissionWizard /></AppShell>
          </RequireAuth>
        }
      />
      <Route
        path="/submissions/:id"
        element={
          <RequireAuth>
            <AppShell><SubmissionDetail /></AppShell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
