import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { providerApi, type AuthRequest } from '../../services/api';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  submitted: 'bg-indigo-100 text-indigo-800',
  in_review: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  denied: 'bg-red-100 text-red-800',
  appealed: 'bg-orange-100 text-orange-800',
};

const allStatuses = ['all', 'draft', 'submitted', 'in_review', 'approved', 'denied', 'appealed'];
const allPayers = ['All Payers', 'UHC', 'Aetna', 'BCBS', 'Cigna', 'Humana', 'EmblemHealth', 'Medicare', 'Medicaid'];

export default function PriorAuthList() {
  const navigate = useNavigate();
  const [auths, setAuths] = useState<AuthRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [payerFilter, setPayerFilter] = useState('All Payers');

  const fetchAuths = () => {
    setLoading(true);
    const filters: { status?: string; payer?: string; search?: string } = {};
    if (statusFilter !== 'all') filters.status = statusFilter;
    if (payerFilter !== 'All Payers') filters.payer = payerFilter;
    if (search.trim()) filters.search = search.trim();

    providerApi.listAuthRequests(filters).then((data) => {
      setAuths(data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchAuths();
  }, [statusFilter, payerFilter]);

  useEffect(() => {
    const timeout = setTimeout(fetchAuths, 300);
    return () => clearTimeout(timeout);
  }, [search]);

  const statusCounts = (auths || []).reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-navy-700">Prior Authorizations</h1>
          <p className="text-sm text-gray-500 mt-1">Manage and track all authorization requests</p>
        </div>
        <button
          onClick={() => navigate('/prior-auth/new')}
          className="px-4 py-2.5 bg-accent-500 text-white text-sm font-medium rounded-lg hover:bg-accent-600 transition-colors"
        >
          + New Prior Auth
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* Search */}
          <div className="flex-1 min-w-[240px]">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by patient name, procedure, or CPT code..."
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-accent-500"
              />
            </div>
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
          >
            {allStatuses.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All Statuses' : s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>

          {/* Payer filter */}
          <select
            value={payerFilter}
            onChange={(e) => setPayerFilter(e.target.value)}
            className="px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
          >
            {allPayers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {/* Status chips */}
        <div className="flex flex-wrap gap-2 mt-3">
          {allStatuses.filter((s) => s !== 'all').map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(statusFilter === s ? 'all' : s)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-navy-700 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              {statusCounts[s] ? ` (${statusCounts[s]})` : ''}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-navy-700 mx-auto" />
            <p className="text-sm text-gray-500 mt-3">Loading authorizations...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wider bg-gray-50">
                  <th className="px-5 py-3 font-medium">Patient</th>
                  <th className="px-5 py-3 font-medium">Procedure</th>
                  <th className="px-5 py-3 font-medium">Payer</th>
                  <th className="px-5 py-3 font-medium">Insurance</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Submitted</th>
                  <th className="px-5 py-3 font-medium">Decision</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(auths || []).map((auth) => (
                  <tr
                    key={auth.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/prior-auth/${auth.id}`)}
                  >
                    <td className="px-5 py-4">
                      <div className="font-medium text-gray-800">{auth.patient_name}</div>
                      <div className="text-xs text-gray-400 mt-0.5">DOB: {auth.patient_dob} | {auth.patient_mrn}</div>
                    </td>
                    <td className="px-5 py-4">
                      <div className="text-gray-800">{auth.procedure_name}</div>
                      <div className="text-xs text-gray-400 font-mono mt-0.5">CPT {auth.cpt_code}</div>
                    </td>
                    <td className="px-5 py-4 text-gray-700 font-medium">{auth.payer}</td>
                    <td className="px-5 py-4">
                      <span className="text-xs text-gray-500 capitalize">{(auth.insurance_type || '').replace('_', ' ')}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[auth.status] || 'bg-gray-100 text-gray-700'}`}>
                        {auth.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-gray-500 text-xs">
                      {auth.submitted_at ? auth.submitted_at.slice(0, 10) : '--'}
                    </td>
                    <td className="px-5 py-4 text-gray-500 text-xs">
                      {auth.decision_date ? auth.decision_date.slice(0, 10) : '--'}
                    </td>
                  </tr>
                ))}
                {(auths || []).length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-gray-400">
                      <div className="text-4xl mb-2">&#128203;</div>
                      <p className="font-medium text-gray-600">No authorization requests found</p>
                      <p className="text-sm mt-1">Try adjusting your filters or create a new request.</p>
                      <button
                        onClick={() => navigate('/prior-auth/new')}
                        className="mt-4 px-4 py-2 bg-accent-500 text-white text-sm font-medium rounded-lg hover:bg-accent-600 transition-colors"
                      >
                        + New Prior Auth
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
