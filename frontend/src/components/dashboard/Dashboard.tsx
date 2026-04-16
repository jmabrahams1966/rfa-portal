import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { dashboardApi, type DashboardStats, type ReasonCodeBreakdown, type RecentSubmission } from '../../services/api';
import { format } from 'date-fns';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  validating: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-blue-100 text-blue-800',
  submitted: 'bg-indigo-100 text-indigo-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
};

export default function Dashboard() {
  const navigate = useNavigate();

  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.stats,
  });

  const { data: reasonCodes } = useQuery<ReasonCodeBreakdown[]>({
    queryKey: ['dashboard-reason-codes'],
    queryFn: dashboardApi.reasonCodeBreakdown,
  });

  const { data: recent } = useQuery<RecentSubmission[]>({
    queryKey: ['dashboard-recent'],
    queryFn: dashboardApi.recentSubmissions,
  });

  const statCards = [
    { label: 'Total Cases', value: stats?.total_cases ?? 0, color: 'bg-navy-700', textColor: 'text-white' },
    { label: 'Draft Submissions', value: stats?.draft_submissions ?? 0, color: 'bg-white', textColor: 'text-navy-700', border: true },
    { label: 'Submitted', value: stats?.submitted ?? 0, color: 'bg-white', textColor: 'text-indigo-700', border: true },
    { label: 'Accepted', value: stats?.accepted ?? 0, color: 'bg-white', textColor: 'text-green-700', border: true },
    { label: 'Rejected', value: stats?.rejected ?? 0, color: 'bg-white', textColor: 'text-red-700', border: true },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-navy-700">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your RFA-2 submissions and case activity</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {statCards.map((card) => (
          <div
            key={card.label}
            className={`${card.color} ${card.border ? 'border border-gray-200' : ''} rounded-xl p-5 shadow-sm`}
          >
            <div className={`text-3xl font-bold ${card.textColor}`}>{card.value}</div>
            <div className={`text-sm mt-1 ${card.color === 'bg-navy-700' ? 'text-navy-200' : 'text-gray-500'}`}>
              {card.label}
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent submissions */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-navy-700">Recent Submissions</h2>
            <button
              onClick={() => navigate('/cases')}
              className="text-sm text-accent-500 hover:text-accent-600 font-medium"
            >
              View All Cases
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-5 py-3 font-medium">Case #</th>
                  <th className="px-5 py-3 font-medium">Claimant</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Reason Codes</th>
                  <th className="px-5 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(recent || []).map((sub) => (
                  <tr
                    key={sub.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/submissions/${sub.id}`)}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-navy-700">{sub.wcb_case_number}</td>
                    <td className="px-5 py-3 font-medium text-gray-800">{sub.claimant_name}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[sub.status] || 'bg-gray-100 text-gray-700'}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {sub.reason_codes.map((code) => (
                          <span key={code} className="px-1.5 py-0.5 bg-navy-50 text-navy-600 rounded text-xs font-mono">
                            {code}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs">
                      {sub.submitted_at
                        ? format(new Date(sub.submitted_at), 'MMM d, yyyy')
                        : format(new Date(sub.created_at), 'MMM d, yyyy')}
                    </td>
                  </tr>
                ))}
                {(!recent || recent.length === 0) && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-gray-400">
                      No submissions yet. Create a case and start filing.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Reason code breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-navy-700">Reason Code Breakdown</h2>
          </div>
          <div className="p-5 space-y-4">
            {(reasonCodes || []).map((rc) => {
              const maxCount = Math.max(...(reasonCodes || []).map((r) => r.count), 1);
              const pct = (rc.count / maxCount) * 100;
              return (
                <div key={rc.code}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-navy-700 bg-navy-50 px-1.5 py-0.5 rounded">
                        {rc.code}
                      </span>
                      <span className="text-sm text-gray-600 truncate">{rc.label}</span>
                    </div>
                    <span className="text-sm font-semibold text-navy-700 ml-2">{rc.count}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div
                      className="bg-accent-500 h-2 rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {(!reasonCodes || reasonCodes.length === 0) && (
              <p className="text-sm text-gray-400 text-center py-4">No data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
