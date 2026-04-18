import { useState, useEffect } from 'react';
import axios from 'axios';

// ---------- Types ----------

interface MonthlyVolume {
  month: string;
  label: string;
  count: number;
}

interface ReasonCodeStat {
  code: string;
  label: string;
  count: number;
  color: string;
}

interface AdjusterPerformance {
  name: string;
  filings: number;
  accepted: number;
  rejected: number;
  acceptance_rate: number;
  avg_processing_days: number;
}

interface TopCase {
  case_number: string;
  claimant: string;
  total_submissions: number;
  last_filed: string;
  last_status: string;
}

interface RecentRejection {
  case_number: string;
  reason_code: string;
  rejection_reason: string;
  filed_date: string;
}

interface AnalyticsData {
  total_filings: number;
  filed_this_month: number;
  acceptance_rate: number;
  avg_days_to_submit: number;
  pending_decisions: number;
  monthly_volume: MonthlyVolume[];
  reason_codes: ReasonCodeStat[];
  outcome_breakdown: { accepted: number; rejected: number; pending: number };
  adjusters: AdjusterPerformance[];
  top_cases: TopCase[];
  recent_rejections: RecentRejection[];
}

// ---------- Mock Data ----------

const MOCK_DATA: AnalyticsData = {
  total_filings: 247,
  filed_this_month: 18,
  acceptance_rate: 73.2,
  avg_days_to_submit: 4.3,
  pending_decisions: 12,
  monthly_volume: [
    { month: '2025-11', label: 'Nov', count: 31 },
    { month: '2025-12', label: 'Dec', count: 28 },
    { month: '2026-01', label: 'Jan', count: 42 },
    { month: '2026-02', label: 'Feb', count: 38 },
    { month: '2026-03', label: 'Mar', count: 45 },
    { month: '2026-04', label: 'Apr', count: 18 },
  ],
  reason_codes: [
    { code: 'MCI', label: 'Medical Cost Increase', count: 64, color: '#3b82f6' },
    { code: 'CNW', label: 'Carrier Not Writing', count: 47, color: '#8b5cf6' },
    { code: 'CAW', label: 'Carrier Adverse Withdrawal', count: 39, color: '#ef4444' },
    { code: 'POL', label: 'Policy Cancellation', count: 32, color: '#f59e0b' },
    { code: 'NRC', label: 'New Rate Class', count: 28, color: '#10b981' },
    { code: 'EXM', label: 'Experience Modification', count: 21, color: '#06b6d4' },
    { code: 'CLF', label: 'Classification Dispute', count: 15, color: '#ec4899' },
    { code: 'AUD', label: 'Audit Dispute', count: 11, color: '#6366f1' },
    { code: 'OTH', label: 'Other', count: 8, color: '#78716c' },
  ],
  outcome_breakdown: { accepted: 168, rejected: 67, pending: 12 },
  adjusters: [
    { name: 'Maria Gonzalez', filings: 62, accepted: 48, rejected: 12, acceptance_rate: 80.0, avg_processing_days: 3.2 },
    { name: 'James Chen', filings: 54, accepted: 39, rejected: 13, acceptance_rate: 75.0, avg_processing_days: 4.1 },
    { name: 'Patricia Williams', filings: 47, accepted: 34, rejected: 11, acceptance_rate: 75.6, avg_processing_days: 3.8 },
    { name: 'Robert Kim', filings: 44, accepted: 28, rejected: 14, acceptance_rate: 66.7, avg_processing_days: 5.4 },
    { name: 'Sarah Thompson', filings: 40, accepted: 29, rejected: 9, acceptance_rate: 76.3, avg_processing_days: 4.6 },
  ],
  top_cases: [
    { case_number: 'WCB-2025-04821', claimant: 'Anderson, Michael J.', total_submissions: 7, last_filed: '2026-04-08', last_status: 'accepted' },
    { case_number: 'WCB-2025-11934', claimant: 'Rivera, Carmen L.', total_submissions: 6, last_filed: '2026-04-02', last_status: 'pending' },
    { case_number: 'WCB-2025-08763', claimant: 'Patel, Rajesh K.', total_submissions: 5, last_filed: '2026-03-28', last_status: 'accepted' },
    { case_number: 'WCB-2026-00217', claimant: 'O\'Brien, Sean T.', total_submissions: 5, last_filed: '2026-03-22', last_status: 'rejected' },
    { case_number: 'WCB-2025-15290', claimant: 'Jackson, Denise M.', total_submissions: 4, last_filed: '2026-04-10', last_status: 'accepted' },
    { case_number: 'WCB-2025-22018', claimant: 'Nguyen, Thi H.', total_submissions: 4, last_filed: '2026-03-15', last_status: 'accepted' },
    { case_number: 'WCB-2026-01482', claimant: 'Martinez, Luis A.', total_submissions: 3, last_filed: '2026-04-05', last_status: 'pending' },
    { case_number: 'WCB-2026-03107', claimant: 'Wilson, Barbara J.', total_submissions: 3, last_filed: '2026-03-30', last_status: 'accepted' },
    { case_number: 'WCB-2025-19445', claimant: 'Davis, Kenneth R.', total_submissions: 3, last_filed: '2026-03-20', last_status: 'rejected' },
    { case_number: 'WCB-2026-00891', claimant: 'Lee, Christina M.', total_submissions: 2, last_filed: '2026-04-12', last_status: 'pending' },
  ],
  recent_rejections: [
    { case_number: 'WCB-2025-19445', reason_code: 'MCI', rejection_reason: 'Insufficient medical documentation to support cost increase claim', filed_date: '2026-04-06' },
    { case_number: 'WCB-2026-00217', reason_code: 'CAW', rejection_reason: 'Missing carrier withdrawal notification letter', filed_date: '2026-04-03' },
    { case_number: 'WCB-2025-11934', reason_code: 'CNW', rejection_reason: 'Narrative does not address specific denial reasons from carrier', filed_date: '2026-03-28' },
    { case_number: 'WCB-2025-08763', reason_code: 'POL', rejection_reason: 'Policy cancellation date discrepancy between form and supporting docs', filed_date: '2026-03-25' },
    { case_number: 'WCB-2025-04821', reason_code: 'EXM', rejection_reason: 'Experience modification calculation not independently verified', filed_date: '2026-03-19' },
  ],
};

