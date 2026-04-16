import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { casesApi, type WCCase } from '../../services/api';
import { format } from 'date-fns';

export default function CaseList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const { data: cases, isLoading } = useQuery<WCCase[]>({
    queryKey: ['cases', search],
    queryFn: () => casesApi.list(search || undefined),
  });

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-navy-700">Cases</h1>
          <p className="text-sm text-gray-500 mt-1">Manage workers' compensation cases and file RFA-2 submissions</p>
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by WCB case number or claimant name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent-500 focus:border-accent-500 outline-none text-sm"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider border-b border-gray-200">
                <th className="px-5 py-3 font-medium">Case #</th>
                <th className="px-5 py-3 font-medium">Claimant</th>
                <th className="px-5 py-3 font-medium">Date of Injury</th>
                <th className="px-5 py-3 font-medium">Employer</th>
                <th className="px-5 py-3 font-medium">Submissions</th>
                <th className="px-5 py-3 font-medium">Last Filed</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center">
                    <div className="flex items-center justify-center gap-2 text-gray-400">
                      <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                      </svg>
                      Loading cases...
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && (cases || []).map((wc) => (
                <tr
                  key={wc.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/cases/${wc.id}`)}
                >
                  <td className="px-5 py-3.5 font-mono text-xs font-semibold text-navy-700">
                    {wc.wcb_case_number}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="font-medium text-gray-800">{wc.claimant_name}</div>
                    <div className="text-xs text-gray-400">DOB: {format(new Date(wc.claimant_dob), 'MM/dd/yyyy')}</div>
                  </td>
                  <td className="px-5 py-3.5 text-gray-600">
                    {format(new Date(wc.date_of_injury), 'MM/dd/yyyy')}
                  </td>
                  <td className="px-5 py-3.5 text-gray-600">{wc.employer_name}</td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-navy-50 text-navy-700 text-xs font-semibold">
                      {wc.submissions_count}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-gray-500 text-xs">
                    {wc.last_filed ? format(new Date(wc.last_filed), 'MMM d, yyyy') : '--'}
                  </td>
                  <td className="px-5 py-3.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/submissions/new/${wc.id}`);
                      }}
                      className="px-3 py-1.5 bg-accent-500 hover:bg-accent-600 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      New Submission
                    </button>
                  </td>
                </tr>
              ))}
              {!isLoading && (!cases || cases.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-gray-400">
                    {search ? 'No cases match your search.' : 'No cases found.'}
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
