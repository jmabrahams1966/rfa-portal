import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { providerApi, type ProviderDashboardData, type AuthRequest } from '../../services/api';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  submitted: 'bg-indigo-100 text-indigo-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  denied: 'bg-red-100 text-red-800',
  appealed: 'bg-orange-100 text-orange-800',
};

const urgencyColors: Record<string, string> = {
  routine: 'text-gray-600',
  urgent: 'text-amber-600',
  emergent: 'text-red-600',
};

export default function ProviderDashboard() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<ProviderDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    providerApi.dashboard().then((data) => {
      setDashboard(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const kpiCards = [
    { label: 'Pending Auths', value: dashboard?.pending_auths ?? 0, color: 'bg-navy-700', textColor: 'text-white', subColor: 'text-navy-200' },
    { label: 'Awaiting Decision', value: dashboard?.awaiting_decision ?? 0, color: 'bg-white', textColor: 'text-amber-700', border: true, subColor: 'text-gray-500' },
    { label: 'Approved This Month', value: dashboard?.approved_this_month ?? 0, color: 'bg-white', textColor: 'text-green-700', border: true, subColor: 'text-gray-500' },
    { label: 'Denied This Month', value: dashboard?.denied_this_month ?? 0, color: 'bg-white', textColor: 'text-red-700', border: true, subColor: 'text-gray-500' },
    { label: 'Approval Rate', value: `${dashboard?.approval_rate ?? 0}%`, color: 'bg-white', textColor: 'text-navy-700', border: true, subColor: 'text-gray-500' },
  ];

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-navy-700">Provider Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Prior authorization requests and compliance overview</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/compliance')}
            className="px-4 py-2.5 bg-white border border-gray-300 text-navy-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Compliance Checker
          </button>
          <button
            onClick={() => navigate('/prior-auth/new')}
            className="px-4 py-2.5 bg-accent-500 text-white text-sm font-medium rounded-lg hover:bg-accent-600 transition-colors"
          >
            + New Prior Auth
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {kpiCards.map((card) => (
          <div
            key={card.label}
            className={`${card.color} ${card.border ? 'border border-gray-200' : ''} rounded-xl p-5 shadow-sm`}
          >
            <div className={`text-3xl font-bold ${card.textColor}`}>{card.value}</div>
            <div className={`text-sm mt-1 ${card.subColor}`}>{card.label}</div>
          </div>
        ))}
      </div>

      {/* Compliance Score */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-navy-700">Average Compliance Score</h2>
            <p className="text-sm text-gray-500 mt-0.5">Across all authorization requests with compliance data</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-48 bg-gray-100 rounded-full h-3">
              <div
                className="h-3 rounded-full transition-all"
                style={{
                  width: `${dashboard?.compliance_score ?? 0}%`,
                  backgroundColor: (dashboard?.compliance_score ?? 0) >= 80 ? '#16a34a' : (dashboard?.compliance_score ?? 0) >= 60 ? '#d97706' : '#dc2626',
                }}
              />
            </div>
            <span className="text-2xl font-bold text-navy-700">{dashboard?.compliance_score ?? 0}%</span>
          </div>
        </div>
      </div>

      {/* Recent Auth Requests */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-navy-700">Recent Authorization Requests</h2>
          <button
            onClick={() => navigate('/prior-auth')}
            className="text-sm text-accent-500 hover:text-accent-600 font-medium"
          >
            View All
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 text-xs uppercase tracking-wider">
                <th className="px-5 py-3 font-medium">Patient</th>
                <th className="px-5 py-3 font-medium">Procedure</th>
                <th className="px-5 py-3 font-medium">Payer</th>
                <th className="px-5 py-3 font-medium">Urgency</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Score</th>
                <th className="px-5 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {(dashboard?.recent_auths || []).map((auth: AuthRequest) => (
                <tr
                  key={auth.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/prior-auth/${auth.id}`)}
                >
                  <td className="px-5 py-3">
                    <div className="font-medium text-gray-800">{auth.patient_name}</div>
                    <div className="text-xs text-gray-400">{auth.patient_mrn}</div>
                  </td>
                  <td className="px-5 py-3">
                    <div className="text-gray-800">{auth.procedure_name}</div>
                    <div className="text-xs text-gray-400 font-mono">{auth.cpt_code}</div>
                  </td>
                  <td className="px-5 py-3 text-gray-700">{auth.payer}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs font-medium capitalize ${urgencyColors[auth.clinical_urgency] || 'text-gray-600'}`}>
                      {auth.clinical_urgency}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[auth.status] || 'bg-gray-100 text-gray-700'}`}>
                      {auth.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    {auth.compliance_score !== null ? (
                      <span className={`text-sm font-semibold ${auth.compliance_score >= 80 ? 'text-green-600' : auth.compliance_score >= 60 ? 'text-amber-600' : 'text-red-600'}`}>
                        {auth.compliance_score}%
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">--</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {(auth.submitted_at || auth.created_at || '').slice(0, 10)}
                  </td>
                </tr>
              ))}
              {(!dashboard?.recent_auths || dashboard.recent_auths.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-gray-400">
                    No authorization requests yet. Create one to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