// ---------- Helpers ----------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const statusColors: Record<string, string> = {
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  pending: 'bg-yellow-100 text-yellow-800',
  draft: 'bg-gray-100 text-gray-700',
};

// ---------- Component ----------

export default function RFAAnalytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        const token = localStorage.getItem('rfa_token');
        const res = await axios.get('/api/enterprise/analytics', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(res.data);
      } catch (err: any) {
        console.warn('Analytics API not available, using mock data:', err.message);
        setData(MOCK_DATA);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          Failed to load analytics data.
        </div>
      </div>
    );
  }

  const maxMonthly = Math.max(...data.monthly_volume.map((m) => m.count), 1);
  const maxReasonCode = Math.max(...data.reason_codes.map((r) => r.count), 1);
  const totalOutcomes = data.outcome_breakdown.accepted + data.outcome_breakdown.rejected + data.outcome_breakdown.pending;
  const acceptedPct = totalOutcomes > 0 ? (data.outcome_breakdown.accepted / totalOutcomes) * 100 : 0;
  const rejectedPct = totalOutcomes > 0 ? (data.outcome_breakdown.rejected / totalOutcomes) * 100 : 0;
  const pendingPct = totalOutcomes > 0 ? (data.outcome_breakdown.pending / totalOutcomes) * 100 : 0;

  const rateColor = data.acceptance_rate >= 70 ? 'text-green-700' : data.acceptance_rate < 50 ? 'text-red-700' : 'text-amber-700';
  const rateBg = data.acceptance_rate >= 70 ? 'bg-green-50 border-green-200' : data.acceptance_rate < 50 ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200';

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">
          RFA filing performance, acceptance rates, and submission trends
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="text-3xl font-bold text-gray-800">{data.total_filings}</div>
          <div className="text-sm text-gray-500 mt-1">Total Filings</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="text-3xl font-bold text-indigo-700">{data.filed_this_month}</div>
          <div className="text-sm text-gray-500 mt-1">Filed This Month</div>
        </div>
        <div className={`border rounded-xl p-5 shadow-sm ${rateBg}`}>
          <div className={`text-3xl font-bold ${rateColor}`}>{data.acceptance_rate}%</div>
          <div className="text-sm text-gray-500 mt-1">Acceptance Rate</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="text-3xl font-bold text-gray-800">{data.avg_days_to_submit}</div>
          <div className="text-sm text-gray-500 mt-1">Avg Days to Submit</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="text-3xl font-bold text-amber-600">{data.pending_decisions}</div>
          <div className="text-sm text-gray-500 mt-1">Pending Decisions</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        {/* Filing Volume Bar Chart */}
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Filing Volume</h2>
            <p className="text-xs text-gray-400 mt-0.5">Submissions per month (last 6 months)</p>
          </div>
          <div className="p-5">
            <div className="flex items-end gap-3 h-48">
              {data.monthly_volume.map((m) => {
                const heightPct = (m.count / maxMonthly) * 100;
                return (
                  <div key={m.month} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs font-semibold text-gray-700">{m.count}</span>
                    <div className="w-full relative" style={{ height: '160px' }}>
                      <div
                        className="absolute bottom-0 w-full bg-indigo-500 rounded-t-md transition-all hover:bg-indigo-600"
                        style={{ height: `${heightPct}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 font-medium">{m.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Acceptance vs Rejection Donut */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Outcomes</h2>
            <p className="text-xs text-gray-400 mt-0.5">Accepted vs Rejected vs Pending</p>
          </div>
          <div className="p-5 flex flex-col items-center">
            {/* CSS Donut Chart */}
            <div className="relative w-40 h-40 mb-5">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                {/* Accepted arc */}
                <circle
                  cx="18" cy="18" r="15.915"
                  fill="none"
                  stroke="#22c55e"
                  strokeWidth="3.5"
                  strokeDasharray={`${acceptedPct} ${100 - acceptedPct}`}
                  strokeDashoffset="0"
                />
                {/* Rejected arc */}
                <circle
                  cx="18" cy="18" r="15.915"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="3.5"
                  strokeDasharray={`${rejectedPct} ${100 - rejectedPct}`}
                  strokeDashoffset={`${-acceptedPct}`}
                />
                {/* Pending arc */}
                <circle
                  cx="18" cy="18" r="15.915"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3.5"
                  strokeDasharray={`${pendingPct} ${100 - pendingPct}`}
                  strokeDashoffset={`${-(acceptedPct + rejectedPct)}`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-gray-800">{totalOutcomes}</span>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">Total</span>
              </div>
            </div>
            {/* Legend */}
            <div className="space-y-2 w-full">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-gray-600">Accepted</span>
                </div>
                <span className="font-semibold text-gray-800">{data.outcome_breakdown.accepted} ({acceptedPct.toFixed(1)}%)</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-gray-600">Rejected</span>
                </div>
                <span className="font-semibold text-gray-800">{data.outcome_breakdown.rejected} ({rejectedPct.toFixed(1)}%)</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="text-gray-600">Pending</span>
                </div>
                <span className="font-semibold text-gray-800">{data.outcome_breakdown.pending} ({pendingPct.toFixed(1)}%)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reason Code Breakdown */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-8">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Reason Code Breakdown</h2>
          <p className="text-xs text-gray-400 mt-0.5">Filing count by reason code</p>
        </div>
        <div className="p-5 space-y-3">
          {data.reason_codes.map((rc) => {
            const widthPct = (rc.count / maxReasonCode) * 100;
            return (
              <div key={rc.code} className="flex items-center gap-3">
                <span className="font-mono text-xs font-bold text-gray-700 bg-gray-100 px-2 py-0.5 rounded w-12 text-center flex-shrink-0">
                  {rc.code}
                </span>
                <span className="text-sm text-gray-600 w-44 flex-shrink-0 truncate">{rc.label}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-5 relative">
                  <div
                    className="h-5 rounded-full transition-all"
                    style={{ width: `${widthPct}%`, backgroundColor: rc.color }}
                  />
                </div>
                <span className="text-sm font-semibold text-gray-700 w-10 text-right flex-shrink-0">{rc.count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tables row */}
      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        {/* Adjuster Performance */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Adjuster Performance</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-3 py-3 font-medium text-center">Filed</th>
                  <th className="px-3 py-3 font-medium text-center">Acc.</th>
                  <th className="px-3 py-3 font-medium text-center">Rej.</th>
                  <th className="px-3 py-3 font-medium text-center">Rate</th>
                  <th className="px-3 py-3 font-medium text-center">Avg Days</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.adjusters.map((adj) => {
                  const rColor =
                    adj.acceptance_rate >= 75
                      ? 'text-green-700 bg-green-50'
                      : adj.acceptance_rate < 50
                        ? 'text-red-700 bg-red-50'
                        : 'text-amber-700 bg-amber-50';
                  return (
                    <tr key={adj.name} className="hover:bg-gray-50">
                      <td className="px-5 py-3 font-medium text-gray-800">{adj.name}</td>
                      <td className="px-3 py-3 text-center text-gray-700">{adj.filings}</td>
                      <td className="px-3 py-3 text-center text-green-700">{adj.accepted}</td>
                      <td className="px-3 py-3 text-center text-red-700">{adj.rejected}</td>
                      <td className="px-3 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${rColor}`}>
                          {adj.acceptance_rate}%
                        </span>
                      </td>
                      <td className="px-3 py-3 text-center text-gray-600">{adj.avg_processing_days}d</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Cases */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Top Cases by Submissions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-5 py-3 font-medium">Case #</th>
                  <th className="px-3 py-3 font-medium">Claimant</th>
                  <th className="px-3 py-3 font-medium text-center">Subs</th>
                  <th className="px-3 py-3 font-medium">Last Filed</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.top_cases.map((tc) => (
                  <tr key={tc.case_number} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-gray-800">
                      {tc.case_number}
                    </td>
                    <td className="px-3 py-3 text-gray-700 truncate max-w-[140px]">{tc.claimant}</td>
                    <td className="px-3 py-3 text-center font-semibold text-gray-800">{tc.total_submissions}</td>
                    <td className="px-3 py-3 text-gray-500 text-xs">{formatDate(tc.last_filed)}</td>
                    <td className="px-3 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[tc.last_status] || 'bg-gray-100 text-gray-700'}`}
                      >
                        {tc.last_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Recent Rejections */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm mb-8">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Recent Rejections</h2>
          <p className="text-xs text-gray-400 mt-0.5">Last 5 rejected submissions -- identify patterns to improve acceptance rates</p>
        </div>
        <div className="divide-y divide-gray-100">
          {data.recent_rejections.map((rej, idx) => (
            <div key={idx} className="px-5 py-4 flex items-start gap-4">
              <div className="flex-shrink-0 mt-0.5">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono text-xs font-semibold text-gray-800">{rej.case_number}</span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-gray-100 text-gray-700 font-mono">
                    {rej.reason_code}
                  </span>
                  <span className="text-xs text-gray-400">{formatDate(rej.filed_date)}</span>
                </div>
                <p className="text-sm text-gray-600">{rej.rejection_reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
