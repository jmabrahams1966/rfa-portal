import { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// ---------------------------------------------------------------------------
//  Procedure Library — expanded with full CPT code sets
// ---------------------------------------------------------------------------

interface Procedure {
  key: string;
  name: string;
  cpts: string[];
  category: string;
}

const PROCEDURES: Procedure[] = [
  // Spine / Neurosurgery
  { key: 'lumbar_fusion', name: 'Lumbar Spinal Fusion', cpts: ['22612', '22614', '22630', '22633'], category: 'Spine' },
  { key: 'lumbar_decompression', name: 'Lumbar Decompression (Laminectomy)', cpts: ['63047', '63048', '63030', '63035'], category: 'Spine' },
  { key: 'cervical_fusion_acdf', name: 'ACDF (Anterior Cervical Discectomy & Fusion)', cpts: ['22551', '22552'], category: 'Spine' },
  { key: 'cervical_decompression', name: 'Cervical Decompression', cpts: ['63020', '63040', '63045'], category: 'Spine' },
  { key: 'spinal_cord_stimulator', name: 'Spinal Cord Stimulator', cpts: ['63650', '63685'], category: 'Spine' },
  { key: 'epidural_steroid_injection', name: 'Epidural Steroid Injection', cpts: ['62321', '62322', '62323', '64483'], category: 'Pain' },
  { key: 'lumbar_disc_replacement', name: 'Lumbar Disc Replacement', cpts: ['22857'], category: 'Spine' },
  { key: 'cervical_disc_replacement', name: 'Cervical Disc Replacement', cpts: ['22856'], category: 'Spine' },
  { key: 'radiofrequency_ablation', name: 'Radiofrequency Ablation', cpts: ['64633', '64634', '64635', '64636'], category: 'Pain' },
  { key: 'facet_joint_injection', name: 'Facet Joint Injection', cpts: ['64490', '64491', '64492', '64493', '64494', '64495'], category: 'Pain' },
  // Orthopedic
  { key: 'total_knee_replacement', name: 'Total Knee Arthroplasty (TKA)', cpts: ['27447'], category: 'Knee' },
  { key: 'total_hip_replacement', name: 'Total Hip Arthroplasty (THA)', cpts: ['27130'], category: 'Hip' },
  { key: 'acl_reconstruction', name: 'ACL Reconstruction', cpts: ['29888'], category: 'Knee' },
  { key: 'rotator_cuff_repair', name: 'Rotator Cuff Repair', cpts: ['29827', '23412'], category: 'Shoulder' },
  { key: 'carpal_tunnel_release', name: 'Carpal Tunnel Release', cpts: ['64721'], category: 'Hand/Wrist' },
  { key: 'shoulder_arthroscopy', name: 'Shoulder Arthroscopy', cpts: ['29805', '29806', '29807'], category: 'Shoulder' },
  { key: 'knee_arthroscopy', name: 'Knee Arthroscopy / Meniscectomy', cpts: ['29880', '29881', '29882'], category: 'Knee' },
  { key: 'ankle_fracture_orif', name: 'Ankle Fracture ORIF', cpts: ['27766', '27792', '27814'], category: 'Ankle' },
  { key: 'achilles_repair', name: 'Achilles Tendon Repair', cpts: ['27650', '27654'], category: 'Ankle' },
  { key: 'trigger_finger_release', name: 'Trigger Finger Release', cpts: ['26055'], category: 'Hand/Wrist' },
  // Concussion / TBI
  { key: 'neuropsychological_testing', name: 'Neuropsychological Testing', cpts: ['96132', '96133', '96136', '96137'], category: 'Neuro' },
  { key: 'cognitive_rehabilitation', name: 'Cognitive Rehabilitation Therapy', cpts: ['97129', '97130'], category: 'Neuro' },
];

// ---------------------------------------------------------------------------
//  Payer List — grouped with backend key matching
// ---------------------------------------------------------------------------

interface Payer {
  key: string;
  name: string;
  group: 'WC / No-Fault' | 'Commercial' | 'Government';
}

const PAYERS: Payer[] = [
  { key: 'workers_comp', name: 'Workers\' Compensation (WC)', group: 'WC / No-Fault' },
  { key: 'no_fault', name: 'No-Fault (PIP)', group: 'WC / No-Fault' },
  { key: 'united_healthcare', name: 'UnitedHealthcare', group: 'Commercial' },
  { key: 'aetna', name: 'Aetna', group: 'Commercial' },
  { key: 'bcbs', name: 'Blue Cross Blue Shield', group: 'Commercial' },
  { key: 'cigna', name: 'Cigna', group: 'Commercial' },
  { key: 'humana', name: 'Humana', group: 'Commercial' },
  { key: 'emblem_health', name: 'EmblemHealth', group: 'Commercial' },
  { key: 'medicare', name: 'Medicare', group: 'Government' },
  { key: 'medicaid_ny', name: 'Medicaid NY', group: 'Government' },
];

const PAYER_GROUPS = ['WC / No-Fault', 'Commercial', 'Government'] as const;

// ---------------------------------------------------------------------------
//  Mock payer criteria data (dev bypass) — representative samples
// ---------------------------------------------------------------------------

interface PayerCriteria {
  policy_number: string;
  policy_name: string;
  criteria: string[];
  required_documentation: string[];
  common_denial_reasons: string[];
  approval_tips: string[];
  avg_decision_days: number;
  appeal_success_rate: number;
}

// Per-procedure, per-payer mock data for dev bypass mode
const MOCK_CRITERIA: Record<string, Record<string, PayerCriteria>> = {
  lumbar_fusion: {
    united_healthcare: {
      policy_number: '2023T0555Y',
      policy_name: 'Spinal Fusion Surgery',
      criteria: [
        'Failed minimum 6 months (26 weeks) conservative treatment including PT, medications, and injections',
        'Documented instability on flexion-extension radiographs (>4 mm translation or >10 deg angular motion)',
        'MRI or CT showing pathology correlating with clinical symptoms and neurological findings',
        'BMI <40 (or documented medical necessity with bariatric evaluation if BMI >=40)',
        'No active tobacco use OR enrollment in cessation program with documented compliance >=6 weeks',
        'Psychological clearance for patients with chronic pain >6 months duration',
        'ODI score >=40 or equivalent validated functional impairment measure',
        'Failed at least 2 epidural steroid injections or selective nerve root blocks',
        'Physical therapy minimum 12 sessions over 6 weeks with documented outcomes per session',
        'Trial of at least 2 classes of analgesics (NSAIDs, neuropathic agents, or muscle relaxants)',
      ],
      required_documentation: [
        'MRI or CT within 6 months of submission',
        'Flexion-extension radiographs if instability is the indication',
        'Physical therapy records showing individual session dates, interventions, and outcomes',
        'Medication history with drug names, dosages, duration, and clinical response',
        'Injection records with dates, agents used, fluoroscopic guidance confirmation, and relief duration',
        'Functional outcome scores (ODI and VAS at minimum)',
        'Operative plan with CPT codes and number of planned levels',
        'History and physical examination within 30 days of submission',
        'Tobacco screening result and cessation documentation if applicable',
        'BMI documented in clinical note',
      ],
      common_denial_reasons: [
        'Insufficient conservative treatment duration -- UHC requires full 6 months, not 3',
        'No validated functional outcome scores (ODI/VAS) documented in the record',
        'BMI >=40 without documented bariatric evaluation or medical necessity justification',
        'Missing injection records or fewer than 2 documented ESI attempts',
        'Active tobacco use without evidence of cessation program enrollment',
      ],
      approval_tips: [
        'UHC weighs functional scores heavily -- always include ODI and VAS with dates',
        'Document tobacco status explicitly even if the patient is a non-smoker',
        'Include BMI in the submission even if it falls in the normal range',
        'Reference InterQual criteria by name in the clinical narrative',
        'If BMI >=40, include a letter from the bariatric or primary care physician',
      ],
      avg_decision_days: 15,
      appeal_success_rate: 45,
    },
    aetna: {
      policy_number: '0508-Spine',
      policy_name: 'Spinal Fusion — Aetna Clinical Policy Bulletin',
      criteria: [
        'Failed minimum 3 months of conservative treatment including PT and medications',
        'MRI demonstrating disc degeneration, instability, or deformity at proposed levels',
        'Documented instability or spondylolisthesis Grade I+',
        'BMI <45 (or documented justification if >=45)',
        'No tobacco use required (preferred, not mandatory)',
        'ODI score >=30',
        'At least 1 epidural or facet injection with documented response',
        'Physical therapy minimum 8 sessions',
        'Trial of NSAIDs or neuropathic agent',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records',
        'Injection records with response',
        'ODI and VAS scores',
        'Medication history',
        'Operative plan with levels and CPT codes',
        'H&P within 30 days',
      ],
      common_denial_reasons: [
        'Conservative treatment less than 3 months',
        'No ODI/VAS functional scores documented',
        'Imaging does not correlate with clinical symptoms',
        'BMI >=45 without justification',
      ],
      approval_tips: [
        'Aetna is more lenient on conservative duration (3 months vs. UHC 6 months)',
        'Reference Aetna CPB number 0508 in the narrative',
        'ODI >=30 is the threshold -- lower than UHC >=40',
        'Tobacco cessation is preferred but not a hard requirement',
      ],
      avg_decision_days: 15,
      appeal_success_rate: 48,
    },
    bcbs: {
      policy_number: 'SUR-7079',
      policy_name: 'Lumbar Spinal Fusion — BCBS Medical Policy',
      criteria: [
        'Failed minimum 3 months of conservative treatment',
        'MRI or CT demonstrating pathology at proposed levels',
        'Documented instability, spondylolisthesis, or DDD',
        'No specific BMI limit (documented comorbidity management recommended)',
        'Tobacco cessation recommended but not required',
        'ODI score >=30 or equivalent',
        'At least 1 injection with documented response',
        'Physical therapy minimum 6 sessions',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records',
        'Injection records',
        'Functional outcome scores',
        'Medication history',
        'Operative plan',
        'H&P within 30 days',
      ],
      common_denial_reasons: [
        'Conservative treatment less than 3 months',
        'No functional scores documented',
        'Imaging not correlating with symptoms',
        'Missing injection records',
      ],
      approval_tips: [
        'BCBS has no hard BMI limit -- but document comorbidity management',
        'Conservative care 3 months -- shorter than UHC',
        'Reference BCBS medical policy SUR-7079',
        'BCBS generally has the highest approval rate for spine fusion among commercial payers',
      ],
      avg_decision_days: 12,
      appeal_success_rate: 50,
    },
    cigna: {
      policy_number: 'IP0076',
      policy_name: 'Spinal Fusion — Cigna Coverage Policy',
      criteria: [
        'Failed minimum 6 months of conservative treatment including PT, medications, and injections',
        'MRI showing pathology at proposed surgical levels',
        'Documented instability or spondylolisthesis',
        'BMI <40 (or documented justification)',
        'No active tobacco use or cessation program enrollment required',
        'ODI score >=40',
        'Failed at least 2 epidural steroid injections',
        'Physical therapy minimum 12 sessions',
        'Psychological clearance for chronic pain >6 months',
        'Trial of at least 2 analgesic classes',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Flexion-extension radiographs',
        'Physical therapy records (12+ sessions)',
        'Medication history',
        'Injection records (2+ ESIs)',
        'ODI and VAS scores',
        'Psychological evaluation if chronic pain >6 months',
        'Operative plan',
        'Tobacco and BMI documentation',
      ],
      common_denial_reasons: [
        'Conservative treatment less than 6 months',
        'Missing functional outcome scores',
        'BMI >=40 without justification',
        'Fewer than 2 ESIs documented',
        'No psychological clearance for chronic pain patients',
      ],
      approval_tips: [
        'Cigna mirrors UHC in strictness -- 6 months conservative care, ODI >=40',
        'EviCore manages prior auth for Cigna -- reference their criteria',
        'Document tobacco status and BMI explicitly',
        'Psychological evaluation is mandatory for chronic pain >6 months',
      ],
      avg_decision_days: 15,
      appeal_success_rate: 42,
    },
    humana: {
      policy_number: 'HUM-SPINE-2023',
      policy_name: 'Lumbar Fusion — Humana Clinical Guidelines',
      criteria: [
        'Failed minimum 3 months of conservative treatment',
        'MRI demonstrating pathology at proposed levels',
        'Documented instability or degenerative condition',
        'BMI <45 or documented justification',
        'ODI score >=30',
        'At least 1 injection with documented response',
        'Physical therapy minimum 8 sessions',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records',
        'Injection records',
        'ODI/VAS scores',
        'Medication history',
        'Operative plan',
      ],
      common_denial_reasons: [
        'Conservative care less than 3 months',
        'No functional scores',
        'Imaging not correlating with symptoms',
      ],
      approval_tips: [
        'Humana is moderately strict -- 3 months conservative, ODI >=30',
        'Document all conservative treatments with dates',
        'Include functional outcome measures',
      ],
      avg_decision_days: 14,
      appeal_success_rate: 46,
    },
    emblem_health: {
      policy_number: 'EH-SPINE-001',
      policy_name: 'Lumbar Fusion — EmblemHealth Policy',
      criteria: [
        'Failed minimum 3 months of conservative treatment',
        'MRI or CT demonstrating structural pathology',
        'Documented instability or spondylolisthesis',
        'ODI score >=30',
        'At least 1 injection with documented response',
        'Physical therapy minimum 6 sessions',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records',
        'Injection records',
        'Functional outcome scores',
        'Operative plan',
        'H&P within 30 days',
      ],
      common_denial_reasons: [
        'Conservative treatment less than 3 months',
        'Missing functional scores',
        'Imaging findings do not support surgery',
      ],
      approval_tips: [
        'EmblemHealth follows criteria similar to Aetna/BCBS',
        'Reference EmblemHealth policy number in submission',
        'ODI >=30 is the threshold',
      ],
      avg_decision_days: 14,
      appeal_success_rate: 47,
    },
    medicare: {
      policy_number: 'LCD-L35075',
      policy_name: 'Lumbar Fusion — Medicare LCD (Novitas/NGS)',
      criteria: [
        'Failed minimum 3 months conservative treatment (PT, medications)',
        'MRI or CT demonstrating structural pathology',
        'Documented instability, spondylolisthesis, or DDD',
        'No specific BMI limit',
        'No tobacco requirement',
        'ODI recommended but not mandatory',
        'At least 1 injection attempt documented',
        'Physical therapy records required',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records',
        'Injection records',
        'Functional assessment',
        'Medication history',
        'Operative plan with CPT codes',
        'H&P within 30 days',
      ],
      common_denial_reasons: [
        'Procedure not meeting LCD criteria',
        'Insufficient documentation of conservative care',
        'Missing imaging correlation',
        'Coding errors',
      ],
      approval_tips: [
        'Medicare uses LCD, not prior auth for most spine -- but some MACs require notification',
        'Reference LCD L35075 (Novitas) or applicable MAC LCD',
        'ABN (Advance Beneficiary Notice) if uncertain coverage',
        'Medicare does not require BMI or tobacco screening for coverage',
      ],
      avg_decision_days: 0,
      appeal_success_rate: 55,
    },
    medicaid_ny: {
      policy_number: 'EMEDNY-SURG-SPINE-001',
      policy_name: 'Lumbar Spinal Fusion -- Prior Authorization Required',
      criteria: [
        'Prior authorization REQUIRED for all spinal fusion under Medicaid NY',
        'Failed minimum 3 months conservative treatment (PT, medications, injections)',
        'MRI or CT demonstrating structural pathology',
        'Documented instability, spondylolisthesis Grade I+, or DDD',
        'Functional outcome score (ODI) documented',
        'At least 1 injection with documented response',
        'Physical therapy minimum 8 sessions',
        'Psychological evaluation recommended for chronic pain >6 months',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'PT records',
        'Injection records with response',
        'ODI score',
        'Medication history',
        'Operative plan',
        'H&P within 30 days',
        'PA request form (eMedNY)',
      ],
      common_denial_reasons: [
        'PA not obtained before surgery -- retroactive PA rarely approved',
        'Conservative treatment less than 3 months',
        'No ODI score in submission',
        'MCO-specific criteria not met',
      ],
      approval_tips: [
        'ALWAYS obtain PA before surgery -- Medicaid rarely approves retroactive PA',
        'Submit PA through eMedNY portal or by phone',
        'If patient is in MCO (Fidelis, Healthfirst), PA goes through MCO not eMedNY',
        'Medicaid NY generally follows BCBS-like criteria with stricter PA enforcement',
      ],
      avg_decision_days: 14,
      appeal_success_rate: 40,
    },
    no_fault: {
      policy_number: 'NFPIP-SPINE-001',
      policy_name: 'Lumbar Spinal Fusion -- No-Fault PIP',
      criteria: [
        'Injury must be causally related to the motor vehicle accident',
        'Treatment within statutory time limits -- initial treatment within 30 days of MVA',
        'Failed minimum 8-12 weeks conservative treatment unless acute instability',
        'MRI or CT demonstrating structural pathology -- distinguish acute traumatic from degenerative',
        'Documented instability on flexion-extension radiographs',
        'Must comply with No-Fault Fee Schedule',
        'NF-3 (Verification of Treatment) form required within 180 days',
        'NF-5 (Hospital Facility Form) required for surgery',
        'IME may be requested by carrier at any time',
        'Medical necessity documented per Regulation 68',
        'ODI score >=30 or equivalent',
        'At least 1 ESI with documented response',
      ],
      required_documentation: [
        'MRI or CT identifying acute vs. degenerative findings',
        'Police report or accident report documenting MVA',
        'Initial ER/urgent care records from date of accident',
        'Physical therapy records with outcomes',
        'Medication and injection history',
        'Functional outcome scores (ODI/VAS)',
        'Operative plan with CPT codes',
        'NF-3 and NF-5 forms',
        'H&P documenting causal relationship to MVA',
      ],
      common_denial_reasons: [
        'IME found claimant at MMI -- no further treatment needed',
        'Treatment not causally related to MVA -- degenerative changes',
        'Pre-existing condition not distinguished from acute injury',
        'NF-3 not submitted within 180 days',
        'Bills not submitted within 45 days of treatment',
        'Fee schedule violation',
      ],
      approval_tips: [
        'Document causal relationship to MVA in EVERY note',
        'Reference date of accident consistently',
        'Distinguish acute traumatic from degenerative findings on MRI',
        'If IME scheduled, prepare detailed rebuttal documentation',
        'No-Fault is generally more permissive initially but carriers aggressively IME',
        'Appeals go to No-Fault arbitration (AAA), not internal payer appeal',
        'Confirm $50,000 PIP limit or SUM coverage before proceeding',
      ],
      avg_decision_days: 30,
      appeal_success_rate: 50,
    },
    workers_comp: {
      policy_number: 'NYS-WCB-MTG-SPINE',
      policy_name: 'Lumbar Fusion -- NYS Workers Comp MTG',
      criteria: [
        'Must follow NYS Workers Compensation Medical Treatment Guidelines (MTG)',
        'Documented work-related injury with WCB case number',
        'Failed minimum 3 months conservative treatment per MTG',
        'MRI demonstrating structural pathology at proposed levels',
        'Documented instability or spondylolisthesis',
        'ODI or equivalent functional score documented',
        'At least 1 injection with documented response',
        'RFA-2 (Request for Authorization) form required',
        'C-4 Auth form submission to WCB',
      ],
      required_documentation: [
        'MRI or CT within 6 months',
        'Physical therapy records per MTG requirements',
        'Injection records with response',
        'Functional outcome scores',
        'RFA-2 form',
        'C-4 Auth form',
        'Operative plan with CPT codes',
      ],
      common_denial_reasons: [
        'Treatment not consistent with MTG guidelines',
        'Insufficient conservative care per MTG timeline',
        'Missing required WCB forms',
        'IME found claimant at MMI',
        'Pre-existing condition not distinguished from work injury',
      ],
      approval_tips: [
        'Follow MTG guidelines precisely -- WCB denials reference specific MTG sections',
        'Submit RFA-2 and C-4 Auth forms correctly',
        'Document work-relatedness in every clinical note',
        'If denied, request WCB hearing -- do not use carrier internal appeal',
      ],
      avg_decision_days: 30,
      appeal_success_rate: 52,
    },
  },
};

// Comparison data for lumbar fusion across the "big four" commercial payers
const COMPARISON_FIELDS: { label: string; key: string }[] = [
  { label: 'Conservative Tx', key: 'conservative' },
  { label: 'BMI Limit', key: 'bmi' },
  { label: 'Tobacco', key: 'tobacco' },
  { label: 'ODI Required', key: 'odi' },
  { label: '# ESIs', key: 'esis' },
  { label: 'Psych Eval', key: 'psych' },
  { label: 'Decision Time', key: 'decision' },
  { label: 'Appeal Rate', key: 'appeal' },
];

type Severity = 'easy' | 'moderate' | 'strict';

interface ComparisonCell {
  text: string;
  severity: Severity;
}

const MOCK_COMPARISON: Record<string, Record<string, ComparisonCell>> = {
  united_healthcare: {
    conservative: { text: '6 months', severity: 'strict' },
    bmi: { text: '<40', severity: 'moderate' },
    tobacco: { text: 'Required', severity: 'strict' },
    odi: { text: '>=40', severity: 'strict' },
    esis: { text: '>=2', severity: 'strict' },
    psych: { text: 'Required', severity: 'strict' },
    decision: { text: '15 days', severity: 'moderate' },
    appeal: { text: '45%', severity: 'moderate' },
  },
  aetna: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: '<45', severity: 'easy' },
    tobacco: { text: 'Optional', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '15 days', severity: 'moderate' },
    appeal: { text: '48%', severity: 'moderate' },
  },
  bcbs: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'Optional', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '12 days', severity: 'easy' },
    appeal: { text: '50%', severity: 'easy' },
  },
  cigna: {
    conservative: { text: '6 months', severity: 'strict' },
    bmi: { text: '<40', severity: 'moderate' },
    tobacco: { text: 'Required', severity: 'strict' },
    odi: { text: '>=40', severity: 'strict' },
    esis: { text: '>=2', severity: 'strict' },
    psych: { text: 'Required', severity: 'strict' },
    decision: { text: '15 days', severity: 'moderate' },
    appeal: { text: '42%', severity: 'strict' },
  },
  humana: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: '<45', severity: 'easy' },
    tobacco: { text: 'Optional', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '14 days', severity: 'moderate' },
    appeal: { text: '46%', severity: 'moderate' },
  },
  emblem_health: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'Optional', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '14 days', severity: 'moderate' },
    appeal: { text: '47%', severity: 'moderate' },
  },
  medicare: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'None', severity: 'easy' },
    odi: { text: 'Optional', severity: 'easy' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: 'N/A', severity: 'easy' },
    appeal: { text: '55%', severity: 'easy' },
  },
  medicaid_ny: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'None', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Recommended', severity: 'easy' },
    decision: { text: '14 days', severity: 'moderate' },
    appeal: { text: '40%', severity: 'strict' },
  },
  no_fault: {
    conservative: { text: '8-12 wks', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'None', severity: 'easy' },
    odi: { text: '>=30', severity: 'moderate' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '30 days', severity: 'strict' },
    appeal: { text: '50%', severity: 'moderate' },
  },
  workers_comp: {
    conservative: { text: '3 months', severity: 'moderate' },
    bmi: { text: 'None', severity: 'easy' },
    tobacco: { text: 'None', severity: 'easy' },
    odi: { text: 'Recommended', severity: 'easy' },
    esis: { text: '>=1', severity: 'easy' },
    psych: { text: 'Optional', severity: 'easy' },
    decision: { text: '30 days', severity: 'strict' },
    appeal: { text: '52%', severity: 'moderate' },
  },
};

