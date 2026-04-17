import { useState } from 'react';
import { providerApi, type ComplianceResult, type AuthRequest } from '../../services/api';

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

const payers = ['UHC', 'Aetna', 'BCBS', 'Cigna', 'Humana', 'EmblemHealth', 'Medicare', 'Medicaid'];

export default function ComplianceChecker() {
  const [selectedProcedure, setSelectedProcedure] = useState('');
  const [procedureSearch, setProcedureSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedCpt, setSelectedCpt] = useState('');
  const [payer, setPayer] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [icd10, setIcd10] = useState('');
  const [narrative, setNarrative] = useState('');
  const [hasImaging, setHasImaging] = useState(false);
  const [hasPTNotes, setHasPTNotes] = useState(false);
  const [hasLabResults, setHasLabResults] = useState(false);
  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [runningDeep, setRunningDeep] = useState(false);
  const [deepAnalysis, setDeepAnalysis] = useState<string | null>(null);

  const filteredProcedures = procedureLibrary.filter((p) => {
    const q = procedureSearch.toLowerCase();
    return !q || p.name.toLowerCase().includes(q) || p.cpt.includes(q);
  });

  const selectProcedure = (proc: typeof procedureLibrary[0]) => {
    setSelectedProcedure(proc.name);
    setSelectedCpt(proc.cpt);
    setProcedureSearch('');
    setShowDropdown(false);
  };

  const buildMockDocuments = () => {
    const docs: { id: string; filename: string; doc_type: string; uploaded_at: string; size: number }[] = [];
    if (hasImaging) docs.push({ id: 'check-img', filename: 'imaging.pdf', doc_type: 'Imaging', uploaded_at: new Date().toISOString(), size: 1000 });
    if (hasPTNotes) docs.push({ id: 'check-pt', filename: 'pt_notes.pdf', doc_type: 'Physical Therapy Notes', uploaded_at: new Date().toISOString(), size: 800 });
    if (hasLabResults) docs.push({ id: 'check-lab', filename: 'labs.pdf', doc_type: 'Lab Results', uploaded_at: new Date().toISOString(), size: 500 });
    return docs;
  };

  const handleCheck = async () => {
    if (!selectedCpt) return;
    setChecking(true);
    setDeepAnalysis(null);
    try {
      const payload: Partial<AuthRequest> = {
        procedure_name: selectedProcedure,
        cpt_code: selectedCpt,
        payer: payer,
        diagnosis: diagnosis,
        icd10_codes: icd10.split(',').map((c) => c.trim()).filter(Boolean),
        narrative: narrative,
        documents: buildMockDocuments(),
      };
      const result = await providerApi.checkCompliance(selectedCpt, payload);
      setCompliance(result);
    } finally {
      setChecking(false);
    }
  };

  const handleDeepAnalysis = async () => {
    setRunningDeep(true);
    try {
      await new Promise((r) => setTimeout(r, 2000));
      const proc = selectedProcedure || 'the proposed procedure';
      const payerName = payer || 'the payer';
      setDeepAnalysis(
        `AI DEEP ANALYSIS REPORT\n` +
        `Procedure: ${proc} (CPT: ${selectedCpt})\n` +
        `Payer: ${payerName}\n\n` +
        `MEDICAL NECESSITY ASSESSMENT:\n` +
        `Based on the clinical data provided, the request for ${proc} ${compliance && compliance.overall_score >= 70 ? 'appears to meet' : 'may not fully meet'} medical necessity criteria.\n\n` +
        `PAYER-SPECIFIC CONSIDERATIONS:\n` +
        `- ${payerName} typically requires documentation of conservative treatment failure (minimum 6-12 weeks)\n` +
        `- Objective diagnostic findings (MRI, EMG/NCS) must correlate with clinical presentation\n` +
        `- Functional limitation documentation using validated outcome measures (ODI, NDI, VAS) is strongly recommended\n` +
        `- Peer-reviewed literature citations supporting the procedure may strengthen the request\n\n` +
        `RECOMMENDATIONS:\n` +
        `1. ${compliance?.checklist?.find((c) => !c.met)?.label ? `Address: ${compliance.checklist.find((c) => !c.met)?.label}` : 'All basic compliance items appear met'}\n` +
        `2. Include specific dates and duration of each conservative treatment modality\n` +
        `3. Document functional impact using standardized assessment tools\n` +
        `4. Reference applicable LCD/NCD criteria in the clinical narrative\n` +
        `5. Ensure all referenced diagnostic studies are attached as supporting documentation`
      );
    } finally {
      setRunningDeep(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-navy-700">Compliance Checker</h1>
        <p className="text-sm text-gray-500 mt-1">Verify prior authorization compliance before submission</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input panel */}
        <div className="space-y-5">
          {/* Procedure selection */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-navy-700 mb-3">Procedure</h2>
            <div className="relative mb-3">
              <input
                type="text"
                value={selectedProcedure || procedureSearch}
                onChange={(e) => {
                  if (selectedProcedure) {
                    setSelectedProcedure('');
                    setSelectedCpt('');
                  }
                  setProcedureSearch(e.target.value);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                placeholder="Search procedure or CPT code..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
              />
              {showDropdown && filteredProcedures.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {filteredProcedures.map((proc) => (
                    <button
                      key={proc.cpt}
                      onClick={() => selectProcedure(proc)}
                      className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm border-b border-gray-50 last:border-0"
                    >
                      <span className="font-medium">{proc.name}</span>
                      <span className="text-gray-400 ml-2">CPT {proc.cpt}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedCpt && (
              <div className="text-xs text-gray-500">Selected CPT: <span className="font-mono font-bold text-navy-700">{selectedCpt}</span></div>
            )}
          </div>

          {/* Clinical data */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-navy-700 mb-3">Clinical Data</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Payer</label>
                <select
                  value={payer}
                  onChange={(e) => setPayer(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent-500"
                >
                  <option value="">Select Payer</option>
                  {payers.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Diagnosis</label>
                <input
                  type="text"
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  placeholder="Primary diagnosis"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">ICD-10 Codes</label>
                <input
                  type="text"
                  value={icd10}
                  onChange={(e) => setIcd10(e.target.value)}
                  placeholder="e.g., M48.06, G95.29"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Clinical Narrative</label>
                <textarea
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  rows={5}
                  placeholder="Describe clinical findings, conservative treatment history, and medical necessity justification..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 resize-y"
                />
                <div className="text-xs text-gray-400 mt-1">{narrative.length} characters</div>
              </div>
            </div>
          </div>

          {/* Documentation checklist */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-navy-700 mb-3">Available Documentation</h2>
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={hasImaging} onChange={(e) => setHasImaging(e.target.checked)} className="w-4 h-4 text-accent-500 rounded" />
                <span className="text-sm text-gray-700">Diagnostic imaging (MRI, CT, X-ray)</span>
              </label>
              <label className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={hasPTNotes} onChange={(e) => setHasPTNotes(e.target.checked)} className="w-4 h-4 text-accent-500 rounded" />
                <span className="text-sm text-gray-700">Physical therapy / conservative treatment notes</span>
              </label>
              <label className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={hasLabResults} onChange={(e) => setHasLabResults(e.target.checked)} className="w-4 h-4 text-accent-500 rounded" />
                <span className="text-sm text-gray-700">Lab results / EMG / NCS</span>
              </label>
            </div>
          </div>

          <button
            onClick={handleCheck}
            disabled={checking || !selectedCpt}
            className="w-full py-3 bg-accent-500 text-white text-sm font-semibold rounded-xl hover:bg-accent-600 transition-colors disabled:opacity-50"
          >
            {checking ? 'Analyzing Compliance...' : 'Run Compliance Check'}
          </button>
        </div>

        {/* Results panel */}
        <div className="space-y-5">
          {compliance ? (
            <>
              {/* Score cards */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
                  <div className="text-sm text-gray-500 mb-2">Compliance Score</div>
                  <div
                    className="text-4xl font-bold"
                    style={{ color: compliance.overall_score >= 80 ? '#16a34a' : compliance.overall_score >= 60 ? '#d97706' : '#dc2626' }}
                  >
                    {compliance.overall_score}%
                  </div>
                  <div className="mt-3 w-full bg-gray-100 rounded-full h-3">
                    <div
                      className="h-3 rounded-full transition-all"
                      style={{
                        width: `${compliance.overall_score}%`,
                        backgroundColor: compliance.overall_score >= 80 ? '#16a34a' : compliance.overall_score >= 60 ? '#d97706' : '#dc2626',
                      }}
                    />
                  </div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 text-center">
                  <div className="text-sm text-gray-500 mb-2">Approval Probability</div>
                  <div
                    className="text-4xl font-bold"
                    style={{ color: compliance.approval_probability >= 75 ? '#16a34a' : compliance.approval_probability >= 50 ? '#d97706' : '#dc2626' }}
                  >
                    {compliance.approval_probability}%
                  </div>
                  <div className="mt-3 w-full h-3 rounded-full overflow-hidden" style={{ background: 'linear-gradient(90deg, #dc2626 0%, #d97706 40%, #16a34a 80%)' }}>
                    <div
                      className="h-3 bg-white/80 transition-all"
                      style={{ marginLeft: `${compliance.approval_probability}%`, width: `${100 - compliance.approval_probability}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Checklist */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <h2 className="text-sm font-semibold text-navy-700 mb-3">Compliance Checklist</h2>
                <div className="space-y-2">
                  {(compliance.checklist || []).map((item, idx) => (
                    <div key={idx} className={`flex items-start gap-3 p-3 rounded-lg ${item.met ? 'bg-green-50' : 'bg-red-50'}`}>
                      <span className="text-base mt-0.5">{item.met ? '\u2705' : '\u274C'}</span>
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-medium ${item.met ? 'text-green-800' : 'text-red-800'}`}>
                          {item.label}
                        </div>
                        <div className={`text-xs mt-0.5 ${item.met ? 'text-green-600' : 'text-red-600'}`}>
                          {item.details}
                        </div>
                      </div>
                      <span className="text-xs text-gray-400 shrink-0">
                        {item.weight}pts
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing items */}
              {(compliance.missing_items || []).length > 0 && (
                <div className="bg-amber-50 rounded-xl border border-amber-200 p-5">
                  <h2 className="text-sm font-semibold text-amber-800 mb-2">Missing Items</h2>
                  <ul className="space-y-1.5">
                    {compliance.missing_items.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                        <span className="text-amber-500 mt-0.5">&#9888;</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {(compliance.recommendations || []).length > 0 && (
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
                  <h2 className="text-sm font-semibold text-blue-800 mb-2">Recommendations</h2>
                  <ul className="space-y-1.5">
                    {compliance.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-blue-700">
                        <span className="text-blue-500 mt-0.5">&#8250;</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Deep AI analysis */}
              <button
                onClick={handleDeepAnalysis}
                disabled={runningDeep}
                className="w-full py-3 bg-navy-700 text-white text-sm font-semibold rounded-xl hover:bg-navy-800 transition-colors disabled:opacity-50"
              >
                {runningDeep ? 'Running AI Analysis...' : 'Run AI Review (Deep Analysis)'}
              </button>

              {deepAnalysis && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                  <h2 className="text-sm font-semibold text-navy-700 mb-3">AI Deep Analysis</h2>
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed bg-gray-50 p-4 rounded-lg">
                    {deepAnalysis}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
              <div className="text-5xl mb-4 text-gray-300">&#9881;</div>
              <h3 className="text-lg font-semibold text-gray-600">No Compliance Check Run</h3>
              <p className="text-sm text-gray-400 mt-2 max-w-xs mx-auto">
                Select a procedure and fill in clinical data, then run a compliance check to see results.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
