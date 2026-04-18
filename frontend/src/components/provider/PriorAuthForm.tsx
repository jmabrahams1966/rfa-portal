import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { providerApi, type AuthRequest, type ComplianceResult, type AuthDocument } from '../../services/api';

const payers = [
  { name: 'Workers\' Compensation (WC)', key: 'workers_comp', category: 'WC / No-Fault' },
  { name: 'No-Fault (PIP / Auto)', key: 'no_fault', category: 'WC / No-Fault' },
  { name: 'UnitedHealthcare', key: 'uhc', category: 'Commercial' },
  { name: 'Aetna', key: 'aetna', category: 'Commercial' },
  { name: 'Blue Cross Blue Shield', key: 'bcbs', category: 'Commercial' },
  { name: 'Cigna', key: 'cigna', category: 'Commercial' },
  { name: 'Humana', key: 'humana', category: 'Commercial' },
  { name: 'EmblemHealth', key: 'emblem_health', category: 'Commercial' },
  { name: 'Medicare', key: 'medicare', category: 'Government' },
  { name: 'Medicaid (NY)', key: 'medicaid_ny', category: 'Government' },
];
const insuranceTypes = [
  { value: 'workers_comp', label: 'Workers\' Compensation' },
  { value: 'no_fault', label: 'No-Fault (PIP / Auto)' },
  { value: 'commercial', label: 'Commercial Insurance' },
  { value: 'medicare', label: 'Medicare' },
  { value: 'medicaid', label: 'Medicaid' },
];
const urgencyLevels = [
  { value: 'routine', label: 'Routine', color: 'text-gray-600' },
  { value: 'urgent', label: 'Urgent', color: 'text-amber-600' },
  { value: 'emergent', label: 'Emergent', color: 'text-red-600' },
];
const docTypes = ['Imaging', 'Clinical Notes', 'Lab Results', 'IME Report', 'Procedure Report', 'Physical Therapy Notes', 'Operative Report', 'Other'];

const procedureLibrary = [
  { name: 'Lumbar Laminectomy', cpt: '63047', category: 'Spine' },
  { name: 'Lumbar Microdiscectomy', cpt: '63030', category: 'Spine' },
  { name: 'ACDF (Anterior Cervical Discectomy & Fusion)', cpt: '22551', category: 'Spine' },
  { name: 'Posterior Lumbar Interbody Fusion (PLIF)', cpt: '22630', category: 'Spine' },
  { name: 'Lateral Lumbar Interbody Fusion (LLIF)', cpt: '22633', category: 'Spine' },
  { name: 'Cervical Laminoplasty', cpt: '63050', category: 'Spine' },
  { name: 'Arthroscopic Rotator Cuff Repair', cpt: '29827', category: 'Shoulder' },
  { name: 'Arthroscopic Meniscectomy', cpt: '29881', category: 'Knee' },
  { name: 'Total Knee Arthroplasty', cpt: '27447', category: 'Knee' },
  { name: 'Total Hip Arthroplasty', cpt: '27130', category: 'Hip' },
  { name: 'Carpal Tunnel Release', cpt: '64721', category: 'Hand/Wrist' },
  { name: 'ACL Reconstruction', cpt: '29888', category: 'Knee' },
  { name: 'Spinal Cord Stimulator Trial', cpt: '63650', category: 'Pain' },
  { name: 'Epidural Steroid Injection (Lumbar)', cpt: '62323', category: 'Pain' },
  { name: 'Epidural Steroid Injection (Cervical)', cpt: '62321', category: 'Pain' },
];

