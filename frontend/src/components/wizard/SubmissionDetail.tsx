import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { submissionsApi, type Submission } from '../../services/api';
import { format } from 'date-fns';

const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Draft' },
  validating: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Validating' },
  ready: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Ready' },
  submitted: { bg: 'bg-indigo-100', text: 'text-indigo-800', label: 'Submitted' },
  accepted: { bg: 'bg-green-100', text: 'text-green-800', label: 'Accepted' },
  rejected: { bg: 'bg-red-100', text: 'text-red-800', label: 'Rejected' },
};

export default function SubmissionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: submission, isLoading } = useQuery<Submission>({
    queryKey: ['submission', id],
    queryFn: () => submissionsApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <svg className="animate-spin w-6 h-6 text-accent-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      </div>
    );
  }

  if (!submission) return null;

  const status = statusConfig[submission.status] || statusConfig.draft;
  const fd = submission.form_data as Record<string, string>;

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <button onClick={() => navigate('/cases')} className="hover:text-accent-500 transition-colors">Cases</button>
        <span>/</span>
        <button onClick={() => navigate(`/cases/${submission.case_id}`)} className="hover:text-accent-500 transition-colors font-mono">
          {submission.wcb_case_number}
        </button>
        <span>/</span>
        <span className="text-gray-600">Submission</span>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-navy-700">Submission Detail</h1>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${status.bg} ${status.text}`}>
                {status.label}
              </span>
            </div>
            <p className="text-sm text-gray-500">
              {submission.claimant_name} -- {submission.wcb_case_number}
            </p>
          </div>
          {submission.wcb_submission_id && (
            <div className="text-right">
              <div className="text-xs text-gray-400 uppercase tracking-wide">WCB Submission ID</div>
              <div className="font-mono font-bold text-navy-700">{submission.wcb_submission_id}</div>
            </div>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Reason codes */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Reason Codes</h2>
            <div className="flex gap-2 flex-wrap">
              {submission.reason_codes.map((code, i) => (
                <div key={code} className="px-3 py-1.5 bg-navy-50 rounded-lg">
                  <span className="font-mono text-sm font-bold text-navy-700">{code}</span>
                  {submission.reason_code_labels[i] && (
                    <span className="text-xs text-gray-500 ml-2">{submission.reason_code_labels[i]}</span>
                  )}
                </div>
              ))}
              {submission.reason_codes.length === 0 && (
                <span className="text-sm text-gray-400">No reason codes assigned</span>
              )}
            </div>
          </div>

          {/* Form data */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Form Data</h2>
            <div className="grid grid-cols-2 gap-4">
              <InfoField label="Certification Date" value={fd.certification_date || '--'} />
              <InfoField label="Disability Classification" value={(fd.disability_classification || '--').replace(/_/g, ' ')} />
              <InfoField label="Degree of Disability" value={fd.degree_of_disability ? `${fd.degree_of_disability}%` : '--'} />
              <InfoField label="Body Parts" value={fd.body_parts || '--'} />
            </div>
          </div>

          {/* Narrative */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Narrative</h2>
            <p className="text-sm text-gray-700 leading-relaxed">
              {submission.narrative || '(No narrative provided)'}
            </p>
          </div>

          {/* Validation results */}
          {(submission.validation_errors.length > 0 || submission.validation_warnings.length > 0) && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Validation Results</h2>
              {submission.validation_errors.map((err, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded-lg mb-2">
                  <svg className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm text-red-700">{err.message}</span>
                </div>
              ))}
              {submission.validation_warnings.map((warn, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg mb-2">
                  <svg className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <span className="text-sm text-amber-700">{warn.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Timeline */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Timeline</h2>
            <div className="space-y-3">
              <TimelineItem
                label="Created"
                date={submission.created_at}
                active
              />
              {submission.attested_at && (
                <TimelineItem
                  label="Attested"
                  date={submission.attested_at}
                  active
                />
              )}
              {submission.submitted_at && (
                <TimelineItem
                  label="Submitted"
                  date={submission.submitted_at}
                  active
                />
              )}
              {submission.status === 'accepted' && (
                <TimelineItem
                  label="Accepted"
                  date={submission.updated_at}
                  active
                  success
                />
              )}
              {submission.status === 'rejected' && (
                <TimelineItem
                  label="Rejected"
                  date={submission.updated_at}
                  active
                  error
                />
              )}
            </div>
          </div>

          {/* Documents */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">
              Documents ({submission.documents.length})
            </h2>
            {submission.documents.length > 0 ? (
              <div className="space-y-2">
                {submission.documents.map((doc) => (
                  <div key={doc.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                    <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <div className="text-xs text-gray-700 truncate font-medium">{doc.filename}</div>
                      <div className="text-[10px] text-gray-400">{doc.doc_type}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No documents attached</p>
            )}
          </div>

          {/* Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Actions</h2>
            <div className="space-y-2">
              {submission.wcb_submission_id && (
                <button
                  onClick={() => submissionsApi.downloadPdf(submission.id)}
                  className="w-full px-4 py-2 border border-accent-500 text-accent-500 hover:bg-accent-50 font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download PDF
                </button>
              )}
              <button
                onClick={() => navigate(`/cases/${submission.case_id}`)}
                className="w-full px-4 py-2 border border-gray-300 text-gray-600 hover:bg-gray-50 font-medium rounded-lg transition-colors text-sm"
              >
                View Case
              </button>
              <button
                onClick={() => navigate('/')}
                className="w-full px-4 py-2 text-gray-500 hover:text-gray-700 font-medium rounded-lg transition-colors text-sm"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{label}</div>
      <div className="text-sm font-medium text-gray-800 capitalize">{value}</div>
    </div>
  );
}

function TimelineItem({ label, date, active, success, error }: { label: string; date: string; active?: boolean; success?: boolean; error?: boolean }) {
  const dotColor = success ? 'bg-green-500' : error ? 'bg-red-500' : active ? 'bg-accent-500' : 'bg-gray-300';
  return (
    <div className="flex items-start gap-3">
      <div className={`w-2.5 h-2.5 rounded-full ${dotColor} mt-1.5 flex-shrink-0`} />
      <div>
        <div className="text-sm font-medium text-gray-700">{label}</div>
        <div className="text-xs text-gray-400">{date?.slice(0,19) || '—'}</div>
      </div>
    </div>
  );
}
