import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || '/api';
const isDevBypass = false; // Set to true for mock data, false to use real backend

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
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      // Don't redirect in dev — just log
      console.warn('API returned 401:', err.config?.url);
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
    const { data } = await api.post('/auth/login/', { email, password });
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
    // Auto-set dev token if not present
    if (!localStorage.getItem('rfa_token')) {
      localStorage.setItem('rfa_token', 'dev-bypass');
      localStorage.setItem('rfa_user', JSON.stringify({id:'dev-001',email:'dev@rfa-portal.com',full_name:'Dev Admin',role:'admin'}));
    }
    return true; // Always authenticated in dev
    return !!localStorage.getItem('rfa_token');
  },
};

// ---------- Cases API ----------

export const casesApi = {
  list: async (search?: string) => {
    if (isDevBypass) return devCases.filter((c) => !search || c.wcb_case_number.includes(search) || c.claimant_name.toLowerCase().includes(search.toLowerCase()));
    const { data } = await api.get('/cases/', { params: { search } });
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
    const { data } = await api.post('/cases/', payload);
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
    const { data } = await api.get('/submissions/', { params: { case_id: caseId } });
    return data as Submission[];
  },

  get: async (id: string) => {
    if (isDevBypass) return devSubmissions.find((s) => s.id === id) || devSubmissions[0];
    const { data } = await api.get(`/submissions/${id}`);
    // Normalize API response to match frontend Submission interface
    return {
      ...data,
      wcb_case_number: data.wcb_case_number || '',
      claimant_name: data.claimant_name || '',
      reason_codes: data.reason_codes || [],
      reason_code_labels: data.reason_code_labels || [],
      form_data: data.form_data || {},
      documents: (data.documents || []).map((d: any) => ({
        id: d.id, filename: d.file_name || d.filename || '', doc_type: d.doc_type || '',
        uploaded_at: d.created_at || '', size: d.size_bytes || 0,
      })),
      validation_errors: data.validation_errors || [],
      validation_warnings: data.validation_warnings || [],
      narrative: data.narrative || '',
      attested: data.attestation_accepted || false,
      attested_at: null,
    } as Submission;
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
    const { data } = await api.post('/submissions/', { case_id: caseId });
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
    const { data } = await api.get('/dashboard/');
    return { total_cases: data.total_cases, draft_submissions: data.submissions_by_status?.draft || 0,
      submitted: data.submissions_by_status?.submitted || 0, accepted: data.submissions_by_status?.accepted || 0,
      rejected: data.submissions_by_status?.rejected || 0 } as DashboardStats;
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
    const { data } = await api.get('/dashboard/reason-codes/');
    return (data.breakdown || []) as ReasonCodeBreakdown[];
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
    const { data } = await api.get('/dashboard/');
    return (data.recent_submissions || []) as RecentSubmission[];
  },
};

// ---------- Onboarding API ----------

