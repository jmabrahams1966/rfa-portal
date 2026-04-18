import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { useState, useEffect, createContext, useContext, type ReactNode } from 'react';
import { authApi } from './services/api';
import LoginPage from './components/auth/LoginPage';

// Non-provider (payer/legal) components
import Dashboard from './components/dashboard/Dashboard';
import CaseList from './components/cases/CaseList';
import CaseDetail from './components/cases/CaseDetail';
import SubmissionWizard from './components/wizard/SubmissionWizard';
import SubmissionDetail from './components/wizard/SubmissionDetail';

// Provider components
import ProviderDashboard from './components/provider/ProviderDashboard';
import PriorAuthList from './components/provider/PriorAuthList';
import PriorAuthForm from './components/provider/PriorAuthForm';
import ComplianceChecker from './components/provider/ComplianceChecker';
import ProcedureLookup from './components/provider/ProcedureLookup';

// ---------- RBAC Context ----------

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

interface RBACContext {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  org_type: 'provider' | 'non_provider';
  is_provider: boolean;
  is_non_provider: boolean;
  is_super_admin: boolean;
  navigation: NavItem[];
  features: string[];
}

const PROVIDER_CONTEXT: RBACContext = {
  user_id: 'dev-001',
  email: 'dev@provider.com',
  full_name: 'Dr. Dev Surgeon',
  role: 'surgeon',
  org_type: 'provider',
  is_provider: true,
  is_non_provider: false,
  is_super_admin: false,
  navigation: [
    { path: '/', label: 'Dashboard', icon: '\uD83D\uDCCA' },
    { path: '/prior-auth', label: 'Prior Authorizations', icon: '\uD83D\uDCCB' },
    { path: '/compliance', label: 'Compliance Checker', icon: '\u2705' },
    { path: '/cases', label: 'Cases', icon: '\uD83D\uDCC1' },
    { path: '/guidelines', label: 'Payer Guidelines', icon: '\uD83D\uDCD6' },
    { path: '/analytics', label: 'Analytics', icon: '\uD83D\uDCC8' },
  ],
  features: ['prior_auth.create', 'prior_auth.submit', 'prior_auth.view', 'compliance.check', 'narrative.generate', 'narrative.optimize'],
};

const NON_PROVIDER_CONTEXT: RBACContext = {
  user_id: 'dev-002',
  email: 'dev@carrier.com',
  full_name: 'Dev Adjuster',
  role: 'adjuster',
  org_type: 'non_provider',
  is_provider: false,
  is_non_provider: true,
  is_super_admin: false,
  navigation: [
    { path: '/', label: 'Dashboard', icon: '\uD83D\uDCCA' },
    { path: '/cases', label: 'Cases', icon: '\uD83D\uDCC1' },
    { path: '/submissions', label: 'RFA Filings', icon: '\uD83D\uDCC4' },
    { path: '/deadlines', label: 'Deadlines', icon: '\u23F0' },
    { path: '/analytics', label: 'Analytics', icon: '\uD83D\uDCC8' },
  ],
  features: ['cases.view', 'cases.create', 'submissions.view', 'submissions.create', 'deadlines.view'],
};

const RBACCtx = createContext<{ rbac: RBACContext; setOrgType: (t: 'provider' | 'non_provider') => void }>({
  rbac: PROVIDER_CONTEXT,
  setOrgType: () => {},
});

export function useRBAC() {
  return useContext(RBACCtx);
}

// ---------- Auth guard ----------

function RequireAuth({ children }: { children: ReactNode }) {
  if (!authApi.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// ---------- Placeholder pages ----------

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-navy-700 mb-2">{title}</h1>
      <p className="text-sm text-gray-500 mb-8">{description}</p>
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
        <div className="text-5xl mb-4 text-gray-300">&#128679;</div>
        <p className="text-lg font-semibold text-gray-600">Coming Soon</p>
        <p className="text-sm text-gray-400 mt-2">This feature is under development.</p>
      </div>
    </div>
  );
}

// ---------- App Shell ----------

