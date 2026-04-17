import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { casesApi, submissionsApi, type WCCase, type Submission } from '../../services/api';
import { format } from 'date-fns';

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  validating: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-blue-100 text-blue-800',
  submitted: 'bg-indigo-100 text-indigo-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
};

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: wcCase, isLoading: caseLoading } = useQuery<WCCase>({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!),
    enabled: !!id,
  });

  const { data: submissions } = useQuery<Submission[]>({
    queryKey: ['submissions', id],
    queryFn: () => submissionsApi.list(id),
    enabled: !!id,
  });

  if (caseLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <svg className="animate-spin w-6 h-6 text-accent-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      </div>
    );
  }

  if (!wcCase) return null;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <button onClick={() => navigate('/cases')} className="hover:text-accent-500 transition-colors">
          Cases
        </button>
        <span>/</span>
        <span className="text-gray-600 font-mono">{wcCase.wcb_case_number}</span>
      </div>

      {/* Case header */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-navy-700">{wcCase.claimant_name}</h1>
              <span className="px-2 py-0.5 bg-navy-50 text-navy-700 rounded text-xs font-mono font-semibold">
                {wcCase.wcb_case_number}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-3 mt-4 text-sm">
              <div>
                <div className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">Date of Injury</div>
                <div className="font-medium text-gray-700">{wcCase.date_of_injury ? format(new Date(wcCase.date_of_injury + 'T00:00:00'), 'MM/dd/yyyy') : '—'}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">Employer</div>
                <div className="font-medium text-gray-700">{wcCase.employer_name || '—'}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">Carrier</div>
                <div className="font-medium text-gray-700">{wcCase.carrier_name || '—'}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">District</div>
                <div className="font-medium text-gray-700">{wcCase.district || '—'}</div>
              </div>
            </div>
          </div>
          <button
            onClick={() => navigate(`/submissions/new/${wcCase.id}`)}
            className="px-5 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm flex items-center gap-2 whitespace-nowrap"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Submission
          </button>
        </div>
      </div>

      {/* Submission history */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-navy-700">Submission History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider border-b border-gray-200">
                <th className="px-5 py-3 font-medium">Submission ID</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Reason Codes</th>
                <th className="px-5 py-3 font-medium">WCB Submission ID</th>
                <th className="px-5 py-3 font-medium">Created</th>
                <th className="px-5 py-3 font-medium">Submitted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(submissions || []).map((sub) => (
                <tr
                  key={sub.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/submissions/${sub.id}`)}
                >
                  <td className="px-5 py-3.5 font-mono text-xs text-gray-600">{sub.id}</td>
                  <td className="px-5 py-3.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[sub.status] || 'bg-gray-100'}`}>
                      {sub.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex gap-1 flex-wrap">
                      {(sub.reason_codes || []).map((code) => (
                        <span key={code} className="px-1.5 py-0.5 bg-navy-50 text-navy-600 rounded text-xs font-mono">
                          {code}
                        </span>
                      ))}
                      {(sub.reason_codes || []).length === 0 && <span className="text-gray-400 text-xs">--</span>}
                    </div>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-gray-600">
                    {sub.wcb_submission_id || '--'}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500 text-xs">
                    {sub.created_at?.slice(0,10) || '—'}
                  </td>
                  <td className="px-5 py-3.5 text-gray-500 text-xs">
                    {sub.submitted_at ? sub.submitted_at?.slice(0,19) || '—' : '--'}
                  </td>
                </tr>
              ))}
              {(!submissions || submissions.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-gray-400">
                    No submissions filed for this case yet.
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