// ---------------------------------------------------------------------------
//  Helpers
// ---------------------------------------------------------------------------

function severityColor(s: Severity): string {
  switch (s) {
    case 'easy': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'moderate': return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'strict': return 'bg-red-50 text-red-700 border-red-200';
  }
}

function severityDot(s: Severity): string {
  switch (s) {
    case 'easy': return 'bg-emerald-400';
    case 'moderate': return 'bg-amber-400';
    case 'strict': return 'bg-red-400';
  }
}

function getCriteria(procedureKey: string, payerKey: string): PayerCriteria | null {
  return MOCK_CRITERIA[procedureKey]?.[payerKey] ?? null;
}

// ---------------------------------------------------------------------------
//  Component
// ---------------------------------------------------------------------------

export default function ProcedureLookup() {
  const navigate = useNavigate();

  // State
  const [procedureSearch, setProcedureSearch] = useState('');
  const [selectedProcedure, setSelectedProcedure] = useState<Procedure | null>(null);
  const [selectedPayer, setSelectedPayer] = useState('');
  const [showProcedureDropdown, setShowProcedureDropdown] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const procDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (procDropdownRef.current && !procDropdownRef.current.contains(e.target as Node)) {
        setShowProcedureDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Filtered procedures
  const filteredProcedures = useMemo(() => {
    const q = procedureSearch.toLowerCase().trim();
    if (!q) return PROCEDURES;
    return PROCEDURES.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.cpts.some((c) => c.includes(q)) ||
        p.category.toLowerCase().includes(q) ||
        p.key.replace(/_/g, ' ').includes(q)
    );
  }, [procedureSearch]);

  // Group procedures by category for display
  const groupedProcedures = useMemo(() => {
    const groups: Record<string, Procedure[]> = {};
    for (const p of filteredProcedures) {
      if (!groups[p.category]) groups[p.category] = [];
      groups[p.category].push(p);
    }
    return groups;
  }, [filteredProcedures]);

  // Current criteria
  const criteria = selectedProcedure && selectedPayer ? getCriteria(selectedProcedure.key, selectedPayer) : null;
  const payerObj = PAYERS.find((p) => p.key === selectedPayer);

  // Handlers
  const handleSelectProcedure = (proc: Procedure) => {
    setSelectedProcedure(proc);
    setProcedureSearch('');
    setShowProcedureDropdown(false);
    setShowComparison(false);
  };

  const handleStartPriorAuth = () => {
    const params = new URLSearchParams();
    if (selectedProcedure) {
      params.set('procedure', selectedProcedure.key);
      params.set('cpt', selectedProcedure.cpts[0]);
    }
    if (selectedPayer) params.set('payer', selectedPayer);
    navigate(`/prior-auth/new?${params.toString()}`);
  };

  // Comparison payer keys (exclude currently selected to show comparison WITH it)
  const comparisonPayers = PAYERS.filter((p) => MOCK_COMPARISON[p.key]);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#0F2044]">Procedure & Payer Lookup</h1>
        <p className="text-sm text-gray-500 mt-1">
          Search for a procedure and payer to view approval criteria, required documentation, denial reasons, and tips
        </p>
      </div>

      {/* Search Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Procedure Search */}
        <div ref={procDropdownRef} className="relative">
          <label className="block text-xs font-semibold text-[#0F2044] mb-1.5 uppercase tracking-wide">
            Procedure
          </label>
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={selectedProcedure ? `${selectedProcedure.name} (${selectedProcedure.cpts.join(', ')})` : procedureSearch}
              onChange={(e) => {
                if (selectedProcedure) {
                  setSelectedProcedure(null);
                  setShowComparison(false);
                }
                setProcedureSearch(e.target.value);
                setShowProcedureDropdown(true);
              }}
              onFocus={() => { if (!selectedProcedure) setShowProcedureDropdown(true); }}
              placeholder="Search by procedure name or CPT code..."
              className="w-full pl-9 pr-8 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2044]/30 focus:border-[#0F2044]"
            />
            {selectedProcedure && (
              <button
                onClick={() => { setSelectedProcedure(null); setProcedureSearch(''); setShowComparison(false); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Procedure Dropdown */}
          {showProcedureDropdown && !selectedProcedure && (
            <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
              {Object.keys(groupedProcedures).length === 0 ? (
                <div className="px-4 py-3 text-sm text-gray-400">No matching procedures</div>
              ) : (
                Object.entries(groupedProcedures).map(([category, procs]) => (
                  <div key={category}>
                    <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 bg-gray-50 border-b border-gray-100 sticky top-0">
                      {category}
                    </div>
                    {procs.map((proc) => (
                      <button
                        key={proc.key}
                        onClick={() => handleSelectProcedure(proc)}
                        className="w-full text-left px-4 py-2.5 hover:bg-[#0F2044]/5 transition-colors border-b border-gray-50 last:border-0"
                      >
                        <div className="text-sm font-medium text-[#0F2044]">{proc.name}</div>
                        <div className="text-xs text-gray-400 mt-0.5">CPT: {proc.cpts.join(', ')}</div>
                      </button>
                    ))}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Payer Dropdown */}
        <div>
          <label className="block text-xs font-semibold text-[#0F2044] mb-1.5 uppercase tracking-wide">
            Insurance Payer
          </label>
          <select
            value={selectedPayer}
            onChange={(e) => { setSelectedPayer(e.target.value); setShowComparison(false); }}
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2044]/30 focus:border-[#0F2044] bg-white"
          >
            <option value="">Select payer...</option>
            {PAYER_GROUPS.map((group) => (
              <optgroup key={group} label={group}>
                {PAYERS.filter((p) => p.group === group).map((p) => (
                  <option key={p.key} value={p.key}>{p.name}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      {/* No selection state */}
      {(!selectedProcedure || !selectedPayer) && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#0F2044]/5 flex items-center justify-center">
            <svg className="w-8 h-8 text-[#0F2044]/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-lg font-semibold text-gray-600">Select a Procedure and Payer</p>
          <p className="text-sm text-gray-400 mt-2">
            Choose a procedure and insurance payer above to view detailed approval criteria, documentation requirements, and denial patterns.
          </p>
        </div>
      )}

      {/* Criteria Card */}
      {selectedProcedure && selectedPayer && !showComparison && (
        <div className="space-y-6">
          {/* Main Card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {/* Card Header */}
            <div className="bg-[#0F2044] px-6 py-5">
              <h2 className="text-lg font-bold text-white">{selectedProcedure.name}</h2>
              <div className="flex items-center gap-3 mt-1.5">
                <span className="text-xs text-gray-300">
                  CPT: {selectedProcedure.cpts.join(', ')}
                </span>
                <span className="text-gray-500">|</span>
                <span className="text-xs text-gray-300">
                  Payer: {payerObj?.name ?? selectedPayer}
                </span>
              </div>
            </div>

            {criteria ? (
              <div className="p-6 space-y-6">
                {/* Metrics Row */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0F2044]/5 rounded-lg p-4 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Avg Decision Time</div>
                    <div className="text-2xl font-bold text-[#0F2044]">
                      {criteria.avg_decision_days === 0 ? 'N/A' : `${criteria.avg_decision_days} days`}
                    </div>
                  </div>
                  <div className="bg-[#0F2044]/5 rounded-lg p-4 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Appeal Success Rate</div>
                    <div className="text-2xl font-bold text-[#0F2044]">{criteria.appeal_success_rate}%</div>
                  </div>
                </div>

                {/* Requirements */}
                <div>
                  <h3 className="text-sm font-bold text-[#0F2044] uppercase tracking-wide mb-3">Requirements for Approval</h3>
                  <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
                    <ul className="space-y-2">
                      {criteria.criteria.map((c, i) => (
                        <li key={i} className="flex items-start gap-2.5 text-sm text-gray-700">
                          <span className="mt-0.5 w-4 h-4 rounded border-2 border-gray-300 flex-shrink-0" />
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Required Documentation */}
                <div>
                  <h3 className="text-sm font-bold text-[#0F2044] uppercase tracking-wide mb-3">Required Documentation</h3>
                  <ul className="space-y-1.5">
                    {criteria.required_documentation.map((d, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="text-[#0F2044]/40 mt-1 flex-shrink-0">&#8226;</span>
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Denial Reasons */}
                <div>
                  <h3 className="text-sm font-bold text-amber-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    Common Denial Reasons
                  </h3>
                  <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
                    <ul className="space-y-1.5">
                      {criteria.common_denial_reasons.map((r, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-amber-800">
                          <span className="mt-1 flex-shrink-0">&#8226;</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Approval Tips */}
                <div>
                  <h3 className="text-sm font-bold text-emerald-700 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Approval Tips
                  </h3>
                  <div className="bg-emerald-50 rounded-lg border border-emerald-200 p-4">
                    <ul className="space-y-1.5">
                      {criteria.approval_tips.map((t, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-emerald-800">
                          <span className="mt-1 flex-shrink-0">&#8226;</span>
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowComparison(true)}
                    className="flex-1 px-4 py-2.5 bg-white border-2 border-[#0F2044] text-[#0F2044] rounded-lg text-sm font-semibold hover:bg-[#0F2044]/5 transition-colors"
                  >
                    Compare Across Payers
                  </button>
                  <button
                    onClick={handleStartPriorAuth}
                    className="flex-1 px-4 py-2.5 bg-[#0F2044] text-white rounded-lg text-sm font-semibold hover:bg-[#0F2044]/90 transition-colors"
                  >
                    Start Prior Auth
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6">
                <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
                  <p className="text-sm text-gray-500">
                    Detailed criteria data for <strong>{selectedProcedure.name}</strong> with{' '}
                    <strong>{payerObj?.name ?? selectedPayer}</strong> is not yet available in the mock dataset.
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Lumbar Fusion has full mock data for all payers. Try selecting that procedure, or connect to the backend API for complete data.
                  </p>
                  <div className="flex gap-3 justify-center mt-4">
                    <button
                      onClick={() => setShowComparison(true)}
                      className="px-4 py-2 bg-white border-2 border-[#0F2044] text-[#0F2044] rounded-lg text-sm font-semibold hover:bg-[#0F2044]/5 transition-colors"
                    >
                      Compare Across Payers
                    </button>
                    <button
                      onClick={handleStartPriorAuth}
                      className="px-4 py-2 bg-[#0F2044] text-white rounded-lg text-sm font-semibold hover:bg-[#0F2044]/90 transition-colors"
                    >
                      Start Prior Auth
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Comparison View */}
      {selectedProcedure && selectedPayer && showComparison && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[#0F2044]">
              Payer Comparison: {selectedProcedure.name}
            </h2>
            <button
              onClick={() => setShowComparison(false)}
              className="text-sm text-[#0F2044] font-medium hover:underline flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Details
            </button>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${severityDot('easy')}`} />
              Favorable
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${severityDot('moderate')}`} />
              Moderate
            </span>
            <span className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${severityDot('strict')}`} />
              Strict
            </span>
          </div>

          {/* Comparison Table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#0F2044] text-white">
                    <th className="text-left px-4 py-3 font-semibold text-xs uppercase tracking-wide sticky left-0 bg-[#0F2044] z-10 min-w-[130px]">
                      Criteria
                    </th>
                    {comparisonPayers.map((p) => (
                      <th
                        key={p.key}
                        className={`text-center px-3 py-3 font-semibold text-xs uppercase tracking-wide min-w-[100px] ${
                          p.key === selectedPayer ? 'bg-[#1a3a6e]' : ''
                        }`}
                      >
                        {p.name.replace('UnitedHealthcare', 'UHC').replace('Blue Cross Blue Shield', 'BCBS').replace('EmblemHealth', 'Emblem').replace("Workers' Compensation (WC)", 'WC').replace('No-Fault (PIP)', 'No-Fault').replace('Medicaid NY', 'Medicaid')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON_FIELDS.map((field, idx) => (
                    <tr key={field.key} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className={`px-4 py-3 font-medium text-[#0F2044] sticky left-0 z-10 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                        {field.label}
                      </td>
                      {comparisonPayers.map((p) => {
                        const cell = MOCK_COMPARISON[p.key]?.[field.key];
                        if (!cell) {
                          return (
                            <td key={p.key} className="text-center px-3 py-3 text-gray-300">--</td>
                          );
                        }
                        return (
                          <td key={p.key} className={`text-center px-3 py-3 ${p.key === selectedPayer ? 'bg-[#0F2044]/5' : ''}`}>
                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${severityColor(cell.severity)}`}>
                              {cell.text}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => setShowComparison(false)}
              className="flex-1 px-4 py-2.5 bg-white border-2 border-[#0F2044] text-[#0F2044] rounded-lg text-sm font-semibold hover:bg-[#0F2044]/5 transition-colors"
            >
              Back to {payerObj?.name ?? 'Payer'} Details
            </button>
            <button
              onClick={handleStartPriorAuth}
              className="flex-1 px-4 py-2.5 bg-[#0F2044] text-white rounded-lg text-sm font-semibold hover:bg-[#0F2044]/90 transition-colors"
            >
              Start Prior Auth
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