export default function PriorAuthForm() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    patient_name: '',
    patient_dob: '',
    patient_mrn: '',
    diagnosis: '',
    icd10_codes: '',
    procedure_name: '',
    cpt_code: '',
    payer: '',
    insurance_type: 'commercial',
    surgeon_name: 'Dr. Dev Surgeon',
    surgeon_npi: '1234567890',
    clinical_urgency: 'routine' as 'routine' | 'urgent' | 'emergent',
    wcb_case_number: '',
    narrative: '',
  });

  const [documents, setDocuments] = useState<AuthDocument[]>([]);
  const [selectedDocType, setSelectedDocType] = useState('Clinical Notes');
  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [procedureSearch, setProcedureSearch] = useState('');
  const [showProcedureDropdown, setShowProcedureDropdown] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [missingWarnings, setMissingWarnings] = useState<string[]>([]);

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const filteredProcedures = procedureLibrary.filter((p) => {
    const q = procedureSearch.toLowerCase();
    return !q || p.name.toLowerCase().includes(q) || p.cpt.includes(q) || p.category.toLowerCase().includes(q);
  });

  const selectProcedure = (proc: typeof procedureLibrary[0]) => {
    setForm((prev) => ({ ...prev, procedure_name: proc.name, cpt_code: proc.cpt }));
    setProcedureSearch('');
    setShowProcedureDropdown(false);
  };

  const handleFileDrop = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!savedId) {
      // Save first
      await handleSave();
    }
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const doc = await providerApi.uploadDocument(savedId || 'auth-temp', file, selectedDocType);
      setDocuments((prev) => [...prev, doc]);
    }
  }, [savedId, selectedDocType]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Partial<AuthRequest> = {
        ...form,
        icd10_codes: form.icd10_codes.split(',').map((c) => c.trim()).filter(Boolean),
        documents,
      };
      const result = await providerApi.createAuthRequest(payload);
      setSavedId(result.id);
      return result.id;
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateNarrative = async () => {
    let id = savedId;
    if (!id) id = (await handleSave()) || null;
    if (!id) return;
    setGenerating(true);
    try {
      const result = await providerApi.generateNarrative(id);
      setForm((prev) => ({ ...prev, narrative: result.narrative }));
    } finally {
      setGenerating(false);
    }
  };

  const handleOptimize = async () => {
    let id = savedId;
    if (!id) id = (await handleSave()) || null;
    if (!id) return;
    setOptimizing(true);
    try {
      const result = await providerApi.optimizeNarrative(id);
      setForm((prev) => ({ ...prev, narrative: result.narrative }));
    } finally {
      setOptimizing(false);
    }
  };

  const handleCheckCompliance = async () => {
    setChecking(true);
    try {
      const payload: Partial<AuthRequest> = {
        id: savedId || undefined,
        ...form,
        icd10_codes: form.icd10_codes.split(',').map((c) => c.trim()).filter(Boolean),
        documents,
      };
      const result = await providerApi.checkCompliance(form.cpt_code, payload);
      setCompliance(result);
    } finally {
      setChecking(false);
    }
  };

  const handleSubmit = async () => {
    // Validate required fields
    const warnings: string[] = [];
    if (!form.patient_name) warnings.push('Patient name is required');
    if (!form.diagnosis) warnings.push('Diagnosis is required');
    if (!form.procedure_name) warnings.push('Procedure is required');
    if (!form.payer) warnings.push('Payer is required');
    if (!form.narrative || form.narrative.length < 50) warnings.push('Clinical narrative is required (min 50 characters)');
    if (documents.length === 0) warnings.push('At least one supporting document is recommended');

    if (warnings.length > 0) {
      setMissingWarnings(warnings);
      return;
    }

    setSubmitting(true);
    try {
      let id = savedId;
      if (!id) id = (await handleSave()) || null;
      if (!id) return;
      await providerApi.submitAuth(id);
      navigate('/prior-auth');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => navigate('/prior-auth')}
            className="text-sm text-accent-500 hover:text-accent-600 font-medium mb-1 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Authorizations
          </button>
          <h1 className="text-2xl font-bold text-navy-700">New Prior Authorization</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-white border border-gray-300 text-navy-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Draft'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 bg-accent-500 text-white text-sm font-medium rounded-lg hover:bg-accent-600 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Submit Authorization'}
          </button>
        </div>
      </div>

      {/* Missing warnings */}
      {missingWarnings.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-red-800 mb-2">Please address the following before submitting:</h3>
          <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
            {missingWarnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
          <button onClick={() => setMissingWarnings([])} className="text-xs text-red-600 hover:text-red-800 mt-2">Dismiss</button>
        </div>
      )}

      <div className="space-y-6">
        {/* Patient Information */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Patient Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Patient Name *</label>
              <input
                type="text"
                value={form.patient_name}
                onChange={(e) => updateField('patient_name', e.target.value)}
                placeholder="Last, First MI"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
              <input
                type="date"
                value={form.patient_dob}
                onChange={(e) => updateField('patient_dob', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">MRN</label>
              <input
                type="text"
                value={form.patient_mrn}
                onChange={(e) => updateField('patient_mrn', e.target.value)}
                placeholder="MRN-XXXXX"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
          </div>
        </div>

        {/* Diagnosis */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Diagnosis</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Primary Diagnosis *</label>
              <input
                type="text"
                value={form.diagnosis}
                onChange={(e) => updateField('diagnosis', e.target.value)}
                placeholder="e.g., Lumbar spinal stenosis with neurogenic claudication"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ICD-10 Codes (comma-separated)</label>
              <input
                type="text"
                value={form.icd10_codes}
                onChange={(e) => updateField('icd10_codes', e.target.value)}
                placeholder="e.g., M48.06, G95.29"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
          </div>
        </div>

        {/* Procedure */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Proposed Procedure</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 mb-1">Procedure *</label>
              <input
                type="text"
                value={form.procedure_name || procedureSearch}
                onChange={(e) => {
                  if (form.procedure_name) {
                    setForm((prev) => ({ ...prev, procedure_name: '', cpt_code: '' }));
                  }
                  setProcedureSearch(e.target.value);
                  setShowProcedureDropdown(true);
                }}
                onFocus={() => setShowProcedureDropdown(true)}
                placeholder="Search by procedure name or CPT code..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
              {showProcedureDropdown && filteredProcedures.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {filteredProcedures.map((proc) => (
                    <button
                      key={proc.cpt}
                      onClick={() => selectProcedure(proc)}
                      className="w-full text-left px-4 py-2.5 hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0"
                    >
                      <div className="text-sm font-medium text-gray-800">{proc.name}</div>
                      <div className="text-xs text-gray-500">CPT {proc.cpt} | {proc.category}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CPT Code</label>
              <input
                type="text"
                value={form.cpt_code}
                onChange={(e) => updateField('cpt_code', e.target.value)}
                placeholder="e.g., 63047"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-gray-50"
              />
            </div>
          </div>
        </div>

        {/* Payer & Insurance */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Payer & Insurance</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Payer *</label>
              <select
                value={form.payer}
                onChange={(e) => updateField('payer', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
              >
                <option value="">Select Payer / Insurance Type</option>
                <optgroup label="Workers' Comp / No-Fault">
                  {payers.filter(p => p.category === 'WC / No-Fault').map((p) => (
                    <option key={p.key} value={p.key}>{p.name}</option>
                  ))}
                </optgroup>
                <optgroup label="Commercial Insurance">
                  {payers.filter(p => p.category === 'Commercial').map((p) => (
                    <option key={p.key} value={p.key}>{p.name}</option>
                  ))}
                </optgroup>
                <optgroup label="Government">
                  {payers.filter(p => p.category === 'Government').map((p) => (
                    <option key={p.key} value={p.key}>{p.name}</option>
                  ))}
                </optgroup>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Insurance Type</label>
              <select
                value={form.insurance_type}
                onChange={(e) => updateField('insurance_type', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
              >
                {insuranceTypes.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Clinical Urgency</label>
              <select
                value={form.clinical_urgency}
                onChange={(e) => updateField('clinical_urgency', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
              >
                {urgencyLevels.map((u) => (
                  <option key={u.value} value={u.value}>{u.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Workers Comp fields */}
          {form.insurance_type === 'workers_comp' && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">WCB Case Number *</label>
                <input type="text" value={form.wcb_case_number}
                  onChange={(e) => updateField('wcb_case_number', e.target.value)}
                  placeholder="G-1234567"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date of Injury *</label>
                <input type="date" value={form.date_of_injury || ''}
                  onChange={(e) => updateField('date_of_injury', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div className="md:col-span-2">
                <p className="text-xs text-amber-700">Workers' Comp submissions are checked against NYS WCB Medical Treatment Guidelines (MTG). The compliance checker will verify your submission meets all MTG requirements.</p>
              </div>
            </div>
          )}

          {/* No-Fault fields */}
          {form.insurance_type === 'no_fault' && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Claim Number *</label>
                <input type="text" value={form.wcb_case_number}
                  onChange={(e) => updateField('wcb_case_number', e.target.value)}
                  placeholder="NF-XXXX-XXXXX"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date of Accident *</label>
                <input type="date" value={form.date_of_injury || ''}
                  onChange={(e) => updateField('date_of_injury', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Auto Insurance Carrier</label>
                <input type="text" value={form.payer || ''}
                  onChange={(e) => updateField('payer', e.target.value)}
                  placeholder="e.g., GEICO, State Farm, Allstate"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">IME Scheduled?</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent-500">
                  <option value="">Select</option>
                  <option value="no">No</option>
                  <option value="scheduled">Yes — Scheduled</option>
                  <option value="completed">Yes — Completed</option>
                </select>
              </div>
              <div className="md:col-span-2">
                <p className="text-xs text-blue-700">No-Fault (PIP) submissions follow NY Insurance Law §5102. The compliance checker will verify medical necessity documentation and treatment timeline requirements.</p>
              </div>
            </div>
          )}
        </div>

        {/* Surgeon */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Surgeon</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Surgeon Name</label>
              <input
                type="text"
                value={form.surgeon_name}
                onChange={(e) => updateField('surgeon_name', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">NPI</label>
              <input
                type="text"
                value={form.surgeon_npi}
                onChange={(e) => updateField('surgeon_npi', e.target.value)}
                placeholder="10-digit NPI"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
            </div>
          </div>
        </div>

        {/* Documents */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-navy-700 mb-4">Supporting Documents</h2>

          <div className="flex gap-4 mb-4">
            <select
              value={selectedDocType}
              onChange={(e) => setSelectedDocType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 bg-white"
            >
              {docTypes.map((dt) => (
                <option key={dt} value={dt}>{dt}</option>
              ))}
            </select>
          </div>

          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragOver ? 'border-accent-500 bg-accent-50' : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFileDrop(e.dataTransfer.files); }}
            onClick={() => fileInputRef.current?.click()}
          >
            <svg className="w-10 h-10 text-gray-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-gray-600 font-medium">Drop files here or click to browse</p>
            <p className="text-xs text-gray-400 mt-1">PDF, DOC, DOCX, images up to 10MB each</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
            onChange={(e) => handleFileDrop(e.target.files)}
          />

          {/* Document list */}
          {documents.length > 0 && (
            <div className="mt-4 space-y-2">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between px-4 py-2.5 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <div>
                      <div className="text-sm font-medium text-gray-800">{doc.filename}</div>
                      <div className="text-xs text-gray-400">{doc.doc_type} | {(doc.size / 1024).toFixed(0)} KB</div>
                    </div>
                  </div>
                  <button
                    onClick={() => setDocuments((prev) => prev.filter((d) => d.id !== doc.id))}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clinical Narrative */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-navy-700">Clinical Narrative</h2>
            <div className="flex gap-2">
              <button
                onClick={handleGenerateNarrative}
                disabled={generating}
                className="px-3 py-1.5 bg-navy-700 text-white text-xs font-medium rounded-lg hover:bg-navy-800 transition-colors disabled:opacity-50"
              >
                {generating ? 'Generating...' : 'Generate Narrative'}
              </button>
              <button
                onClick={handleOptimize}
                disabled={optimizing || !form.narrative}
                className="px-3 py-1.5 bg-white border border-navy-700 text-navy-700 text-xs font-medium rounded-lg hover:bg-navy-50 transition-colors disabled:opacity-50"
              >
                {optimizing ? 'Optimizing...' : `Optimize for ${form.payer || 'Payer'}`}
              </button>
            </div>
          </div>

          <textarea
            value={form.narrative}
            onChange={(e) => updateField('narrative', e.target.value)}
            rows={10}
            placeholder="Enter or generate clinical narrative supporting medical necessity..."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 resize-y font-mono leading-relaxed"
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-gray-400">
              {form.narrative.length} characters
              {form.narrative.length > 0 && form.narrative.length < 50 && (
                <span className="text-amber-500 ml-2">Minimum 50 characters recommended</span>
              )}
            </p>
          </div>
        </div>

        {/* Compliance Check */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-navy-700">Compliance Check</h2>
            <button
              onClick={handleCheckCompliance}
              disabled={checking}
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {checking ? 'Checking...' : 'Check Compliance'}
            </button>
          </div>

          {compliance ? (
            <div className="space-y-4">
              {/* Score and probability */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-1">Compliance Score</div>
                  <div className="flex items-center gap-3">
                    <div className="text-3xl font-bold" style={{ color: compliance.overall_score >= 80 ? '#16a34a' : compliance.overall_score >= 60 ? '#d97706' : '#dc2626' }}>
                      {compliance.overall_score}%
                    </div>
                    <div className="flex-1">
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="h-3 rounded-full transition-all"
                          style={{
                            width: `${compliance.overall_score}%`,
                            backgroundColor: compliance.overall_score >= 80 ? '#16a34a' : compliance.overall_score >= 60 ? '#d97706' : '#dc2626',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-sm text-gray-500 mb-1">Estimated Approval Probability</div>
                  <div className="flex items-center gap-3">
                    <div className="text-3xl font-bold" style={{ color: compliance.approval_probability >= 75 ? '#16a34a' : compliance.approval_probability >= 50 ? '#d97706' : '#dc2626' }}>
                      {compliance.approval_probability}%
                    </div>
                    <div className="flex-1">
                      <div className="w-full h-3 rounded-full overflow-hidden" style={{ background: 'linear-gradient(90deg, #dc2626 0%, #d97706 40%, #16a34a 80%)' }}>
                        <div
                          className="h-3 bg-white/80 transition-all"
                          style={{ marginLeft: `${compliance.approval_probability}%`, width: `${100 - compliance.approval_probability}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Checklist */}
              <div className="space-y-2">
                {(compliance.checklist || []).map((item, idx) => (
                  <div key={idx} className={`flex items-start gap-3 p-3 rounded-lg ${item.met ? 'bg-green-50' : 'bg-red-50'}`}>
                    <span className="text-lg mt-0.5">{item.met ? '\u2705' : '\u274C'}</span>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${item.met ? 'text-green-800' : 'text-red-800'}`}>{item.label}</div>
                      <div className={`text-xs mt-0.5 ${item.met ? 'text-green-600' : 'text-red-600'}`}>{item.details}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Missing items */}
              {(compliance.missing_items || []).length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-amber-800 mb-2">Missing Elements</h3>
                  <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                    {compliance.missing_items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="text-sm">Click "Check Compliance" to analyze this request against payer requirements</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