function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { rbac, setOrgType } = useRBAC();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    authApi.logout();
    navigate('/login');
  };

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  const portalLabel = rbac.is_provider ? 'RFA Portal \u2014 Provider' : 'RFA Portal \u2014 Payer/Legal';
  const portalSubLabel = rbac.is_provider ? 'Prior Authorization' : 'Workers\' Comp Filing';
  const sidebarBg = rbac.is_provider ? 'bg-[#0F2044]' : 'bg-[#1a1a2e]';
  const borderColor = rbac.is_provider ? 'border-[#1a3a6e]' : 'border-[#2d2d4a]';

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-64' : 'w-20'} flex flex-col ${sidebarBg} text-white transition-all duration-200 flex-shrink-0`}
      >
        {/* Brand */}
        <div className={`flex items-center gap-3 px-5 py-5 border-b ${borderColor}`}>
          <div className="w-9 h-9 rounded-lg bg-accent-500 flex items-center justify-center font-bold text-sm flex-shrink-0">
            RFA
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <div className="font-semibold text-sm leading-tight truncate">{portalLabel}</div>
              <div className="text-[11px] text-gray-400 leading-tight">{portalSubLabel}</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {(rbac.navigation || []).map((item) => (
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

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className={`px-3 py-2 text-gray-400 hover:text-white text-xs flex items-center gap-2 mx-3 mb-2 rounded hover:bg-white/10 transition-colors`}
        >
          <svg className={`w-4 h-4 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
          {sidebarOpen && <span>Collapse</span>}
        </button>

        {/* User */}
        <div className={`border-t ${borderColor} px-4 py-3`}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-xs font-bold flex-shrink-0">
              {(rbac.full_name || 'U').charAt(0)}
            </div>
            {sidebarOpen && (
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{rbac.full_name || 'User'}</div>
                <div className="text-[11px] text-gray-400 truncate capitalize">{rbac.role || ''}</div>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className={`mt-2 text-xs text-gray-400 hover:text-red-300 transition-colors ${sidebarOpen ? '' : 'text-center w-full'}`}
          >
            {sidebarOpen ? 'Sign Out' : 'Out'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {/* View Toggle Bar */}
        <div className="bg-white border-b border-gray-200 px-6 py-3">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">Portal View:</span>
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setOrgType('provider')}
                  className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                    rbac.is_provider
                      ? 'bg-[#0F2044] text-white shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  🏥 Provider
                </button>
                <button
                  onClick={() => setOrgType('non_provider')}
                  className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${
                    rbac.is_non_provider
                      ? 'bg-[#1a1a2e] text-white shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  ⚖️ Payer / Legal
                </button>
              </div>
            </div>
            <div className="text-xs text-gray-400">
              {rbac.is_provider ? 'Prior Authorization & Compliance' : 'Workers\' Comp RFA Filing'}
            </div>
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}

// ---------- Provider Routes ----------

function ProviderRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppShell><ProviderDashboard /></AppShell>} />
      <Route path="/prior-auth" element={<AppShell><PriorAuthList /></AppShell>} />
      <Route path="/prior-auth/new" element={<AppShell><PriorAuthForm /></AppShell>} />
      <Route path="/prior-auth/:id" element={<AppShell><PriorAuthForm /></AppShell>} />
      <Route path="/compliance" element={<AppShell><ComplianceChecker /></AppShell>} />
      <Route path="/cases" element={<AppShell><CaseList /></AppShell>} />
      <Route path="/cases/:id" element={<AppShell><CaseDetail /></AppShell>} />
      <Route path="/guidelines" element={<AppShell><ProcedureLookup /></AppShell>} />
      <Route path="/analytics" element={<AppShell><PlaceholderPage title="Analytics" description="Prior authorization approval rates, turnaround times, and compliance trends" /></AppShell>} />
      <Route path="/settings" element={<AppShell><PlaceholderPage title="Settings" description="Account and organization settings" /></AppShell>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// ---------- Non-Provider Routes ----------

function NonProviderRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppShell><Dashboard /></AppShell>} />
      <Route path="/cases" element={<AppShell><CaseList /></AppShell>} />
      <Route path="/cases/:id" element={<AppShell><CaseDetail /></AppShell>} />
      <Route path="/submissions/new/:caseId" element={<AppShell><SubmissionWizard /></AppShell>} />
      <Route path="/submissions/:id" element={<AppShell><SubmissionDetail /></AppShell>} />
      <Route path="/submissions" element={<AppShell><PlaceholderPage title="RFA Filings" description="View and manage all RFA-2 filings and submissions" /></AppShell>} />
      <Route path="/deadlines" element={<AppShell><PlaceholderPage title="Deadlines" description="Track upcoming filing deadlines and compliance windows" /></AppShell>} />
      <Route path="/analytics" element={<AppShell><PlaceholderPage title="Analytics" description="Submission metrics, acceptance rates, and case trends" /></AppShell>} />
      <Route path="/settings" element={<AppShell><PlaceholderPage title="Settings" description="Account and organization settings" /></AppShell>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// ---------- App ----------

export default function App() {
  const [_ready, setReady] = useState(false);
  const [rbac, setRbac] = useState<RBACContext>(PROVIDER_CONTEXT);

  const setOrgType = (orgType: 'provider' | 'non_provider') => {
    if (orgType === 'provider') {
      setRbac(PROVIDER_CONTEXT);
    } else {
      setRbac(NON_PROVIDER_CONTEXT);
    }
  };

  useEffect(() => {
    // Auto-login in dev mode
    if (authApi.isAuthenticated() && !authApi.getUser()) {
      authApi.login('dev@rfaportal.com', 'dev').then(() => setReady(true));
    } else {
      setReady(true);
    }

    // Try to fetch real RBAC context, fall back to mock
    fetch('/api/rbac/context/')
      .then((res) => {
        if (!res.ok) throw new Error('RBAC endpoint not available');
        return res.json();
      })
      .then((data) => {
        if (data && data.org_type) {
          setRbac({
            user_id: data.user_id || 'dev-001',
            email: data.email || '',
            full_name: data.full_name || '',
            role: data.role || '',
            org_type: data.org_type,
            is_provider: data.is_provider ?? data.org_type === 'provider',
            is_non_provider: data.is_non_provider ?? data.org_type === 'non_provider',
            is_super_admin: data.is_super_admin ?? false,
            navigation: data.navigation || [],
            features: data.features || [],
          });
        }
      })
      .catch(() => {
        // Use mock context — already set as default
      });
  }, []);

  return (
    <RBACCtx.Provider value={{ rbac, setOrgType }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              {rbac.is_provider ? <ProviderRoutes /> : <NonProviderRoutes />}
            </RequireAuth>
          }
        />
      </Routes>
    </RBACCtx.Provider>
  );
}
