import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';
const isDevBypass = !import.meta.env.VITE_API_URL;

const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('rfa_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('rfa_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

// ---------- Types ----------

export interface User {
  id: string;
  email: string;
  name: string;
  organization: string;
  role: string;
}

export interface WCCase {
  id: string;
  wcb_case_number: string;
  claimant_name: string;
  claimant_dob: string;
  date_of_injury: string;
  employer_name: string;
  carrier_name: string;
  carrier_code: string;
  submissions_count: number;
  last_filed: string | null;
  created_at: string;
  updated_at: string;
}

export interface Submission {
  id: string;
  case_id: string;
  wcb_case_number: string;
  claimant_name: string;
  status: 'draft' | 'validating' | 'ready' | 'submitted' | 'accepted' | 'rejected';
  reason_codes: string[];
  reason_code_labels: string[];
  narrative: string;
  form_data: Record<string, unknown>;
  documents: SubmissionDocument[];
  validation_errors: ValidationItem[];
  validation_warnings: ValidationItem[];
  wcb_submission_id: string | null;
  submitted_at: string | null;
  attested: boolean;
  attested_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubmissionDocument {
  id: string;
  filename: string;
  doc_type: string;
  uploaded_at: string;
  size: number;
}

export interface ValidationItem {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ExtractionResult {
  reason_codes: { code: string; label: string; confidence: 'HIGH' | 'MEDIUM' | 'LOW' }[];
  extracted_fields: Record<string, { value: string; confidence: 'HIGH' | 'MEDIUM' | 'LOW' }>;
}

export interface DashboardStats {
  total_cases: number;
  draft_submissions: number;
  submitted: number;
  accepted: number;
  rejected: number;
}

export interface ReasonCodeBreakdown {
  code: string;
  label: string;
  count: number;
}

export interface RecentSubmission {
  id: string;
  wcb_case_number: string;
  claimant_name: string;
  status: string;
  reason_codes: string[];
  submitted_at: string | null;
  created_at: string;
}

// ---------- Auth API ----------

export const authApi = {
  login: async (email: string, password: string) => {
    if (isDevBypass) {
      const devUser: User = {
        id: 'dev-user-1',
        email: 'dev@rfaportal.com',
        name: 'Dev User',
        organization: 'RFA Dev Org',
        role: 'admin',
      };
      localStorage.setItem('rfa_token', 'dev-token');
      localStorage.setItem('rfa_user', JSON.stringify(devUser));
      return devUser;
    }
    const { data } = await api.post('/auth/login', { email, password });
    localStorage.setItem('rfa_token', data.token);
    localStorage.setItem('rfa_user', JSON.stringify(data.user));
    return data.user as User;
  },

  logout: () => {
    localStorage.removeItem('rfa_token');
    localStorage.removeItem('rfa_user');
  },

  getUser: (): User | null => {
    const raw = localStorage.getItem('rfa_user');
    return raw ? JSON.parse(raw) : null;
  },

  isAuthenticated: (): boolean => {
    if (isDevBypass) return true;
    return !!localStorage.getItem('rfa_token');
  },
};

// ---------- Cases API ----------

export const casesApi = {
  list: async (search?: string) => {
    if (isDevBypass) return devCases.filter((c) => !search || c.wcb_case_number.includes(search) || c.claimant_name.toLowerCase().includes(search.toLowerCase()));
    const { data } = await api.get('/cases', { params: { search } });
    return data as WCCase[];
  },

  get: async (id: string) => {
    if (isDevBypass) return devCases.find((c) => c.id === id) || devCases[0];
    const { data } = await api.get(`/cases/${id}`);
    return data as WCCase;
  },

  create: async (payload: Partial<WCCase>) => {
    if (isDevBypass) {
      const newCase: WCCase = {
        id: `case-${Date.now()}`,
        wcb_case_number: payload.wcb_case_number || '',
        claimant_name: payload.claimant_name || '',
        claimant_dob: payload.claimant_dob || '',
        date_of_injury: payload.date_of_injury || '',
        employer_name: payload.employer_name || '',
        carrier_name: payload.carrier_name || '',
        carrier_code: payload.carrier_code || '',
        submissions_count: 0,
        last_filed: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      devCases.push(newCase);
      return newCase;
    }
    const { data } = await api.post('/cases', payload);
    return data as WCCase;
  },

  update: async (id: string, payload: Partial<WCCase>) => {
    if (isDevBypass) {
      const idx = devCases.findIndex((c) => c.id === id);
      if (idx >= 0) devCases[idx] = { ...devCases[idx], ...payload, updated_at: new Date().toISOString() };
      return devCases[idx];
    }
    const { data } = await api.put(`/cases/${id}`, payload);
    return data as WCCase;
  },
};

// ---------- Submissions API ----------

export const submissionsApi = {
  list: async (caseId?: string) => {
    if (isDevBypass) return devSubmissions.filter((s) => !caseId || s.case_id === caseId);
    const { data } = await api.get('/submissions', { params: { case_id: caseId } });
    return data as Submission[];
  },

  get: async (id: string) => {
    if (isDevBypass) return devSubmissions.find((s) => s.id === id) || devSubmissions[0];
    const { data } = await api.get(`/submissions/${id}`);
    return data as Submission;
  },

  create: async (caseId: string) => {
    if (isDevBypass) {
      const wc = devCases.find((c) => c.id === caseId) || devCases[0];
      const sub: Submission = {
        id: `sub-${Date.now()}`,
        case_id: caseId,
        wcb_case_number: wc.wcb_case_number,
        claimant_name: wc.claimant_name,
        status: 'draft',
        reason_codes: [],
        reason_code_labels: [],
        narrative: '',
        form_data: {},
        documents: [],
        validation_errors: [],
        validation_warnings: [],
        wcb_submission_id: null,
        submitted_at: null,
        attested: false,
        attested_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      devSubmissions.push(sub);
      return sub;
    }
    const { data } = await api.post('/submissions', { case_id: caseId });
    return data as Submission;
  },

  update: async (id: string, payload: Partial<Submission>) => {
    if (isDevBypass) {
      const idx = devSubmissions.findIndex((s) => s.id === id);
      if (idx >= 0) devSubmissions[idx] = { ...devSubmissions[idx], ...payload, updated_at: new Date().toISOString() };
      return devSubmissions[idx];
    }
    const { data } = await api.put(`/submissions/${id}`, payload);
    return data as Submission;
  },

  uploadDoc: async (id: string, file: File, docType: string) => {
    if (isDevBypass) {
      const doc: SubmissionDocument = {
        id: `doc-${Date.now()}`,
        filename: file.name,
        doc_type: docType,
        uploaded_at: new Date().toISOString(),
        size: file.size,
      };
      const sub = devSubmissions.find((s) => s.id === id);
      if (sub) sub.documents.push(doc);
      return doc;
    }
    const form = new FormData();
    form.append('file', file);
    form.append('doc_type', docType);
    const { data } = await api.post(`/submissions/${id}/documents`, form);
    return data as SubmissionDocument;
  },

  extract: async (id: string) => {
    if (isDevBypass) {
      await new Promise((r) => setTimeout(r, 2000));
      const result: ExtractionResult = {
        reason_codes: [
          { code: 'MCI', label: 'Medical Causation / Impairment', confidence: 'HIGH' },
          { code: 'PPD', label: 'Permanent Partial Disability', confidence: 'MEDIUM' },
          { code: 'TTD', label: 'Temporary Total Disability', confidence: 'LOW' },
        ],
        extracted_fields: {
          certification_date: { value: '2026-03-15', confidence: 'HIGH' },
          disability_classification: { value: 'schedule_loss', confidence: 'HIGH' },
          degree_of_disability: { value: '35', confidence: 'MEDIUM' },
          body_parts: { value: 'Left knee, Right shoulder', confidence: 'HIGH' },
          narrative: { value: 'Claimant sustained injuries to left knee and right shoulder during workplace incident on 2025-06-15. MRI confirms ACL tear and rotator cuff impingement. IME confirms causation with reasonable medical certainty.', confidence: 'MEDIUM' },
        },
      };
      const sub = devSubmissions.find((s) => s.id === id);
      if (sub) {
        sub.reason_codes = result.reason_codes.map((r) => r.code);
        sub.reason_code_labels = result.reason_codes.map((r) => r.label);
      }
      return result;
    }
    const { data } = await api.post(`/submissions/${id}/extract`);
    return data as ExtractionResult;
  },

  validate: async (id: string) => {
    if (isDevBypass) {
      await new Promise((r) => setTimeout(r, 800));
      const sub = devSubmissions.find((s) => s.id === id);
      const errors: ValidationItem[] = [];
      const warnings: ValidationItem[] = [];
      if (sub && !sub.narrative) errors.push({ field: 'narrative', message: 'Narrative is required and must be at least 50 characters.', severity: 'error' });
      if (sub && sub.documents.length === 0) warnings.push({ field: 'documents', message: 'No supporting documents uploaded. Consider attaching relevant medical records.', severity: 'warning' });
      if (sub) {
        sub.validation_errors = errors;
        sub.validation_warnings = warnings;
        sub.status = errors.length === 0 ? 'ready' : 'draft';
      }
      return { errors, warnings };
    }
    const { data } = await api.post(`/submissions/${id}/validate`);
    return data as { errors: ValidationItem[]; warnings: ValidationItem[] };
  },

  buildXml: async (id: string) => {
    if (isDevBypass) {
      const sub = devSubmissions.find((s) => s.id === id);
      return `<?xml version="1.0" encoding="UTF-8"?>
<RFA2Submission>
  <Header>
    <WCBCaseNumber>${sub?.wcb_case_number || 'WCB-2025-001234'}</WCBCaseNumber>
    <ClaimantName>${sub?.claimant_name || 'John Doe'}</ClaimantName>
    <SubmissionDate>${new Date().toISOString().split('T')[0]}</SubmissionDate>
  </Header>
  <ReasonCodes>
    ${(sub?.reason_codes || []).map((c) => `<Code>${c}</Code>`).join('\n    ')}
  </ReasonCodes>
  <Narrative>${sub?.narrative || ''}</Narrative>
  <FormData>
    ${Object.entries(sub?.form_data || {}).map(([k, v]) => `<Field name="${k}">${v}</Field>`).join('\n    ')}
  </FormData>
</RFA2Submission>`;
    }
    const { data } = await api.get(`/submissions/${id}/xml`);
    return data as string;
  },

  submit: async (id: string) => {
    if (isDevBypass) {
      await new Promise((r) => setTimeout(r, 1500));
      const sub = devSubmissions.find((s) => s.id === id);
      if (sub) {
        sub.status = 'submitted';
        sub.submitted_at = new Date().toISOString();
        sub.wcb_submission_id = `WCB-SUB-${Date.now().toString(36).toUpperCase()}`;
      }
      return sub;
    }
    const { data } = await api.post(`/submissions/${id}/submit`);
    return data as Submission;
  },

  attest: async (id: string) => {
    if (isDevBypass) {
      const sub = devSubmissions.find((s) => s.id === id);
      if (sub) {
        sub.attested = true;
        sub.attested_at = new Date().toISOString();
      }
      return sub;
    }
    const { data } = await api.post(`/submissions/${id}/attest`);
    return data as Submission;
  },

  downloadPdf: async (id: string) => {
    if (isDevBypass) {
      alert('PDF download is not available in dev mode.');
      return;
    }
    const { data } = await api.get(`/submissions/${id}/pdf`, { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rfa2-submission-${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

// ---------- Dashboard API ----------

export const dashboardApi = {
  stats: async () => {
    if (isDevBypass) {
      return {
        total_cases: devCases.length,
        draft_submissions: devSubmissions.filter((s) => s.status === 'draft').length,
        submitted: devSubmissions.filter((s) => s.status === 'submitted').length,
        accepted: devSubmissions.filter((s) => s.status === 'accepted').length,
        rejected: devSubmissions.filter((s) => s.status === 'rejected').length,
      } as DashboardStats;
    }
    const { data } = await api.get('/dashboard/stats');
    return data as DashboardStats;
  },

  reasonCodeBreakdown: async () => {
    if (isDevBypass) {
      return [
        { code: 'MCI', label: 'Medical Causation / Impairment', count: 12 },
        { code: 'PPD', label: 'Permanent Partial Disability', count: 8 },
        { code: 'TTD', label: 'Temporary Total Disability', count: 5 },
        { code: 'SLU', label: 'Schedule Loss of Use', count: 4 },
        { code: 'CLM', label: 'Claim Establishment', count: 3 },
      ] as ReasonCodeBreakdown[];
    }
    const { data } = await api.get('/dashboard/reason-codes');
    return data as ReasonCodeBreakdown[];
  },

  recentSubmissions: async () => {
    if (isDevBypass) {
      return devSubmissions.slice(0, 10).map((s) => ({
        id: s.id,
        wcb_case_number: s.wcb_case_number,
        claimant_name: s.claimant_name,
        status: s.status,
        reason_codes: s.reason_codes,
        submitted_at: s.submitted_at,
        created_at: s.created_at,
      })) as RecentSubmission[];
    }
    const { data } = await api.get('/dashboard/recent');
    return data as RecentSubmission[];
  },
};

// ---------- Onboarding API ----------

export const onboardingApi = {
  signup: async (payload: { email: string; password: string; name: string; organization: string }) => {
    if (isDevBypass) {
      return { success: true, message: 'Account created (dev mode).' };
    }
    const { data } = await api.post('/onboarding/signup', payload);
    return data;
  },
};

// ---------- Dev Data ----------

const devCases: WCCase[] = [
  {
    id: 'case-1',
    wcb_case_number: 'WCB-2025-001234',
    claimant_name: 'John M. Rodriguez',
    claimant_dob: '1978-04-12',
    date_of_injury: '2025-06-15',
    employer_name: 'Metro Construction LLC',
    carrier_name: 'Empire State Insurance',
    carrier_code: 'ESI-4420',
    submissions_count: 2,
    last_filed: '2026-03-20T14:30:00Z',
    created_at: '2025-07-01T09:00:00Z',
    updated_at: '2026-03-20T14:30:00Z',
  },
  {
    id: 'case-2',
    wcb_case_number: 'WCB-2025-005678',
    claimant_name: 'Sarah K. Williams',
    claimant_dob: '1985-11-03',
    date_of_injury: '2025-09-22',
    employer_name: 'Hudson Valley Medical Center',
    carrier_name: 'Guardian Casualty Co.',
    carrier_code: 'GCC-7801',
    submissions_count: 1,
    last_filed: '2026-02-15T10:00:00Z',
    created_at: '2025-10-01T08:00:00Z',
    updated_at: '2026-02-15T10:00:00Z',
  },
  {
    id: 'case-3',
    wcb_case_number: 'WCB-2026-000112',
    claimant_name: 'Michael T. Chen',
    claimant_dob: '1990-07-28',
    date_of_injury: '2026-01-10',
    employer_name: 'Albany Logistics Inc.',
    carrier_name: 'National Workers Mutual',
    carrier_code: 'NWM-3355',
    submissions_count: 0,
    last_filed: null,
    created_at: '2026-01-20T11:00:00Z',
    updated_at: '2026-01-20T11:00:00Z',
  },
];

const devSubmissions: Submission[] = [
  {
    id: 'sub-1',
    case_id: 'case-1',
    wcb_case_number: 'WCB-2025-001234',
    claimant_name: 'John M. Rodriguez',
    status: 'accepted',
    reason_codes: ['MCI', 'PPD'],
    reason_code_labels: ['Medical Causation / Impairment', 'Permanent Partial Disability'],
    narrative: 'Claimant sustained injuries to left knee during workplace fall on 6/15/2025. IME confirms causation with reasonable medical certainty. Permanent partial disability assessment completed.',
    form_data: { certification_date: '2026-02-01', disability_classification: 'schedule_loss', degree_of_disability: '25', body_parts: 'Left knee' },
    documents: [
      { id: 'doc-1', filename: 'IME_Report_Rodriguez.pdf', doc_type: 'IME Report', uploaded_at: '2026-03-15T09:00:00Z', size: 245000 },
      { id: 'doc-2', filename: 'MRI_Left_Knee.pdf', doc_type: 'Medical Record', uploaded_at: '2026-03-15T09:05:00Z', size: 1200000 },
    ],
    validation_errors: [],
    validation_warnings: [],
    wcb_submission_id: 'WCB-SUB-M4K9X2',
    submitted_at: '2026-03-20T14:30:00Z',
    attested: true,
    attested_at: '2026-03-20T14:29:00Z',
    created_at: '2026-03-15T08:00:00Z',
    updated_at: '2026-03-20T14:30:00Z',
  },
  {
    id: 'sub-2',
    case_id: 'case-1',
    wcb_case_number: 'WCB-2025-001234',
    claimant_name: 'John M. Rodriguez',
    status: 'draft',
    reason_codes: ['TTD'],
    reason_code_labels: ['Temporary Total Disability'],
    narrative: '',
    form_data: {},
    documents: [],
    validation_errors: [],
    validation_warnings: [],
    wcb_submission_id: null,
    submitted_at: null,
    attested: false,
    attested_at: null,
    created_at: '2026-04-10T12:00:00Z',
    updated_at: '2026-04-10T12:00:00Z',
  },
  {
    id: 'sub-3',
    case_id: 'case-2',
    wcb_case_number: 'WCB-2025-005678',
    claimant_name: 'Sarah K. Williams',
    status: 'submitted',
    reason_codes: ['MCI'],
    reason_code_labels: ['Medical Causation / Impairment'],
    narrative: 'Claimant reports repetitive stress injury to bilateral wrists from data entry duties. Orthopedic evaluation confirms bilateral carpal tunnel syndrome causally related to occupational activities.',
    form_data: { certification_date: '2026-02-10', disability_classification: 'non_schedule', degree_of_disability: '15', body_parts: 'Bilateral wrists' },
    documents: [
      { id: 'doc-3', filename: 'Ortho_Evaluation_Williams.pdf', doc_type: 'IME Report', uploaded_at: '2026-02-12T10:00:00Z', size: 189000 },
    ],
    validation_errors: [],
    validation_warnings: [],
    wcb_submission_id: 'WCB-SUB-P7R3Y8',
    submitted_at: '2026-02-15T10:00:00Z',
    attested: true,
    attested_at: '2026-02-15T09:58:00Z',
    created_at: '2026-02-10T08:00:00Z',
    updated_at: '2026-02-15T10:00:00Z',
  },
];

export default api;
