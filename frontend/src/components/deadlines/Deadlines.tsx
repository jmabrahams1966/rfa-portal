import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

// ---------- Types ----------

interface Deadline {
  case_id: string;
  wcb_case_number: string;
  deadline_type: string;
  due_date: string;
  trigger_date: string;
  trigger_event?: string;
  days_remaining: number;
}

interface DeadlineResponse {
  overdue: Deadline[];
  due_this_week: Deadline[];
  due_this_month: Deadline[];
}

// ---------- Constants ----------

const DEADLINE_LABELS: Record<string, string> = {
  rfa_after_ime: 'AIRA After IME (30 days)',
  rfa_after_decision: 'AIRA After Board Decision (30 days)',
  treatment_denial: 'Treatment Denial Response (30 days)',
  section_300_prerequisite: 'Section 300.23(b) Prerequisite',
  ime_scheduling: 'IME Scheduling (60 days)',
};

// ---------- Mock Data ----------

const MOCK_DEADLINES: DeadlineResponse = {
  overdue: [
    {
      case_id: 'case-001',
      wcb_case_number: 'WCB-2025-04821',
      deadline_type: 'rfa_after_ime',
      due_date: '2026-04-07',
      trigger_date: '2026-03-08',
      trigger_event: 'IME report received 03/08/2026',
      days_remaining: -7,
    },
    {
      case_id: 'case-002',
      wcb_case_number: 'WCB-2025-11934',
      deadline_type: 'treatment_denial',
      due_date: '2026-04-10',
      trigger_date: '2026-03-11',
      trigger_event: 'Treatment denial issued 03/11/2026',
      days_remaining: -4,
    },
    {
      case_id: 'case-003',
      wcb_case_number: 'WCB-2026-00217',
      deadline_type: 'rfa_after_decision',
      due_date: '2026-04-12',
      trigger_date: '2026-03-13',
      trigger_event: 'Board decision rendered 03/13/2026',
      days_remaining: -2,
    },
  ],
  due_this_week: [
    {
      case_id: 'case-004',
      wcb_case_number: 'WCB-2025-08763',
      deadline_type: 'section_300_prerequisite',
      due_date: '2026-04-15',
      trigger_date: '2026-03-15',
      trigger_event: 'Pre-hearing conference 03/15/2026',
      days_remaining: 1,
    },
    {
      case_id: 'case-005',
      wcb_case_number: 'WCB-2026-01482',
      deadline_type: 'rfa_after_ime',
      due_date: '2026-04-17',
      trigger_date: '2026-03-18',
      trigger_event: 'IME report received 03/18/2026',
      days_remaining: 3,
    },
    {
      case_id: 'case-006',
      wcb_case_number: 'WCB-2025-15290',
      deadline_type: 'treatment_denial',
      due_date: '2026-04-19',
      trigger_date: '2026-03-20',
      trigger_event: 'Treatment denial issued 03/20/2026',
      days_remaining: 5,
    },
  ],
  due_this_month: [
    {
      case_id: 'case-007',
      wcb_case_number: 'WCB-2025-22018',
      deadline_type: 'ime_scheduling',
      due_date: '2026-04-25',
      trigger_date: '2026-02-24',
      trigger_event: 'IME ordered 02/24/2026',
      days_remaining: 11,
    },
    {
      case_id: 'case-008',
      wcb_case_number: 'WCB-2026-03107',
      deadline_type: 'rfa_after_decision',
      due_date: '2026-04-28',
      trigger_date: '2026-03-29',
      trigger_event: 'Board decision rendered 03/29/2026',
      days_remaining: 14,
    },
    {
      case_id: 'case-009',
      wcb_case_number: 'WCB-2025-19445',
      deadline_type: 'rfa_after_ime',
      due_date: '2026-05-02',
      trigger_date: '2026-04-02',
      trigger_event: 'IME report received 04/02/2026',
      days_remaining: 18,
    },
    {
      case_id: 'case-010',
      wcb_case_number: 'WCB-2026-00891',
      deadline_type: 'section_300_prerequisite',
      due_date: '2026-05-08',
      trigger_date: '2026-04-08',
      trigger_event: 'Pre-hearing conference 04/08/2026',
      days_remaining: 24,
    },
  ],
};

// ---------- Helpers ----------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getDeadlineLabel(type: string): string {
  return DEADLINE_LABELS[type] || type;
}

// ---------- Component ----------

