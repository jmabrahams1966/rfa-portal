import { useState, useCallback, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  casesApi,
  submissionsApi,
  type WCCase,
  type Submission,
  type ExtractionResult,
  type ValidationItem,
  type SubmissionDocument,
} from '../../services/api';
import { format } from 'date-fns';

const STEPS = [
  'Select Case',
  'Upload Documents',
  'AI Extraction',
  'Form Completion',
  'Supporting Docs',
  'Validation',
  'Review & Attest',
  'Confirmation',
];

const DOC_TYPES = [
  'IME Report',
  'Board Decision',
  'Medical Record',
  'Operative Note',
  'Wage Records',
  'Surveillance',
  'Other',
];

const REQUIRED_DOCS_BY_CODE: Record<string, string[]> = {
  MCI: ['IME Report', 'Medical Record'],
  PPD: ['IME Report', 'Medical Record'],
  TTD: ['Medical Record'],
  SLU: ['IME Report', 'Medical Record'],
  CLM: ['Medical Record'],
};

const confidenceColor = {
  HIGH: 'bg-green-100 text-green-800 border-green-200',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-200',
  LOW: 'bg-red-100 text-red-800 border-red-200',
};

export default function SubmissionWizard() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [currentStep, setCurrentStep] = useState(0);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [formData, setFormData] = useState<Record<string, string>>({
    certification_date: '',
    disability_classification: 'schedule_loss',
    degree_of_disability: '',
    body_parts: '',
    narrative: '',
  });
  const [validationResult, setValidationResult] = useState<{
    errors: ValidationItem[];
    warnings: ValidationItem[];
  } | null>(null);
  const [validating, setValidating] = useState(false);
  const [xmlPreview, setXmlPreview] = useState('');
  const [showXml, setShowXml] = useState(false);
  const [attested, setAttested] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completedSubmission, setCompletedSubmission] = useState<Submission | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<SubmissionDocument[]>([]);
  const [highestStep, setHighestStep] = useState(0);

  // File upload state
  const [pendingFiles, setPendingFiles] = useState<{ file: File; docType: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: wcCase } = useQuery<WCCase>({
    queryKey: ['case', caseId],
    queryFn: () => casesApi.get(caseId!),
    enabled: !!caseId,
  });

  const createSubmission = useMutation({
    mutationFn: () => submissionsApi.create(caseId!),
    onSuccess: (sub) => {
      setSubmissionId(sub.id);
    },
  });

  // Create submission on mount
  useEffect(() => {
    if (caseId && !submissionId) {
      createSubmission.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  const goToStep = useCallback(
    (step: number) => {
      if (step < 0 || step >= STEPS.length) return;
      // Can go back freely, but forward only if step <= highestStep + 1
      if (step <= highestStep || step === currentStep + 1) {
        setCurrentStep(step);
        if (step > highestStep) setHighestStep(step);
      }
    },
    [currentStep, highestStep],
  );

  const handleNext = useCallback(() => {
    goToStep(currentStep + 1);
  }, [currentStep, goToStep]);

  const handleBack = useCallback(() => {
    goToStep(currentStep - 1);
  }, [currentStep, goToStep]);

  // ---------- Step handlers ----------

  const handleConfirmCase = () => {
    handleNext();
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    const newPending = files.map((f) => ({ file: f, docType: 'Other' }));
    setPendingFiles((prev) => [...prev, ...newPending]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newPending = files.map((f) => ({ file: f, docType: 'Other' }));
    setPendingFiles((prev) => [...prev, ...newPending]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const updatePendingDocType = (index: number, docType: string) => {
    setPendingFiles((prev) => prev.map((p, i) => (i === index ? { ...p, docType } : p)));
  };

  const removePending = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadAll = async () => {
    if (!submissionId || pendingFiles.length === 0) return;
    setUploading(true);
    try {
      const uploaded: SubmissionDocument[] = [];
      for (const pf of pendingFiles) {
        const doc = await submissionsApi.uploadDoc(submissionId, pf.file, pf.docType);
        uploaded.push(doc);
      }
      setUploadedDocs((prev) => [...prev, ...uploaded]);
      setPendingFiles([]);
    } finally {
      setUploading(false);
    }
  };

  const handleExtract = async () => {
    if (!submissionId) return;
    setExtracting(true);
    try {
      const result = await submissionsApi.extract(submissionId);
      setExtraction(result);
      setSelectedCodes((result.reason_codes || []).map((r) => r.code));
      // Pre-fill form from extraction
      const fields = result.extracted_fields;
      setFormData((prev) => ({
        ...prev,
        certification_date: fields.certification_date?.value || prev.certification_date,
        disability_classification: fields.disability_classification?.value || prev.disability_classification,
        degree_of_disability: fields.degree_of_disability?.value || prev.degree_of_disability,
        body_parts: fields.body_parts?.value || prev.body_parts,
        narrative: fields.narrative?.value || prev.narrative,
      }));
    } finally {
      setExtracting(false);
    }
  };

  const handleValidate = async () => {
    if (!submissionId) return;
    setValidating(true);
    // Save form data first
    await submissionsApi.update(submissionId, {
      reason_codes: selectedCodes,
      narrative: formData.narrative,
      form_data: formData as unknown as Record<string, unknown>,
    });
    try {
      const result = await submissionsApi.validate(submissionId);
      setValidationResult(result);
    } finally {
      setValidating(false);
    }
  };

  const handleLoadXml = async () => {
    if (!submissionId) return;
    const xml = await submissionsApi.buildXml(submissionId);
    setXmlPreview(xml);
  };

  const handleAttest = async () => {
    if (!submissionId) return;
    await submissionsApi.attest(submissionId);
    setAttested(true);
  };

  const handleSubmit = async () => {
    if (!submissionId) return;
    setSubmitting(true);
    try {
      const result = await submissionsApi.submit(submissionId);
      if (result) {
        setCompletedSubmission(result);
        queryClient.invalidateQueries({ queryKey: ['cases'] });
        queryClient.invalidateQueries({ queryKey: ['submissions'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
        handleNext();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!submissionId) return;
    submissionsApi.downloadPdf(submissionId);
  };

  const narrativeLength = formData.narrative.length;
  const narrativeMax = 500;

  // ---------- Step rendering ----------

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return renderSelectCase();
      case 1:
        return renderUploadDocs();
      case 2:
        return renderExtraction();
      case 3:
        return renderFormCompletion();
      case 4:
        return renderSupportingDocs();
      case 5:
        return renderValidation();
      case 6:
        return renderReviewAttest();
      case 7:
        return renderConfirmation();
      default:
        return null;
    }
  };

  const renderSelectCase = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">Confirm Case Information</h2>
      {wcCase ? (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <Field label="WCB Case Number" value={wcCase.wcb_case_number} mono />
            <Field label="Claimant Name" value={wcCase.claimant_name} />
            <Field label="Date of Birth" value={wcCase.claimant_dob || '—'} />
            <Field label="Date of Injury" value={wcCase.date_of_injury || '—'} />
            <Field label="Employer" value={wcCase.employer_name} />
            <Field label="Carrier" value={`${wcCase.carrier_name} (${wcCase.carrier_code})`} />
          </div>
          <div className="mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={handleConfirmCase}
              className="px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
            >
              Confirm and Continue
            </button>
          </div>
        </div>
      ) : (
        <div className="text-gray-400">Loading case information...</div>
      )}
    </div>
  );

  const renderUploadDocs = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">Upload Supporting Documents</h2>

      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
          dragOver ? 'border-accent-500 bg-accent-50' : 'border-gray-300 hover:border-accent-400 bg-white'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.tiff"
        />
        <svg className="w-10 h-10 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-sm text-gray-600 font-medium">Drop files here or click to browse</p>
        <p className="text-xs text-gray-400 mt-1">PDF, DOC, DOCX, JPG, PNG, TIFF</p>
      </div>

      {/* Pending files */}
      {pendingFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="text-sm font-medium text-gray-700">Files to Upload</h3>
          {pendingFiles.map((pf, i) => (
            <div key={i} className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-2.5">
              <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm text-gray-700 flex-1 truncate">{pf.file.name}</span>
              <select
                value={pf.docType}
                onChange={(e) => updatePendingDocType(i, e.target.value)}
                className="text-xs border border-gray-300 rounded-lg px-2 py-1.5 focus:ring-2 focus:ring-accent-500 outline-none"
              >
                {DOC_TYPES.map((dt) => (
                  <option key={dt} value={dt}>{dt}</option>
                ))}
              </select>
              <button
                onClick={() => removePending(i)}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <button
            onClick={handleUploadAll}
            disabled={uploading}
            className="mt-2 px-5 py-2 bg-accent-500 hover:bg-accent-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : `Upload ${pendingFiles.length} File${pendingFiles.length > 1 ? 's' : ''}`}
          </button>
        </div>
      )}

      {/* Already uploaded */}
      {uploadedDocs.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Uploaded Documents</h3>
          <div className="space-y-1">
            {uploadedDocs.map((doc) => (
              <div key={doc.id} className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg px-4 py-2.5">
                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm text-gray-700 flex-1 truncate">{doc.filename}</span>
                <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded">{doc.doc_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderExtraction = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">AI Document Analysis</h2>

      {!extraction && !extracting && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <svg className="w-12 h-12 mx-auto text-accent-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <p className="text-gray-600 mb-4">
            Our AI will analyze your uploaded documents to extract reason codes, key dates, and relevant medical findings.
          </p>
          <button
            onClick={handleExtract}
            className="px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
          >
            Start AI Analysis
          </button>
        </div>
      )}

      {extracting && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <svg className="animate-spin w-10 h-10 mx-auto text-accent-500 mb-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          <p className="text-lg font-medium text-navy-700 mb-1">Analyzing documents...</p>
          <p className="text-sm text-gray-500">This may take a moment while our AI reviews your files.</p>
        </div>
      )}

      {extraction && !extracting && (
        <div className="space-y-6">
          {/* Reason codes */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Detected Reason Codes</h3>
            <div className="space-y-2">
              {(extraction.reason_codes || []).map((rc) => (
                <label key={rc.code} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedCodes.includes(rc.code)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedCodes((prev) => [...prev, rc.code]);
                      else setSelectedCodes((prev) => prev.filter((c) => c !== rc.code));
                    }}
                    className="w-4 h-4 text-accent-500 border-gray-300 rounded focus:ring-accent-500"
                  />
                  <span className="font-mono text-sm font-bold text-navy-700 bg-navy-50 px-2 py-0.5 rounded">
                    {rc.code}
                  </span>
                  <span className="text-sm text-gray-700 flex-1">{rc.label}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${confidenceColor[rc.confidence]}`}>
                    {rc.confidence}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Extracted fields */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-3">Extracted Fields</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(extraction.extracted_fields).map(([key, val]) => (
                <div key={key} className="flex items-start justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</div>
                    <div className="text-sm font-medium text-gray-800 mt-0.5">{val.value}</div>
                  </div>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${confidenceColor[val.confidence]} ml-2 flex-shrink-0`}>
                    {val.confidence}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleNext}
              className="px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
            >
              Confirm and Continue
            </button>
            <button
              onClick={handleExtract}
              className="px-4 py-2.5 border border-gray-300 text-gray-600 hover:bg-gray-50 font-medium rounded-lg transition-colors text-sm"
            >
              Re-analyze
            </button>
          </div>
        </div>
      )}
    </div>
  );

  const renderFormCompletion = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">Complete AIRA Form</h2>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
        {/* Selected reason codes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Selected Reason Codes</label>
          <div className="flex gap-2 flex-wrap">
            {selectedCodes.map((code) => (
              <span key={code} className="px-2.5 py-1 bg-navy-50 text-navy-700 rounded-lg text-sm font-mono font-semibold">
                {code}
              </span>
            ))}
          </div>
        </div>

        {/* Certification date */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Certification Date</label>
          <input
            type="date"
            value={formData.certification_date}
            onChange={(e) => setFormData((prev) => ({ ...prev, certification_date: e.target.value }))}
            className="w-full max-w-xs px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent-500 focus:border-accent-500 outline-none text-sm"
          />
        </div>

        {/* Disability classification (show for MCI/PPD/SLU) */}
        {(selectedCodes.includes('MCI') || selectedCodes.includes('PPD') || selectedCodes.includes('SLU')) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Disability Classification</label>
            <div className="flex flex-col gap-2">
              {[
                { value: 'schedule_loss', label: 'Schedule Loss of Use (SLU)' },
                { value: 'non_schedule', label: 'Non-Schedule (Permanent Partial / Total)' },
                { value: 'slu_addendum', label: 'SLU Addendum' },
              ].map((opt) => (
                <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="disability_classification"
                    value={opt.value}
                    checked={formData.disability_classification === opt.value}
                    onChange={(e) => setFormData((prev) => ({ ...prev, disability_classification: e.target.value }))}
                    className="w-4 h-4 text-accent-500 border-gray-300 focus:ring-accent-500"
                  />
                  <span className="text-sm text-gray-700">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Degree of disability */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Degree of Disability (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.degree_of_disability}
            onChange={(e) => setFormData((prev) => ({ ...prev, degree_of_disability: e.target.value }))}
            className="w-full max-w-xs px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent-500 focus:border-accent-500 outline-none text-sm"
            placeholder="e.g. 35"
          />
        </div>

        {/* Body parts */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Body Parts Affected</label>
          <input
            type="text"
            value={formData.body_parts}
            onChange={(e) => setFormData((prev) => ({ ...prev, body_parts: e.target.value }))}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent-500 focus:border-accent-500 outline-none text-sm"
            placeholder="e.g. Left knee, Right shoulder"
          />
        </div>

        {/* Narrative */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Narrative
            <span className={`ml-2 text-xs font-normal ${narrativeLength > narrativeMax ? 'text-red-500' : 'text-gray-400'}`}>
              {narrativeLength}/{narrativeMax}
            </span>
          </label>
          <textarea
            value={formData.narrative}
            onChange={(e) => setFormData((prev) => ({ ...prev, narrative: e.target.value }))}
            maxLength={narrativeMax}
            rows={6}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent-500 focus:border-accent-500 outline-none text-sm resize-none"
            placeholder="Provide a concise narrative summarizing the medical findings and basis for this filing..."
          />
          <div className="mt-1 flex justify-end">
            <div className="w-full max-w-[200px] bg-gray-100 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all ${
                  narrativeLength > narrativeMax ? 'bg-red-500' : narrativeLength > narrativeMax * 0.8 ? 'bg-amber-500' : 'bg-accent-500'
                }`}
                style={{ width: `${Math.min((narrativeLength / narrativeMax) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSupportingDocs = () => {
    const allRequired = selectedCodes.flatMap((code) => REQUIRED_DOCS_BY_CODE[code] || []);
    const uniqueRequired = [...new Set(allRequired)];
    const uploadedTypes = uploadedDocs.map((d) => d.doc_type);

    return (
      <div>
        <h2 className="text-lg font-semibold text-navy-700 mb-4">Supporting Documents Checklist</h2>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500 mb-4">
            The following documents are required based on your selected reason codes ({selectedCodes.join(', ')}).
          </p>
          <div className="space-y-3">
            {uniqueRequired.map((docType) => {
              const hasDoc = uploadedTypes.includes(docType);
              return (
                <div
                  key={docType}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${
                    hasDoc ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                  }`}
                >
                  {hasDoc ? (
                    <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                  <span className={`text-sm font-medium ${hasDoc ? 'text-green-800' : 'text-red-800'}`}>
                    {docType}
                  </span>
                  {hasDoc && (
                    <span className="text-xs text-green-600 ml-auto">Uploaded</span>
                  )}
                  {!hasDoc && (
                    <span className="text-xs text-red-500 ml-auto">Missing</span>
                  )}
                </div>
              );
            })}
            {uniqueRequired.length === 0 && (
              <p className="text-sm text-gray-400 py-4 text-center">No specific documents required for selected reason codes.</p>
            )}
          </div>

          {uniqueRequired.some((dt) => !uploadedTypes.includes(dt)) && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2">
              <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-amber-800">Missing Required Documents</p>
                <p className="text-xs text-amber-600 mt-0.5">
                  Some required documents have not been uploaded. You may still proceed, but missing documents may result in rejection by the WCB.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderValidation = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">Submission Validation</h2>

      {!validationResult && !validating && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-gray-600 mb-4">
            Run validation to check your submission for errors and warnings before filing with the WCB.
          </p>
          <button
            onClick={handleValidate}
            className="px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
          >
            Run Validation
          </button>
        </div>
      )}

      {validating && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <svg className="animate-spin w-8 h-8 mx-auto text-accent-500 mb-3" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          <p className="text-sm text-gray-600">Validating submission...</p>
        </div>
      )}

      {validationResult && !validating && (
        <div className="space-y-4">
          {/* Errors */}
          {validationResult.errors.length > 0 && (
            <div className="bg-white rounded-xl border border-red-200 p-5">
              <h3 className="text-sm font-semibold text-red-700 flex items-center gap-2 mb-3">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Errors ({validationResult.errors.length}) -- Must fix before submission
              </h3>
              <div className="space-y-2">
                {validationResult.errors.map((err, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-red-50 rounded-lg">
                    <span className="text-xs font-mono text-red-600 bg-red-100 px-1.5 py-0.5 rounded mt-0.5">{err.field}</span>
                    <span className="text-sm text-red-700 flex-1">{err.message}</span>
                    <button
                      onClick={() => {
                        if (err.field === 'narrative') {
                          setCurrentStep(3);
                        }
                      }}
                      className="text-xs text-red-600 hover:text-red-800 font-medium underline flex-shrink-0"
                    >
                      Fix
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {validationResult.warnings.length > 0 && (
            <div className="bg-white rounded-xl border border-amber-200 p-5">
              <h3 className="text-sm font-semibold text-amber-700 flex items-center gap-2 mb-3">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                Warnings ({validationResult.warnings.length})
              </h3>
              <div className="space-y-2">
                {validationResult.warnings.map((warn, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg">
                    <span className="text-xs font-mono text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded mt-0.5">{warn.field}</span>
                    <span className="text-sm text-amber-700 flex-1">{warn.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Success */}
          {validationResult.errors.length === 0 && validationResult.warnings.length === 0 && (
            <div className="bg-white rounded-xl border border-green-200 p-6 text-center">
              <svg className="w-10 h-10 mx-auto text-green-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-green-700 font-medium">All validations passed!</p>
              <p className="text-sm text-gray-500 mt-1">Your submission is ready for review.</p>
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={handleValidate}
              className="px-4 py-2 border border-gray-300 text-gray-600 hover:bg-gray-50 rounded-lg text-sm font-medium"
            >
              Re-validate
            </button>
            {validationResult.errors.length === 0 && (
              <button
                onClick={handleNext}
                className="px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
              >
                Continue to Review
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const renderReviewAttest = () => (
    <div>
      <h2 className="text-lg font-semibold text-navy-700 mb-4">Review and Attest</h2>

      <div className="space-y-6">
        {/* Form summary */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-navy-700 uppercase tracking-wide mb-4">Submission Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <Field label="WCB Case Number" value={wcCase?.wcb_case_number || ''} mono />
            <Field label="Claimant" value={wcCase?.claimant_name || ''} />
            <Field label="Date of Injury" value={wcCase ? wcCase.date_of_injury || '—' : ''} />
            <Field label="Reason Codes" value={selectedCodes.join(', ')} mono />
            <Field label="Certification Date" value={formData.certification_date} />
            <Field label="Degree of Disability" value={formData.degree_of_disability ? `${formData.degree_of_disability}%` : '--'} />
            <Field label="Body Parts" value={formData.body_parts || '--'} />
            <Field label="Classification" value={formData.disability_classification.replace(/_/g, ' ').toUpperCase()} />
            <Field label="Documents" value={`${uploadedDocs.length} file(s) attached`} />
          </div>
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Narrative</div>
            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{formData.narrative || '(No narrative provided)'}</p>
          </div>
        </div>

        {/* XML preview */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => {
              setShowXml(!showXml);
              if (!xmlPreview) handleLoadXml();
            }}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
          >
            <h3 className="text-sm font-semibold text-navy-700 uppercase tracking-wide">XML Preview</h3>
            <svg className={`w-4 h-4 text-gray-400 transition-transform ${showXml ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showXml && (
            <div className="px-6 pb-6">
              <pre className="bg-gray-900 text-green-400 rounded-lg p-4 text-xs overflow-x-auto max-h-64 overflow-y-auto font-mono">
                {xmlPreview || 'Loading...'}
              </pre>
            </div>
          )}
        </div>

        {/* Attestation */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={attested}
              onChange={(e) => {
                if (e.target.checked) handleAttest();
                else setAttested(false);
              }}
              className="w-5 h-5 mt-0.5 text-accent-500 border-gray-300 rounded focus:ring-accent-500"
            />
            <div>
              <p className="text-sm font-medium text-gray-800">Attestation</p>
              <p className="text-xs text-gray-500 mt-1">
                I hereby attest that the information provided in this AIRA submission is true, accurate, and complete to the best of my knowledge.
                I understand that filing a false or fraudulent claim is a violation of the Workers' Compensation Law and may subject me to civil
                and criminal penalties. I authorize the release of medical information contained herein to the Workers' Compensation Board.
              </p>
            </div>
          </label>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={!attested || submitting || (validationResult?.errors?.length ?? 0) > 0}
            className="px-8 py-3 bg-accent-500 hover:bg-accent-600 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                </svg>
                Submitting to WCB...
              </span>
            ) : (
              'Submit to WCB'
            )}
          </button>
          <button
            onClick={() => {
              const xml = submission?.xml_payload || xmlPreview || '';
              const blob = new Blob([xml], { type: 'application/xml' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `RFA2_${wcCase?.wcb_case_number || 'submission'}.xml`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="px-6 py-3 border border-navy-300 text-navy-700 hover:bg-navy-50 font-medium rounded-lg transition-colors text-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download XML
          </button>
          <a
            href="https://onboard.wcb.ny.gov"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 border border-blue-300 text-blue-700 hover:bg-blue-50 font-medium rounded-lg transition-colors text-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Open WCB eCase
          </a>
          {!attested && (
            <span className="text-xs text-gray-400">You must accept the attestation to submit.</span>
          )}
        </div>
      </div>
    </div>
  );

  const renderConfirmation = () => (
    <div>
      <div className="bg-white rounded-xl border border-green-200 p-8 text-center max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-navy-700 mb-2">Submission Successful</h2>
        <p className="text-gray-600 mb-6">Your AIRA has been submitted to the Workers' Compensation Board.</p>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">WCB Submission ID</div>
          <div className="text-lg font-mono font-bold text-navy-700">
            {completedSubmission?.wcb_submission_id || '--'}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {completedSubmission?.submitted_at && completedSubmission?.submitted_at?.slice(0,19) || '—'}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <button
            onClick={() => {
              const xml = submission?.xml_payload || '';
              const blob = new Blob([xml], { type: 'application/xml' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `RFA2_${wcCase?.wcb_case_number || 'submission'}.xml`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="w-full px-6 py-2.5 border border-navy-300 text-navy-700 hover:bg-navy-50 font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download XML for eCase
          </button>
          <a
            href="https://onboard.wcb.ny.gov"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full px-6 py-2.5 border border-blue-300 text-blue-700 hover:bg-blue-50 font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Open WCB eCase Portal
          </a>
          <button
            onClick={handleDownloadPdf}
            className="w-full px-6 py-2.5 border border-accent-500 text-accent-500 hover:bg-accent-50 font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download PDF Copy
          </button>
          <button
            onClick={() => navigate('/')}
            className="w-full px-6 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <button onClick={() => navigate('/cases')} className="hover:text-accent-500 transition-colors">Cases</button>
        <span>/</span>
        <span className="text-gray-500 font-mono">{wcCase?.wcb_case_number || '...'}</span>
        <span>/</span>
        <span className="text-gray-600">New Submission</span>
      </div>

      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          {STEPS.map((step, i) => (
            <button
              key={step}
              onClick={() => {
                if (i <= highestStep) goToStep(i);
              }}
              disabled={i > highestStep}
              className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
                i === currentStep
                  ? 'text-accent-500'
                  : i < currentStep
                  ? 'text-green-600 hover:text-green-700'
                  : i <= highestStep
                  ? 'text-gray-500 hover:text-gray-700 cursor-pointer'
                  : 'text-gray-300 cursor-not-allowed'
              }`}
            >
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-colors ${
                  i === currentStep
                    ? 'border-accent-500 bg-accent-500 text-white'
                    : i < currentStep
                    ? 'border-green-500 bg-green-500 text-white'
                    : i <= highestStep
                    ? 'border-gray-400 text-gray-500'
                    : 'border-gray-200 text-gray-300'
                }`}
              >
                {i < currentStep ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
              <span className="hidden lg:inline">{step}</span>
            </button>
          ))}
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-accent-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${((currentStep) / (STEPS.length - 1)) * 100}%` }}
          />
        </div>
      </div>

      {/* Step content */}
      <div className="min-h-[400px]">
        {renderStep()}
      </div>

      {/* Navigation buttons */}
      {currentStep > 0 && currentStep < 7 && (
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
          <button
            onClick={handleBack}
            className="px-5 py-2.5 border border-gray-300 text-gray-600 hover:bg-gray-50 font-medium rounded-lg transition-colors text-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          {currentStep !== 2 && currentStep !== 5 && currentStep !== 6 && (
            <button
              onClick={handleNext}
              className="px-5 py-2.5 bg-accent-500 hover:bg-accent-600 text-white font-medium rounded-lg transition-colors text-sm flex items-center gap-2"
            >
              Next
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">{label}</div>
      <div className={`text-sm font-medium text-gray-800 ${mono ? 'font-mono' : ''}`}>{value || '--'}</div>
    </div>
  );
}