export const onboardingApi = {
  signup: async (payload: { email: string; password: string; name: string; organization: string }) => {
    if (isDevBypass) {
      return { success: true, message: 'Account created (dev mode).' };
    }
    const { data } = await api.post('/onboarding//signup', payload);
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

// ---------- Provider Types ----------

export interface AuthRequest {
  id: string;
  patient_name: string;
  patient_dob: string;
  patient_mrn: string;
  diagnosis: string;
  icd10_codes: string[];
  procedure_name: string;
  cpt_code: string;
  payer: string;
  insurance_type: string;
  surgeon_name: string;
  surgeon_npi: string;
  clinical_urgency: 'routine' | 'urgent' | 'emergent';
  wcb_case_number: string;
  status: 'draft' | 'submitted' | 'in_review' | 'approved' | 'denied' | 'appealed';
  narrative: string;
  compliance_score: number | null;
  missing_elements: string[];
  documents: AuthDocument[];
  submitted_at: string | null;
  decision_date: string | null;
  denial_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthDocument {
  id: string;
  filename: string;
  doc_type: string;
  uploaded_at: string;
  size: number;
}

export interface ComplianceResult {
  overall_score: number;
  approval_probability: number;
  checklist: ComplianceItem[];
  missing_items: string[];
  recommendations: string[];
}

export interface ComplianceItem {
  label: string;
  met: boolean;
  details: string;
  weight: number;
}

export interface ProviderDashboardData {
  pending_auths: number;
  awaiting_decision: number;
  approved_this_month: number;
  denied_this_month: number;
  approval_rate: number;
  compliance_score: number;
  recent_auths: AuthRequest[];
}

// ---------- Provider API ----------

const devAuthRequests: AuthRequest[] = [
  {
    id: 'auth-1',
    patient_name: 'James P. Morrison',
    patient_dob: '1965-03-14',
    patient_mrn: 'MRN-10042',
    diagnosis: 'Lumbar spinal stenosis with neurogenic claudication',
    icd10_codes: ['M48.06', 'G95.29'],
    procedure_name: 'Lumbar Laminectomy L4-L5',
    cpt_code: '63047',
    payer: 'UHC',
    insurance_type: 'commercial',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'routine',
    wcb_case_number: '',
    status: 'approved',
    narrative: 'Patient presents with progressive lumbar spinal stenosis at L4-L5 with neurogenic claudication refractory to 12 weeks of conservative management including physical therapy, epidural steroid injections, and oral analgesics. MRI confirms severe central canal stenosis. Surgical decompression is medically necessary.',
    compliance_score: 94,
    missing_elements: [],
    documents: [
      { id: 'adoc-1', filename: 'MRI_Lumbar_Morrison.pdf', doc_type: 'Imaging', uploaded_at: '2026-03-01T09:00:00Z', size: 2400000 },
      { id: 'adoc-2', filename: 'PT_Notes_Morrison.pdf', doc_type: 'Clinical Notes', uploaded_at: '2026-03-01T09:05:00Z', size: 156000 },
    ],
    submitted_at: '2026-03-05T10:00:00Z',
    decision_date: '2026-03-12T14:00:00Z',
    denial_reason: null,
    created_at: '2026-03-01T08:00:00Z',
    updated_at: '2026-03-12T14:00:00Z',
  },
  {
    id: 'auth-2',
    patient_name: 'Linda R. Vasquez',
    patient_dob: '1972-08-22',
    patient_mrn: 'MRN-10058',
    diagnosis: 'Right rotator cuff tear, complete',
    icd10_codes: ['M75.121'],
    procedure_name: 'Arthroscopic Rotator Cuff Repair',
    cpt_code: '29827',
    payer: 'Aetna',
    insurance_type: 'commercial',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'urgent',
    wcb_case_number: '',
    status: 'submitted',
    narrative: 'Patient sustained complete right rotator cuff tear confirmed by MRI. Conservative treatment including PT and corticosteroid injection failed to provide relief. Surgical repair is indicated to prevent further tendon retraction and muscle atrophy.',
    compliance_score: 87,
    missing_elements: ['Functional limitation documentation'],
    documents: [
      { id: 'adoc-3', filename: 'MRI_Shoulder_Vasquez.pdf', doc_type: 'Imaging', uploaded_at: '2026-03-20T11:00:00Z', size: 1800000 },
    ],
    submitted_at: '2026-03-22T09:00:00Z',
    decision_date: null,
    denial_reason: null,
    created_at: '2026-03-20T10:00:00Z',
    updated_at: '2026-03-22T09:00:00Z',
  },
  {
    id: 'auth-3',
    patient_name: 'Robert A. Kim',
    patient_dob: '1980-12-05',
    patient_mrn: 'MRN-10071',
    diagnosis: 'Cervical disc herniation C5-C6 with radiculopathy',
    icd10_codes: ['M50.122', 'M54.12'],
    procedure_name: 'ACDF C5-C6',
    cpt_code: '22551',
    payer: 'BCBS',
    insurance_type: 'commercial',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'routine',
    wcb_case_number: '',
    status: 'denied',
    narrative: 'Patient with cervical disc herniation at C5-C6 causing right upper extremity radiculopathy. EMG/NCS confirms C6 radiculopathy. Failed 8 weeks conservative care.',
    compliance_score: 62,
    missing_elements: ['Duration of conservative treatment inadequate per payer policy', 'Missing EMG/NCS report attachment', 'No functional outcome measures documented'],
    documents: [],
    submitted_at: '2026-02-28T14:00:00Z',
    decision_date: '2026-03-10T16:00:00Z',
    denial_reason: 'Insufficient documentation of conservative treatment failure. Payer requires minimum 12 weeks of documented conservative care.',
    created_at: '2026-02-25T09:00:00Z',
    updated_at: '2026-03-10T16:00:00Z',
  },
  {
    id: 'auth-4',
    patient_name: 'Patricia M. O\'Brien',
    patient_dob: '1958-05-17',
    patient_mrn: 'MRN-10089',
    diagnosis: 'Degenerative spondylolisthesis L4-L5',
    icd10_codes: ['M43.16', 'M47.816'],
    procedure_name: 'Posterior Lumbar Interbody Fusion L4-L5',
    cpt_code: '22630',
    payer: 'Medicare',
    insurance_type: 'medicare',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'routine',
    wcb_case_number: '',
    status: 'in_review',
    narrative: 'Patient presents with Grade II degenerative spondylolisthesis at L4-L5 with bilateral lower extremity symptoms and significant functional limitation. Failed 16 weeks of conservative treatment including physical therapy and epidural injections.',
    compliance_score: 91,
    missing_elements: ['Bone density scan recommended for fusion candidates over 65'],
    documents: [
      { id: 'adoc-4', filename: 'XR_Lumbar_OBrien.pdf', doc_type: 'Imaging', uploaded_at: '2026-04-01T08:00:00Z', size: 950000 },
      { id: 'adoc-5', filename: 'PT_Summary_OBrien.pdf', doc_type: 'Clinical Notes', uploaded_at: '2026-04-01T08:10:00Z', size: 210000 },
      { id: 'adoc-6', filename: 'ESI_Records_OBrien.pdf', doc_type: 'Procedure Report', uploaded_at: '2026-04-01T08:15:00Z', size: 340000 },
    ],
    submitted_at: '2026-04-02T10:00:00Z',
    decision_date: null,
    denial_reason: null,
    created_at: '2026-04-01T07:00:00Z',
    updated_at: '2026-04-02T10:00:00Z',
  },
  {
    id: 'auth-5',
    patient_name: 'David W. Thompson',
    patient_dob: '1975-09-30',
    patient_mrn: 'MRN-10095',
    diagnosis: 'Left knee medial meniscus tear',
    icd10_codes: ['M23.212'],
    procedure_name: 'Arthroscopic Meniscectomy',
    cpt_code: '29881',
    payer: 'Cigna',
    insurance_type: 'workers_comp',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'urgent',
    wcb_case_number: 'WCB-2026-003344',
    status: 'draft',
    narrative: '',
    compliance_score: null,
    missing_elements: [],
    documents: [],
    submitted_at: null,
    decision_date: null,
    denial_reason: null,
    created_at: '2026-04-10T14:00:00Z',
    updated_at: '2026-04-10T14:00:00Z',
  },
];

export const providerApi = {
  listAuthRequests: async (filters?: { status?: string; payer?: string; search?: string }) => {
    let results = [...devAuthRequests];
    if (filters?.status) results = results.filter((a) => a.status === filters.status);
    if (filters?.payer) results = results.filter((a) => a.payer === filters.payer);
    if (filters?.search) {
      const q = filters.search.toLowerCase();
      results = results.filter((a) => a.patient_name.toLowerCase().includes(q) || a.procedure_name.toLowerCase().includes(q) || a.cpt_code.includes(q));
    }
    return results;
  },

  getAuthRequest: async (id: string) => {
    return devAuthRequests.find((a) => a.id === id) || devAuthRequests[0];
  },

  createAuthRequest: async (data: Partial<AuthRequest>) => {
    const newAuth: AuthRequest = {
      id: `auth-${Date.now()}`,
      patient_name: data.patient_name || '',
      patient_dob: data.patient_dob || '',
      patient_mrn: data.patient_mrn || '',
      diagnosis: data.diagnosis || '',
      icd10_codes: data.icd10_codes || [],
      procedure_name: data.procedure_name || '',
      cpt_code: data.cpt_code || '',
      payer: data.payer || '',
      insurance_type: data.insurance_type || 'commercial',
      surgeon_name: data.surgeon_name || 'Dr. Dev Surgeon',
      surgeon_npi: data.surgeon_npi || '1234567890',
      clinical_urgency: data.clinical_urgency || 'routine',
      wcb_case_number: data.wcb_case_number || '',
      status: 'draft',
      narrative: data.narrative || '',
      compliance_score: null,
      missing_elements: [],
      documents: [],
      submitted_at: null,
      decision_date: null,
      denial_reason: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    devAuthRequests.push(newAuth);
    return newAuth;
  },

  uploadDocument: async (authId: string, file: File, docType: string) => {
    const doc: AuthDocument = {
      id: `adoc-${Date.now()}`,
      filename: file.name,
      doc_type: docType,
      uploaded_at: new Date().toISOString(),
      size: file.size,
    };
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (auth) auth.documents.push(doc);
    return doc;
  },

  generateNarrative: async (authId: string) => {
    await new Promise((r) => setTimeout(r, 1500));
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (!auth) return { narrative: '' };
    const narrative = `Patient ${auth.patient_name} (DOB: ${auth.patient_dob}) presents with ${auth.diagnosis}. Clinical evaluation and diagnostic imaging confirm the diagnosis (ICD-10: ${(auth.icd10_codes || []).join(', ')}). The patient has undergone a comprehensive course of conservative treatment including physical therapy, pharmacological management, and activity modification without adequate symptomatic relief.\n\nThe proposed procedure, ${auth.procedure_name} (CPT: ${auth.cpt_code}), is medically necessary based on the following clinical findings: persistent symptoms despite conservative measures, progressive functional decline, and objective imaging findings consistent with surgical pathology. The procedure meets established medical necessity criteria per ${auth.payer} guidelines.\n\nWithout surgical intervention, the patient faces continued functional impairment and risk of progressive neurological deterioration. The expected outcome of the proposed procedure includes pain reduction, functional restoration, and prevention of further deterioration.`;
    auth.narrative = narrative;
    return { narrative };
  },

  optimizeNarrative: async (authId: string) => {
    await new Promise((r) => setTimeout(r, 1200));
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (!auth) return { narrative: '' };
    const prefix = `[OPTIMIZED FOR ${auth.payer.toUpperCase()} GUIDELINES]\n\n`;
    const optimized = prefix + auth.narrative + `\n\nThis request aligns with ${auth.payer} medical policy requirements including documented failure of conservative treatment, appropriate diagnostic confirmation, and clinical indication meeting LCD/NCD criteria.`;
    auth.narrative = optimized;
    return { narrative: optimized };
  },

  checkCompliance: async (_procedureKey: string, data: Partial<AuthRequest>) => {
    await new Promise((r) => setTimeout(r, 1000));
    const hasNarrative = !!(data.narrative && data.narrative.length > 50);
    const hasDocs = (data.documents || []).length > 0;
    const hasConservative = (data.narrative || '').toLowerCase().includes('conservative');
    const hasImaging = (data.documents || []).some((d) => d.doc_type === 'Imaging') || (data.narrative || '').toLowerCase().includes('mri') || (data.narrative || '').toLowerCase().includes('imaging');
    const hasDiagnosis = !!(data.diagnosis && data.icd10_codes && data.icd10_codes.length > 0);
    const hasFunctional = (data.narrative || '').toLowerCase().includes('functional');

    const checklist: ComplianceItem[] = [
      { label: 'Clinical narrative provided', met: hasNarrative, details: hasNarrative ? 'Narrative meets minimum length requirement' : 'Narrative is missing or too short', weight: 20 },
      { label: 'Supporting documentation attached', met: hasDocs, details: hasDocs ? `${(data.documents || []).length} document(s) attached` : 'No supporting documents uploaded', weight: 15 },
      { label: 'Conservative treatment documented', met: hasConservative, details: hasConservative ? 'Conservative treatment failure documented' : 'No mention of conservative treatment in narrative', weight: 20 },
      { label: 'Diagnostic imaging referenced', met: hasImaging, details: hasImaging ? 'Imaging studies referenced' : 'No imaging studies referenced or attached', weight: 15 },
      { label: 'Diagnosis with ICD-10 codes', met: hasDiagnosis, details: hasDiagnosis ? `Diagnosis: ${data.diagnosis}` : 'Primary diagnosis or ICD-10 codes missing', weight: 15 },
      { label: 'Functional limitation documented', met: hasFunctional, details: hasFunctional ? 'Functional impact described' : 'No functional limitation documentation found', weight: 15 },
    ];

    const totalWeight = checklist.reduce((s, c) => s + c.weight, 0);
    const metWeight = checklist.filter((c) => c.met).reduce((s, c) => s + c.weight, 0);
    const overallScore = Math.round((metWeight / totalWeight) * 100);
    const approvalProb = Math.min(Math.round(overallScore * 1.05), 99);

    const missingItems = checklist.filter((c) => !c.met).map((c) => c.label);
    const recommendations = checklist.filter((c) => !c.met).map((c) => c.details);

    const auth = devAuthRequests.find((a) => a.id === data.id);
    if (auth) {
      auth.compliance_score = overallScore;
      auth.missing_elements = missingItems;
    }

    return {
      overall_score: overallScore,
      approval_probability: approvalProb,
      checklist,
      missing_items: missingItems,
      recommendations,
    } as ComplianceResult;
  },

  submitAuth: async (authId: string) => {
    await new Promise((r) => setTimeout(r, 1000));
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (auth) {
      auth.status = 'submitted';
      auth.submitted_at = new Date().toISOString();
      auth.updated_at = new Date().toISOString();
    }
    return auth;
  },

  recordDenial: async (authId: string, reason: string) => {
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (auth) {
      auth.status = 'denied';
      auth.denial_reason = reason;
      auth.decision_date = new Date().toISOString();
      auth.updated_at = new Date().toISOString();
    }
    return auth;
  },

  generateAppeal: async (authId: string) => {
    await new Promise((r) => setTimeout(r, 1500));
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (!auth) return { appeal_narrative: '' };
    const appeal = `APPEAL NARRATIVE - ${auth.patient_name}\n\nThis letter constitutes a formal appeal of the denial of prior authorization for ${auth.procedure_name} (CPT: ${auth.cpt_code}).\n\nDenial Reason: ${auth.denial_reason || 'Not specified'}\n\nRebuttal: The initial submission has been supplemented with additional clinical documentation demonstrating medical necessity. The patient continues to experience significant functional limitations despite the documented course of conservative treatment. Updated clinical findings and peer-reviewed literature support the medical necessity of the proposed procedure.\n\nWe respectfully request reconsideration of this determination based on the totality of clinical evidence presented.`;
    auth.status = 'appealed';
    auth.updated_at = new Date().toISOString();
    return { appeal_narrative: appeal };
  },

  recordOutcome: async (authId: string, outcome: string, notes: string) => {
    const auth = devAuthRequests.find((a) => a.id === authId);
    if (auth) {
      auth.status = outcome as AuthRequest['status'];
      auth.decision_date = new Date().toISOString();
      auth.updated_at = new Date().toISOString();
      if (outcome === 'denied') auth.denial_reason = notes;
    }
    return auth;
  },

  dashboard: async () => {
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const approvedThisMonth = devAuthRequests.filter((a) => a.status === 'approved' && a.decision_date && new Date(a.decision_date) >= monthStart).length;
    const deniedThisMonth = devAuthRequests.filter((a) => a.status === 'denied' && a.decision_date && new Date(a.decision_date) >= monthStart).length;
    const totalDecided = approvedThisMonth + deniedThisMonth;
    const approvalRate = totalDecided > 0 ? Math.round((approvedThisMonth / totalDecided) * 100) : 0;

    const avgScore = devAuthRequests.filter((a) => a.compliance_score !== null).reduce((sum, a) => sum + (a.compliance_score || 0), 0) / Math.max(devAuthRequests.filter((a) => a.compliance_score !== null).length, 1);

    return {
      pending_auths: devAuthRequests.filter((a) => a.status === 'draft').length,
      awaiting_decision: devAuthRequests.filter((a) => a.status === 'submitted' || a.status === 'in_review').length,
      approved_this_month: approvedThisMonth,
      denied_this_month: deniedThisMonth,
      approval_rate: approvalRate,
      compliance_score: Math.round(avgScore),
      recent_auths: devAuthRequests.slice(0, 10),
    } as ProviderDashboardData;
  },
};

export default api;