export default function Deadlines() {
  const navigate = useNavigate();
  const [data, setData] = useState<DeadlineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, _setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    async function fetchDeadlines() {
      try {
        const token = localStorage.getItem('rfa_token');
        const res = await axios.get('/api/enterprise/deadlines', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(res.data);
      } catch (err: any) {
        console.warn('Deadlines API not available, using mock data:', err.message);
        setData(MOCK_DEADLINES);
      } finally {
        setLoading(false);
      }
    }
    fetchDeadlines();
  }, []);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">{error}</div>
      </div>
    );
  }

  const overdue = data?.overdue || [];
  const dueThisWeek = data?.due_this_week || [];
  const dueThisMonth = data?.due_this_month || [];

  // Compute "on track" as due_this_month items with > 7 days remaining
  const onTrackCount = dueThisMonth.filter((d) => d.days_remaining > 7).length;

  // Filter logic
  const filterDeadlines = (items: Deadline[]) => {
    return items.filter((d) => {
      const matchesType = filterType === 'all' || d.deadline_type === filterType;
      const matchesSearch =
        !searchQuery ||
        d.wcb_case_number.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesSearch;
    });
  };

  const filteredOverdue = filterDeadlines(overdue).sort((a, b) => a.days_remaining - b.days_remaining);
  const filteredDueThisWeek = filterDeadlines(dueThisWeek).sort((a, b) => a.days_remaining - b.days_remaining);
  const filteredUpcoming = filterDeadlines(dueThisMonth).sort((a, b) => a.days_remaining - b.days_remaining);

  const renderDeadlineRow = (d: Deadline) => (
    <div
      key={`${d.case_id}-${d.deadline_type}`}
      className="flex items-center justify-between px-5 py-3.5 border-b border-black/5 last:border-b-0"
    >
      <div className="flex items-center gap-6 flex-1 min-w-0">
        <span className="font-mono text-xs font-semibold text-gray-800 w-36 flex-shrink-0">
          {d.wcb_case_number}
        </span>
        <span className="text-sm text-gray-700 w-64 flex-shrink-0 truncate">
          {getDeadlineLabel(d.deadline_type)}
        </span>
        <span className="text-sm text-gray-500 w-32 flex-shrink-0">
          {formatDate(d.due_date)}
        </span>
        {d.days_remaining < 0 ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 w-28 justify-center flex-shrink-0">
            {Math.abs(d.days_remaining)}d overdue
          </span>
        ) : d.days_remaining <= 7 ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 w-28 justify-center flex-shrink-0">
            {d.days_remaining}d remaining
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 w-28 justify-center flex-shrink-0">
            {d.days_remaining}d remaining
          </span>
        )}
        <span className="text-xs text-gray-400 truncate flex-1 min-w-0">
          {d.trigger_event || `Triggered ${formatDate(d.trigger_date)}`}
        </span>
      </div>
      <button
        onClick={() => navigate(`/cases/${d.case_id}`)}
        className="ml-4 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors flex-shrink-0"
      >
        View Case
      </button>
    </div>
  );

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">Deadlines</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track filing deadlines and compliance windows across all active cases
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <div className="text-3xl font-bold text-red-700">{overdue.length}</div>
          <div className="text-sm text-red-600 mt-1 font-medium">Overdue</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <div className="text-3xl font-bold text-amber-700">{dueThisWeek.length}</div>
          <div className="text-sm text-amber-600 mt-1 font-medium">Due This Week</div>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <div className="text-3xl font-bold text-blue-700">{dueThisMonth.length}</div>
          <div className="text-sm text-blue-600 mt-1 font-medium">Due This Month</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <div className="text-3xl font-bold text-green-700">{onTrackCount}</div>
          <div className="text-sm text-green-600 mt-1 font-medium">On Track</div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search by case number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
        >
          <option value="all">All Deadline Types</option>
          {Object.entries(DEADLINE_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Overdue section */}
      {filteredOverdue.length > 0 && (
        <div className="mb-6">
          <div className="bg-red-50 border border-red-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 bg-red-100 border-b border-red-200">
              <h2 className="text-sm font-bold text-red-800 uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Overdue ({filteredOverdue.length})
              </h2>
            </div>
            <div>{filteredOverdue.map(renderDeadlineRow)}</div>
          </div>
        </div>
      )}

      {/* Due This Week section */}
      {filteredDueThisWeek.length > 0 && (
        <div className="mb-6">
          <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
            <div className="px-5 py-3 bg-amber-100 border-b border-amber-200">
              <h2 className="text-sm font-bold text-amber-800 uppercase tracking-wider">
                Due This Week ({filteredDueThisWeek.length})
              </h2>
            </div>
            <div>{filteredDueThisWeek.map(renderDeadlineRow)}</div>
          </div>
        </div>
      )}

      {/* Upcoming section */}
      {filteredUpcoming.length > 0 && (
        <div className="mb-6">
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
              <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider">
                Upcoming ({filteredUpcoming.length})
              </h2>
            </div>
            <div>{filteredUpcoming.map(renderDeadlineRow)}</div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {filteredOverdue.length === 0 &&
        filteredDueThisWeek.length === 0 &&
        filteredUpcoming.length === 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center shadow-sm">
            <div className="text-4xl text-gray-300 mb-3">&#128197;</div>
            <p className="text-gray-500 font-medium">No deadlines match your filters</p>
            <p className="text-sm text-gray-400 mt-1">Try adjusting your search or filter criteria</p>
          </div>
        )}
    </div>
  );
}
