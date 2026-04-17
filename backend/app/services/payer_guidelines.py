"""
Commercial & Government Payer Prior Authorization Guidelines — Knowledge Base.

Comprehensive prior authorization criteria for 8 major insurance payers, covering
14 orthopedic/neurosurgery/concussion procedures.  Each procedure-payer combination
includes policy numbers, clinical criteria, required documentation, common denial
reasons, approval tips, and performance metrics.

This module complements mtg_guidelines.py (NYS WCB MTG) and is consumed by
compliance_checker.py and narrative_service.py to evaluate PA requests against
payer-specific standards.

Payers:  UnitedHealthcare · Aetna · BCBS · Cigna · Humana · EmblemHealth
         Medicare (Novitas/NGS for NY) · Medicaid NY (eMedNY)

Procedures (14):
  Spine/Neurosurgery — lumbar_fusion, lumbar_decompression, cervical_fusion_acdf,
                       cervical_decompression, spinal_cord_stimulator,
                       epidural_steroid_injection
  Orthopedic         — total_knee_replacement, total_hip_replacement,
                       acl_reconstruction, rotator_cuff_repair,
                       carpal_tunnel_release, shoulder_arthroscopy
  Concussion/TBI     — neuropsychological_testing, cognitive_rehabilitation
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

# ---------------------------------------------------------------------------
#  PAYER AUTH GUIDELINES  —  8 payers × 14 procedures = 112 combinations
# ---------------------------------------------------------------------------

PAYER_AUTH_GUIDELINES: dict[str, dict[str, Any]] = {

    # ======================================================================
    #  1. UNITEDH EALTHCARE (UHC)
    # ======================================================================
    "united_healthcare": {
        "name": "UnitedHealthcare (UHC)",
        "type": "commercial",
        "source": "UHC Medical Policies & InterQual Criteria",
        "pa_portal": "UHCProvider.com — Prior Authorization and Notification",
        "phone": "1-877-842-3210",
        "avg_p2p_wait_days": 5,
        "procedures": {

            # ----------------------------------------------------------
            # SPINE / NEUROSURGERY
            # ----------------------------------------------------------

            "lumbar_fusion": {
                "policy_number": "2023T0555Y",
                "policy_name": "Spinal Fusion Surgery",
                "criteria": [
                    "Failed minimum 6 months (26 weeks) conservative treatment including PT, medications, and injections",
                    "Documented instability on flexion-extension radiographs (>4 mm translation or >10° angular motion)",
                    "MRI or CT showing pathology correlating with clinical symptoms and neurological findings",
                    "BMI <40 (or documented medical necessity with bariatric evaluation if BMI ≥40)",
                    "No active tobacco use OR enrollment in cessation program with documented compliance ≥6 weeks",
                    "Psychological clearance for patients with chronic pain >6 months duration",
                    "ODI score ≥40 or equivalent validated functional impairment measure",
                    "Failed at least 2 epidural steroid injections or selective nerve root blocks",
                    "Physical therapy minimum 12 sessions over 6 weeks with documented outcomes per session",
                    "Trial of at least 2 classes of analgesics (NSAIDs, neuropathic agents, or muscle relaxants)",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months of submission",
                    "Flexion-extension radiographs if instability is the indication",
                    "Physical therapy records showing individual session dates, interventions, and outcomes",
                    "Medication history with drug names, dosages, duration, and clinical response",
                    "Injection records with dates, agents used, fluoroscopic guidance confirmation, and relief duration",
                    "Functional outcome scores (ODI and VAS at minimum)",
                    "Operative plan with CPT codes and number of planned levels",
                    "History and physical examination within 30 days of submission",
                    "Tobacco screening result and cessation documentation if applicable",
                    "BMI documented in clinical note",
                ],
                "common_denial_reasons": [
                    "Insufficient conservative treatment duration — UHC requires full 6 months, not 3",
                    "No validated functional outcome scores (ODI/VAS) documented in the record",
                    "BMI ≥40 without documented bariatric evaluation or medical necessity justification",
                    "Missing injection records or fewer than 2 documented ESI attempts",
                    "Active tobacco use without evidence of cessation program enrollment",
                ],
                "approval_tips": [
                    "UHC weighs functional scores heavily — always include ODI and VAS with dates",
                    "Document tobacco status explicitly even if the patient is a non-smoker",
                    "Include BMI in the submission even if it falls in the normal range",
                    "Reference InterQual criteria by name in the clinical narrative",
                    "If BMI ≥40, include a letter from the bariatric or primary care physician explaining why surgery is still appropriate",
                ],
                "avg_decision_days": 15,
                "appeal_success_rate": 45,
            },

            "lumbar_decompression": {
                "policy_number": "2023T0556X",
                "policy_name": "Lumbar Decompression (Laminectomy/Discectomy)",
                "criteria": [
                    "Failed minimum 6 weeks of conservative treatment including physical therapy and medications",
                    "MRI or CT demonstrating neural compression correlating with radicular symptoms",
                    "Progressive neurological deficit (motor weakness, reflex changes, bowel/bladder dysfunction) may bypass conservative care requirement",
                    "Positive straight leg raise test or femoral nerve stretch test documented in exam",
                    "EMG/NCS confirming radiculopathy when clinical presentation is equivocal",
                    "No prior decompression at the same level within 12 months unless documented recurrence",
                    "Pain distribution consistent with dermatomal pattern matching imaging findings",
                ],
                "required_documentation": [
                    "MRI within 6 months demonstrating disc herniation or spinal stenosis",
                    "Physical therapy records (minimum 6 sessions)",
                    "Neurological examination documenting sensory, motor, and reflex findings",
                    "Medication trial records including NSAIDs and/or neuropathic agents",
                    "EMG/NCS if radiculopathy is clinically uncertain",
                    "Operative plan with specific levels and CPT codes",
                ],
                "common_denial_reasons": [
                    "Imaging findings do not correlate with clinical symptoms or dermatomal pattern",
                    "Insufficient conservative treatment documented — need full 6 weeks",
                    "No neurological examination findings documented in the submitted records",
                    "Prior decompression at same level without documented recurrence evidence",
                ],
                "approval_tips": [
                    "Clearly map the dermatomal pattern to the imaging finding in the narrative",
                    "Cauda equina syndrome or progressive motor deficit should be flagged as urgent",
                    "Include VAS leg score separately from VAS back score",
                    "Reference InterQual for Lumbar Disc Surgery specifically",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "cervical_fusion_acdf": {
                "policy_number": "2023T0557Z",
                "policy_name": "Anterior Cervical Discectomy and Fusion (ACDF)",
                "criteria": [
                    "Failed minimum 6 weeks of conservative treatment including PT, medications, and/or cervical traction",
                    "MRI demonstrating cervical disc herniation or spondylotic stenosis with cord or root compression",
                    "Radiculopathy with dermatomal correlation to imaging findings",
                    "Myelopathy signs (Hoffmann sign, hyperreflexia, gait instability) may bypass conservative care",
                    "ODI-Neck or NDI score ≥30 or equivalent functional impairment",
                    "BMI <40 or documented justification if BMI ≥40",
                    "No active tobacco use or documented cessation program enrollment",
                    "Maximum 3 levels for ACDF — 4+ levels requires additional justification",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination with upper and lower extremity findings",
                    "NDI or ODI-Neck score",
                    "Physical therapy records if applicable",
                    "Medication history including trial of NSAIDs and neuropathic agents",
                    "Operative plan specifying levels and approach",
                    "Tobacco and BMI documentation",
                ],
                "common_denial_reasons": [
                    "NDI or equivalent functional score not included",
                    "Conservative care not adequately documented for 6 weeks",
                    "Multi-level (≥4) ACDF without sufficient clinical justification",
                    "Imaging does not show clear cord or root compression at proposed levels",
                ],
                "approval_tips": [
                    "For myelopathy, document Hoffmann sign, Babinski, clonus, and gait disturbance explicitly",
                    "Always include NDI score — UHC uses this as a primary decision point for cervical procedures",
                    "If multi-level, provide level-by-level justification with imaging correlation",
                    "Mention MRI signal changes within the cord (myelomalacia) if present",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 50,
            },

            "cervical_decompression": {
                "policy_number": "2023T0558A",
                "policy_name": "Cervical Decompression (Laminectomy/Foraminotomy)",
                "criteria": [
                    "Failed minimum 6 weeks of conservative care unless myelopathy is present",
                    "MRI or CT demonstrating cervical stenosis or foraminal narrowing with neural compression",
                    "Clinical symptoms correlating with imaging findings (radiculopathy or myelopathy)",
                    "Neurological examination documenting upper extremity weakness, sensory changes, or reflex abnormalities",
                    "For posterior approach: multilevel stenosis or ossified posterior longitudinal ligament (OPLL)",
                    "NDI score ≥30 or equivalent functional impairment",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Detailed neurological examination",
                    "NDI score",
                    "Conservative treatment records including PT and medications",
                    "CT if bony pathology (OPLL, facet hypertrophy) is the primary indication",
                    "Operative plan with levels and approach",
                ],
                "common_denial_reasons": [
                    "No NDI score documented",
                    "Imaging does not demonstrate significant neural compression",
                    "Insufficient conservative treatment without documented myelopathy",
                    "Lack of neurological examination findings in submitted records",
                ],
                "approval_tips": [
                    "If myelopathy is present, clearly state it bypasses conservative care requirements",
                    "Document hand clumsiness, gait instability, and fine motor deficits in detail",
                    "CT scan is helpful to supplement MRI when bony pathology drives the indication",
                    "Reference InterQual Cervical Spine criteria in the narrative",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 52,
            },

            "spinal_cord_stimulator": {
                "policy_number": "2023T0610R",
                "policy_name": "Spinal Cord Stimulation (Neuromodulation)",
                "criteria": [
                    "Failed minimum 6 months of conservative treatment including PT, medications, and injections",
                    "Diagnosis of failed back surgery syndrome (FBSS), complex regional pain syndrome (CRPS), or chronic intractable neuropathic pain",
                    "Successful SCS trial of ≥5 days with ≥50% pain relief documented on VAS",
                    "Psychological evaluation by licensed psychologist clearing patient for implant",
                    "No active substance abuse — negative urine drug screen within 30 days",
                    "No untreated major psychiatric disorder that would impair candidacy",
                    "Failed or is not a candidate for repeat surgical intervention",
                    "BMI <40 or documented medical justification if ≥40",
                    "No active tobacco use or documented cessation program enrollment",
                ],
                "required_documentation": [
                    "SCS trial report with daily VAS scores and percentage relief",
                    "Psychological evaluation report",
                    "Urine drug screen results within 30 days",
                    "Comprehensive pain management history",
                    "MRI demonstrating post-surgical changes or underlying pathology",
                    "Physical therapy records showing 6+ months of treatment",
                    "Medication management records including opioid history",
                    "Functional outcome measures (ODI, VAS, PCS)",
                ],
                "common_denial_reasons": [
                    "SCS trial did not demonstrate ≥50% pain reduction",
                    "Missing or incomplete psychological evaluation",
                    "Positive urine drug screen or substance abuse history without documentation of remission",
                    "Insufficient conservative treatment duration (less than 6 months)",
                    "No functional outcome measures included in submission",
                ],
                "approval_tips": [
                    "Include detailed trial data — daily VAS, activity logs, and patient satisfaction ratings",
                    "Psychological evaluation must be recent (within 6 months) and explicitly recommend implant",
                    "Document all prior surgical interventions and why further surgery is not indicated",
                    "UHC often requests peer-to-peer for SCS — prepare surgeon to discuss trial results",
                    "Include pain catastrophizing scale (PCS) in addition to ODI/VAS",
                ],
                "avg_decision_days": 20,
                "appeal_success_rate": 35,
            },

            "epidural_steroid_injection": {
                "policy_number": "2023T0520M",
                "policy_name": "Epidural Steroid Injections (Therapeutic)",
                "criteria": [
                    "Radicular pain correlating with imaging findings (MRI or CT)",
                    "Failed minimum 2 weeks of conservative treatment (oral medications and/or PT)",
                    "Maximum 3 injections per spinal region per 12-month period",
                    "Minimum 2-week interval between injections",
                    "Fluoroscopic or CT guidance required for all injections",
                    "Must document response to prior injection before authorizing subsequent injection",
                    "No prior injection at same level within 2 weeks",
                ],
                "required_documentation": [
                    "MRI or CT demonstrating pathology at the target level",
                    "Pain diagram or description of radicular distribution",
                    "Trial of oral medications (NSAIDs, neuropathic agents)",
                    "Prior injection response records if requesting 2nd or 3rd injection",
                    "VAS score before and after each prior injection",
                    "Planned approach (interlaminar vs. transforaminal) and level",
                ],
                "common_denial_reasons": [
                    "Exceeded 3 injections per region per 12 months",
                    "No documented response to prior injection before requesting another",
                    "Imaging does not show pathology at the proposed level",
                    "Non-fluoroscopic (blind) injection technique proposed",
                ],
                "approval_tips": [
                    "Always document the response to each prior ESI with VAS change and duration",
                    "Specify transforaminal vs. interlaminar approach — UHC prefers documentation of the rationale",
                    "If requesting a 3rd injection, explicitly state the functional benefit from the first two",
                    "Include the date of last injection and interval in the narrative",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 65,
            },

            # ----------------------------------------------------------
            # ORTHOPEDIC
            # ----------------------------------------------------------

            "total_knee_replacement": {
                "policy_number": "2023T0700K",
                "policy_name": "Total Knee Arthroplasty (TKA)",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment including PT, medications, and injections",
                    "Radiographic evidence of moderate-to-severe osteoarthritis (Kellgren-Lawrence Grade III or IV)",
                    "Weight-bearing radiographs demonstrating joint space narrowing",
                    "BMI <40 (or documented bariatric evaluation and justification if ≥40)",
                    "No active tobacco use or documented cessation program enrollment",
                    "Functional impairment documented with KOOS or WOMAC scores",
                    "Failed trial of viscosupplementation or corticosteroid injection",
                    "HbA1c <8.0 for diabetic patients",
                    "Preoperative medical clearance for patients with significant comorbidities",
                ],
                "required_documentation": [
                    "Weight-bearing AP, lateral, and sunrise knee radiographs within 6 months",
                    "KOOS or WOMAC functional outcome scores",
                    "Physical therapy records (minimum 6 sessions)",
                    "Medication history (NSAIDs, topical agents, acetaminophen)",
                    "Injection records (corticosteroid and/or viscosupplementation) with response",
                    "BMI and tobacco status documentation",
                    "HbA1c if diabetic (within 3 months)",
                    "Medical clearance if significant cardiac or pulmonary comorbidities",
                ],
                "common_denial_reasons": [
                    "Non-weight-bearing radiographs or Kellgren-Lawrence Grade I–II",
                    "BMI ≥40 without bariatric evaluation",
                    "No functional outcome scores documented",
                    "HbA1c ≥8.0 without documented optimization plan",
                    "Insufficient conservative care — less than 3 months",
                ],
                "approval_tips": [
                    "Weight-bearing radiographs are non-negotiable — UHC will deny on non-WB films alone",
                    "Include KOOS or WOMAC with every submission — UHC tracks these for quality metrics",
                    "If BMI ≥40, include documentation from bariatric surgery evaluation or detailed justification",
                    "Document HbA1c even for non-diabetic patients to preempt questions",
                    "Reference InterQual Total Joint criteria in the narrative",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "total_hip_replacement": {
                "policy_number": "2023T0701H",
                "policy_name": "Total Hip Arthroplasty (THA)",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment including PT, medications, and activity modification",
                    "Radiographic evidence of moderate-to-severe hip osteoarthritis (Kellgren-Lawrence Grade III or IV)",
                    "AP pelvis and lateral hip radiographs demonstrating joint space narrowing or AVN",
                    "BMI <40 or documented justification if ≥40",
                    "No active tobacco use or documented cessation program",
                    "Functional impairment documented with HOOS or Harris Hip Score",
                    "Failed trial of corticosteroid injection or documented contraindication",
                    "HbA1c <8.0 for diabetic patients",
                ],
                "required_documentation": [
                    "AP pelvis and frog-leg lateral hip radiographs within 6 months",
                    "HOOS or Harris Hip Score",
                    "Physical therapy records",
                    "Medication history including NSAIDs",
                    "Injection records with response documentation",
                    "BMI and tobacco status",
                    "HbA1c if diabetic",
                    "Templating or operative plan with approach (anterior vs. posterior)",
                ],
                "common_denial_reasons": [
                    "Kellgren-Lawrence Grade I–II on radiographs",
                    "No functional outcome score documented",
                    "BMI ≥40 without justification",
                    "No injection trial or documented contraindication to injection",
                ],
                "approval_tips": [
                    "Include AP pelvis (both hips) for comparison — UHC reviewers compare sides",
                    "Harris Hip Score <60 strengthens the case significantly",
                    "For AVN, include MRI showing staging and progression",
                    "Document night pain, rest pain, and walking distance limitations explicitly",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 58,
            },

            "acl_reconstruction": {
                "policy_number": "2023T0720A",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "MRI-confirmed complete ACL tear or clinical examination demonstrating Grade III laxity",
                    "Functional instability with giving way episodes documented",
                    "Age and activity level supporting surgical intervention",
                    "Failed trial of conservative treatment (bracing, PT, activity modification) for minimum 4 weeks if not competitive athlete",
                    "No untreated concurrent ligamentous injuries requiring staged approach without documentation",
                    "Pre-rehabilitation PT completed (minimum 4 sessions) to restore range of motion",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear within 6 months",
                    "Physical examination with Lachman test, anterior drawer, and pivot shift results",
                    "Activity level and functional demands description",
                    "Physical therapy records including pre-habilitation",
                    "Documentation of instability episodes (giving way events)",
                    "Graft choice rationale (autograft vs. allograft)",
                ],
                "common_denial_reasons": [
                    "MRI shows partial tear without documented instability",
                    "No documentation of functional instability or giving way episodes",
                    "Insufficient pre-habilitation PT documentation",
                    "No physical examination findings (Lachman/pivot shift) documented",
                ],
                "approval_tips": [
                    "Document specific giving way episodes with dates and circumstances",
                    "Include KT-1000 arthrometer results if available — objective instability data strengthens the case",
                    "For patients >40, include detailed activity demands and functional goals",
                    "Pre-hab PT documentation showing restored ROM improves approval rates with UHC",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 60,
            },

            "rotator_cuff_repair": {
                "policy_number": "2023T0730R",
                "policy_name": "Rotator Cuff Repair (Arthroscopic or Open)",
                "criteria": [
                    "MRI demonstrating full-thickness rotator cuff tear or high-grade partial tear (>50%)",
                    "Failed minimum 6 weeks of conservative treatment (PT, NSAIDs, subacromial injection)",
                    "Acute traumatic tear in active patient may bypass conservative care requirement",
                    "Functional impairment documented with ASES score or Simple Shoulder Test",
                    "Subacromial injection with documented temporary relief supports surgical indication",
                    "No irreparable tear with fatty infiltration Goutallier Grade 3–4 (relative contraindication)",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months showing tear size and location",
                    "ASES score or Simple Shoulder Test",
                    "Physical therapy records (minimum 6 weeks)",
                    "Injection records (subacromial corticosteroid) with response",
                    "Physical examination documenting strength testing and provocative tests",
                    "Operative plan specifying repair technique and any concurrent procedures",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% thickness without documented failure of conservative care",
                    "No functional outcome score (ASES/SST) included",
                    "Insufficient conservative treatment duration (less than 6 weeks)",
                    "MRI showing Goutallier Grade 3–4 fatty infiltration suggesting irreparable tear",
                ],
                "approval_tips": [
                    "For acute traumatic tears, clearly document mechanism of injury and date of onset",
                    "Include ASES score — UHC uses this as a quality benchmark for shoulder surgery",
                    "Document subacromial injection response — temporary relief supports surgical indication",
                    "If tear is >3 cm, mention risk of progression without repair",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 60,
            },

            "carpal_tunnel_release": {
                "policy_number": "2023T0740C",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist (moderate to severe)",
                    "Failed minimum 6 weeks of conservative treatment (splinting, NSAIDs, activity modification)",
                    "Corticosteroid injection trial with documented response",
                    "Clinical symptoms consistent with CTS (numbness/tingling in median nerve distribution)",
                    "Positive Phalen test or Tinel sign on examination",
                    "Thenar atrophy or persistent sensory deficit may bypass conservative care and injection requirements",
                ],
                "required_documentation": [
                    "EMG/NCS report within 12 months confirming median neuropathy",
                    "Physical examination documenting Phalen, Tinel, and thenar muscle assessment",
                    "Conservative treatment records (splinting log, medication trial)",
                    "Injection record with response documentation",
                    "Functional impact statement (work limitations, ADL difficulties)",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS or EMG showing only mild changes",
                    "No injection trial documented",
                    "Insufficient conservative treatment (less than 6 weeks)",
                    "EMG/NCS older than 12 months",
                ],
                "approval_tips": [
                    "UHC requires EMG/NCS for carpal tunnel release — clinical diagnosis alone is insufficient",
                    "If EMG shows mild CTS, document thenar weakness or persistent symptoms despite conservative care",
                    "Include a functional impact statement describing specific work and ADL limitations",
                    "Bilateral requests should be submitted separately with individual EMG/NCS for each side",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 70,
            },

            "shoulder_arthroscopy": {
                "policy_number": "2023T0750S",
                "policy_name": "Shoulder Arthroscopy (Diagnostic/Therapeutic)",
                "criteria": [
                    "MRI demonstrating labral tear, loose bodies, or other intra-articular pathology",
                    "Failed minimum 6 weeks of conservative treatment (PT, NSAIDs, injection)",
                    "Mechanical symptoms (locking, catching, popping) documented",
                    "Positive provocative tests on examination (O'Brien, Speed, apprehension)",
                    "Diagnostic arthroscopy alone not typically authorized without MRI findings",
                    "For labral repair: MRI arthrogram preferred to confirm labral pathology",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination with provocative tests documented",
                    "Physical therapy records (minimum 6 weeks)",
                    "Injection records with response (diagnostic or therapeutic)",
                    "Description of mechanical symptoms and functional limitations",
                    "Operative plan with planned procedures",
                ],
                "common_denial_reasons": [
                    "No MRI obtained prior to request — clinical diagnosis alone insufficient",
                    "Diagnostic arthroscopy without identified intra-articular pathology on MRI",
                    "Insufficient conservative care (less than 6 weeks PT)",
                    "No mechanical symptoms documented — only pain",
                ],
                "approval_tips": [
                    "MRI arthrogram significantly improves approval for labral pathology",
                    "Document specific mechanical symptoms (locking, catching) — pain alone is not sufficient",
                    "Include injection response — if intra-articular injection provided relief, it supports an articular source",
                    "List all planned arthroscopic procedures (debridement, repair, acromioplasty) in the operative plan",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 58,
            },

            # ----------------------------------------------------------
            # CONCUSSION / TBI
            # ----------------------------------------------------------

            "neuropsychological_testing": {
                "policy_number": "2023T0800N",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Documented traumatic brain injury (concussion, moderate TBI, or severe TBI) with persistent cognitive complaints >3 months post-injury",
                    "Objective cognitive deficits identified on screening (MOCA <26 or abnormal neurocognitive screen)",
                    "Testing requested to guide treatment planning or return-to-work/school decision",
                    "No neuropsychological testing within prior 12 months unless significant clinical change",
                    "Referral from treating neurologist, neurosurgeon, or physiatrist",
                    "Maximum 8 hours of testing per evaluation (16 units of 96132/96133)",
                ],
                "required_documentation": [
                    "Documentation of TBI event (ED records, imaging, mechanism of injury)",
                    "Clinical notes showing persistent cognitive complaints (memory, attention, executive function)",
                    "Screening cognitive test results (MOCA, MMSE, or computerized neurocognitive testing)",
                    "Referral from qualified physician with specific clinical question to be addressed",
                    "Prior neuropsychological testing reports if any",
                    "CPT codes and estimated testing hours",
                ],
                "common_denial_reasons": [
                    "Testing requested for <3 months post-injury without documented urgent indication",
                    "No objective screening showing cognitive deficit prior to requesting formal testing",
                    "Repeat testing within 12 months without documented clinical change",
                    "Testing hours exceed 8-hour maximum without justification",
                ],
                "approval_tips": [
                    "Include MOCA score or computerized cognitive screening results to demonstrate need",
                    "Clearly state the clinical question: return-to-work capacity, treatment planning, or baseline",
                    "If repeat testing, document specific clinical changes since last evaluation",
                    "UHC allows 8 hours standard — justify additional hours with complexity of the case",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 50,
            },

            "cognitive_rehabilitation": {
                "policy_number": "2023T0810C",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI with objective cognitive deficits on neuropsychological testing",
                    "Neuropsychological testing completed within 12 months recommending cognitive rehabilitation",
                    "Treatment plan with specific, measurable cognitive goals",
                    "Initial authorization for 12 sessions; extension requires progress documentation",
                    "Must be provided by licensed speech-language pathologist, occupational therapist, or neuropsychologist",
                    "Patient demonstrates potential for functional improvement (not solely maintenance)",
                    "No more than 24 sessions per calendar year without additional medical justification",
                ],
                "required_documentation": [
                    "Neuropsychological testing report with rehabilitation recommendations",
                    "Treatment plan with specific cognitive domains targeted and measurable goals",
                    "Provider credentials (SLP, OT, or neuropsychologist license)",
                    "Progress notes for each session if requesting extension beyond initial 12",
                    "Functional outcome measures (FIM, MPAI, or domain-specific measures)",
                    "Re-evaluation at 12-session mark with documented progress toward goals",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing supporting the need for rehabilitation",
                    "Treatment goals are vague or not measurable",
                    "No documented progress after initial 12 sessions when requesting extension",
                    "Provider not appropriately licensed for cognitive rehabilitation",
                    "Exceeds 24-session annual maximum without documented justification",
                ],
                "approval_tips": [
                    "Neuropsychological testing must specifically recommend cognitive rehabilitation — general recommendations are insufficient",
                    "Set SMART goals for each cognitive domain (attention, memory, executive function)",
                    "Track functional outcome measures at every session for extension requests",
                    "UHC is more likely to approve if goals are tied to return-to-work or return-to-school",
                    "Request peer-to-peer early if initial denial — cognitive rehab has reasonable P2P success rates",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 40,
            },
        },
    },

    # ======================================================================
    #  2. AETNA
    # ======================================================================
    "aetna": {
        "name": "Aetna",
        "type": "commercial",
        "source": "Aetna Clinical Policy Bulletins (CPBs)",
        "pa_portal": "Availity.com or Aetna Provider Portal",
        "phone": "1-888-632-3862",
        "avg_p2p_wait_days": 3,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "CPB 0743",
                "policy_name": "Spinal Surgery: Lumbar Spinal Fusion",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, medications, activity modification)",
                    "MRI or CT demonstrating pathology at the proposed fusion level(s)",
                    "Documented instability (spondylolisthesis, or dynamic instability on flexion-extension films)",
                    "OR degenerative disc disease at 1–2 levels with concordant symptoms",
                    "OR revision surgery for failed prior decompression with documented recurrent symptoms",
                    "Psychological screening recommended but not mandatory for patients with pain >6 months",
                    "ODI score ≥30 or equivalent functional impairment",
                    "BMI <40 recommended; BMI ≥40 requires documentation of weight management efforts",
                    "At least 1 epidural steroid injection or facet injection with documented response",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "Flexion-extension radiographs if instability is the indication",
                    "Physical therapy records with treatment dates and response",
                    "Medication history with response documentation",
                    "Injection records with response",
                    "Functional outcome scores (ODI)",
                    "Operative plan with levels and approach",
                    "Recent H&P (within 30 days)",
                ],
                "common_denial_reasons": [
                    "Conservative treatment less than 3 months",
                    "No objective instability demonstrated on imaging",
                    "Multi-level fusion (>2 levels) without individual level justification",
                    "Missing ODI or functional outcome scores",
                ],
                "approval_tips": [
                    "Cite CPB 0743 by number in the narrative — Aetna reviewers look for this",
                    "Aetna requires only 3 months conservative care vs. UHC's 6 months — highlight full compliance",
                    "For multi-level fusion, provide level-by-level imaging correlation",
                    "Psychological screening strengthens the case even though Aetna doesn't mandate it",
                ],
                "avg_decision_days": 15,
                "appeal_success_rate": 48,
            },

            "lumbar_decompression": {
                "policy_number": "CPB 0743",
                "policy_name": "Spinal Surgery: Lumbar Decompression",
                "criteria": [
                    "Failed minimum 4 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI demonstrating disc herniation, spinal stenosis, or foraminal stenosis with neural compression",
                    "Clinical symptoms correlating with imaging — radiculopathy or neurogenic claudication",
                    "Positive straight leg raise or neurological deficit on examination",
                    "EMG/NCS if radiculopathy is clinically equivocal",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination findings",
                    "Physical therapy records (minimum 4 weeks)",
                    "Medication trial documentation",
                    "EMG/NCS if obtained",
                    "Operative plan with levels",
                ],
                "common_denial_reasons": [
                    "Imaging does not correlate with clinical symptoms",
                    "Conservative treatment less than 4 weeks without progressive deficit",
                    "No neurological examination documented",
                ],
                "approval_tips": [
                    "Cite CPB 0743 in the submission",
                    "Aetna's threshold for decompression is 4 weeks — shorter than UHC's 6 weeks",
                    "For neurogenic claudication from stenosis, document walking tolerance in distance/blocks",
                    "Include gait assessment findings in the neurological exam",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 60,
            },

            "cervical_fusion_acdf": {
                "policy_number": "CPB 0743",
                "policy_name": "Spinal Surgery: Cervical Fusion (ACDF)",
                "criteria": [
                    "Failed minimum 4 weeks of conservative treatment unless cervical myelopathy",
                    "MRI demonstrating disc herniation or stenosis with cord or root compression",
                    "Radiculopathy or myelopathy with correlation to imaging findings",
                    "NDI score ≥30 or equivalent functional limitation",
                    "For myelopathy: Nurick grade or mJOA score documented",
                    "Maximum 4 contiguous levels for ACDF — non-contiguous levels require separate justification",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination with motor, sensory, and reflex findings",
                    "NDI or mJOA score",
                    "Conservative treatment records",
                    "Operative plan specifying levels and graft type",
                ],
                "common_denial_reasons": [
                    "No NDI or mJOA score documented",
                    "Conservative care < 4 weeks without myelopathy documentation",
                    "Non-contiguous level ACDF without individual level justification",
                ],
                "approval_tips": [
                    "For myelopathy, Aetna looks for mJOA score — include it alongside NDI",
                    "Cite CPB 0743 by number in the narrative",
                    "Document hand dexterity changes, balance difficulties, and Hoffmann sign",
                    "Aetna generally approves 1–2 level ACDF more readily than 3+ levels",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 52,
            },

            "cervical_decompression": {
                "policy_number": "CPB 0743",
                "policy_name": "Spinal Surgery: Cervical Decompression",
                "criteria": [
                    "Failed minimum 4 weeks of conservative treatment unless myelopathy present",
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Clinical myelopathy or radiculopathy correlating with imaging",
                    "NDI ≥30 or mJOA <14",
                    "Posterior approach indicated for multilevel stenosis, OPLL, or congenital stenosis",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination with gait assessment",
                    "NDI and/or mJOA scores",
                    "Conservative treatment records unless myelopathy",
                    "Operative plan with levels and approach",
                ],
                "common_denial_reasons": [
                    "No functional scores (NDI/mJOA) documented",
                    "Imaging does not show significant stenosis",
                    "Conservative care not documented when myelopathy is not present",
                ],
                "approval_tips": [
                    "mJOA score <14 is a strong indicator Aetna will approve",
                    "Document progression of myelopathy symptoms with timeline",
                    "For OPLL, CT scan is essential to document extent of ossification",
                    "Cite CPB 0743 in the narrative",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "spinal_cord_stimulator": {
                "policy_number": "CPB 0234",
                "policy_name": "Spinal Cord Stimulation",
                "criteria": [
                    "Diagnosis of FBSS, CRPS Type I or II, or chronic intractable neuropathic pain",
                    "Failed minimum 6 months of conservative treatment including medication management and PT",
                    "Successful trial stimulation of ≥3 days with ≥50% pain reduction on VAS",
                    "Psychological evaluation within 6 months clearing patient for implant",
                    "No untreated substance use disorder — urine drug screen within 30 days",
                    "Not a candidate for further corrective surgery",
                    "Pain duration ≥6 months",
                ],
                "required_documentation": [
                    "SCS trial report with pain scores and functional outcomes",
                    "Psychological evaluation report",
                    "Urine drug screen",
                    "Comprehensive pain management history",
                    "MRI or imaging of the spine",
                    "Physical therapy records",
                    "Operative plan for permanent implant",
                ],
                "common_denial_reasons": [
                    "Trial did not show ≥50% pain reduction",
                    "Psychological evaluation not performed or not within 6 months",
                    "Active substance use disorder identified",
                    "Conservative care less than 6 months",
                ],
                "approval_tips": [
                    "Cite CPB 0234 by number in the clinical narrative",
                    "Aetna requires only 3-day trial vs. UHC's 5-day minimum — confirm compliance",
                    "Include both pain scores AND functional improvement data from the trial",
                    "Document why corrective surgery is not an option",
                ],
                "avg_decision_days": 18,
                "appeal_success_rate": 38,
            },

            "epidural_steroid_injection": {
                "policy_number": "CPB 0016",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "Radicular symptoms correlating with imaging pathology",
                    "Failed minimum 2 weeks of oral medication management",
                    "Maximum 3 injections per spinal region per 6-month period",
                    "Fluoroscopic or CT guidance required",
                    "Documented functional limitation from radicular pain",
                    "Prior injection response documented before authorizing subsequent injection",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology at target level",
                    "Pain description and distribution",
                    "Medication trial records",
                    "Prior injection response if applicable",
                    "Planned approach and level",
                ],
                "common_denial_reasons": [
                    "More than 3 injections per region in 6 months — Aetna uses 6-month window not 12",
                    "No imaging correlation to proposed injection level",
                    "Non-fluoroscopic injection proposed",
                ],
                "approval_tips": [
                    "Note Aetna uses 6-month window (3 per region) vs. UHC's 12-month window",
                    "Cite CPB 0016 in the submission",
                    "Document specific functional limitations — not just pain level",
                    "If requesting 3rd injection, provide clear rationale for continued benefit",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 68,
            },

            "total_knee_replacement": {
                "policy_number": "CPB 0544",
                "policy_name": "Knee Replacement Surgery",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, NSAIDs, injections)",
                    "Weight-bearing radiographs demonstrating Kellgren-Lawrence Grade III or IV OA",
                    "Functional impairment documented with KOOS or WOMAC",
                    "BMI <40 recommended; higher BMI requires documented weight management",
                    "Trial of at least 1 intra-articular corticosteroid injection",
                    "HbA1c <8.0 for diabetic patients within 3 months",
                    "Medically optimized for surgery (cardiac clearance if indicated)",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "KOOS or WOMAC scores",
                    "Physical therapy records",
                    "Injection records with response",
                    "Medication history",
                    "HbA1c if diabetic",
                    "Medical clearance if significant comorbidities",
                ],
                "common_denial_reasons": [
                    "Radiographs not weight-bearing or show only mild arthritis",
                    "No functional outcome scores",
                    "HbA1c ≥8.0 not addressed",
                    "Insufficient conservative care (less than 3 months)",
                ],
                "approval_tips": [
                    "Cite CPB 0544 in the narrative",
                    "Aetna tends to approve TKA with Kellgren-Lawrence Grade III-IV and 3 months conservative care",
                    "Include walking distance, stair climbing ability, and sleep disturbance from pain",
                    "Document failed viscosupplementation as additional conservative measure",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 58,
            },

            "total_hip_replacement": {
                "policy_number": "CPB 0544",
                "policy_name": "Hip Replacement Surgery",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment",
                    "Radiographic evidence of severe OA (Kellgren-Lawrence Grade III-IV) or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Functional impairment with Harris Hip Score <60 or HOOS documenting limitation",
                    "Failed intra-articular corticosteroid injection or documented contraindication",
                    "BMI <40 recommended; higher BMI requires documentation",
                    "HbA1c <8.0 for diabetics",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "Physical therapy records",
                    "Injection records",
                    "Medication history",
                    "HbA1c if diabetic",
                ],
                "common_denial_reasons": [
                    "Radiographs showing only mild-moderate OA",
                    "No Harris Hip Score or HOOS included",
                    "Insufficient conservative care",
                    "No injection trial documented",
                ],
                "approval_tips": [
                    "Cite CPB 0544 in the submission",
                    "Harris Hip Score <60 is Aetna's threshold for surgical indication",
                    "For AVN, include MRI with Ficat staging",
                    "Aetna approves THA more readily than TKA — ensure documentation is complete",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 60,
            },

            "acl_reconstruction": {
                "policy_number": "CPB 0651",
                "policy_name": "ACL Reconstruction Surgery",
                "criteria": [
                    "MRI confirming complete ACL tear",
                    "Clinical examination with positive Lachman and/or pivot shift",
                    "Functional instability with documented giving way events",
                    "For partial tears: documented instability despite bracing and rehabilitation",
                    "Pre-habilitation PT recommended (minimum 2–4 weeks) to restore ROM",
                    "Activity demands supporting surgical reconstruction over non-operative management",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear within 6 months",
                    "Physical examination findings",
                    "Description of instability episodes",
                    "Pre-habilitation PT records if applicable",
                    "Activity level and functional goals",
                ],
                "common_denial_reasons": [
                    "Partial ACL tear without documented instability",
                    "No physical examination findings documenting instability",
                    "No MRI obtained",
                    "Low-demand patient without documented functional instability",
                ],
                "approval_tips": [
                    "Cite CPB 0651 in the narrative",
                    "Aetna is generally favorable for ACL reconstruction in active patients",
                    "Document concomitant meniscal tears — they strengthen the surgical indication",
                    "For patients >40, document continued high-demand activities",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 65,
            },

            "rotator_cuff_repair": {
                "policy_number": "CPB 0234",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "MRI confirming full-thickness tear or high-grade partial tear (>50%)",
                    "Failed minimum 6 weeks of conservative care (PT, NSAIDs, subacromial injection)",
                    "Acute traumatic tear may bypass conservative care requirement",
                    "ASES score or DASH score documenting functional impairment",
                    "No significant fatty infiltration (Goutallier Grade 3–4) suggesting irreparable tear",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "Physical therapy records",
                    "Injection records with response",
                    "Physical examination with strength and ROM testing",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% without failed conservative care",
                    "No ASES or DASH score documented",
                    "Less than 6 weeks of conservative treatment",
                    "Irreparable tear on MRI (massive tear with retraction and fatty infiltration)",
                ],
                "approval_tips": [
                    "Include ASES score with every rotator cuff repair submission to Aetna",
                    "For acute tears, document date of injury and mechanism clearly",
                    "Mention tear size in cm and number of tendons involved",
                    "If concurrent biceps tenotomy/tenodesis planned, include it in the operative plan",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 62,
            },

            "carpal_tunnel_release": {
                "policy_number": "CPB 0357",
                "policy_name": "Carpal Tunnel Surgery",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Failed minimum 4 weeks of conservative treatment (splinting, NSAIDs)",
                    "Clinical symptoms of CTS (numbness in median nerve distribution)",
                    "Positive provocative tests (Phalen, Tinel) on examination",
                    "Injection trial recommended but not mandatory if EMG shows moderate-severe CTS",
                    "Thenar atrophy may expedite authorization without conservative care",
                ],
                "required_documentation": [
                    "EMG/NCS report within 12 months",
                    "Physical examination with provocative tests",
                    "Conservative treatment records",
                    "Functional impact on work and ADLs",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS obtained",
                    "EMG showing only mild CTS without failed conservative care",
                    "Conservative treatment less than 4 weeks",
                ],
                "approval_tips": [
                    "Cite CPB 0357 in the submission",
                    "Aetna does not mandate injection trial if EMG shows moderate-severe CTS — but document why injection was not done",
                    "Note Aetna requires only 4 weeks conservative care vs. UHC's 6 weeks",
                    "If bilateral, Aetna allows same-day bilateral CTR in appropriate patients",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 72,
            },

            "shoulder_arthroscopy": {
                "policy_number": "CPB 0234",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "MRI demonstrating intra-articular pathology (labral tear, loose bodies, synovitis)",
                    "Failed minimum 6 weeks of conservative treatment",
                    "Mechanical symptoms documented (locking, catching, clicking)",
                    "Positive provocative tests on examination",
                    "For instability: documented recurrent dislocations or subluxations",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination with provocative tests",
                    "Physical therapy records",
                    "Documentation of mechanical symptoms or instability events",
                    "Operative plan listing all planned procedures",
                ],
                "common_denial_reasons": [
                    "No MRI obtained before surgical request",
                    "Pure diagnostic arthroscopy without MRI evidence of pathology",
                    "Less than 6 weeks of conservative care",
                    "No mechanical symptoms — pain alone insufficient",
                ],
                "approval_tips": [
                    "MRI arthrogram is preferred by Aetna for suspected labral pathology",
                    "Document specific instability events with dates for labral repair indications",
                    "List all planned arthroscopic procedures — Aetna wants to know the full scope",
                    "For adhesive capsulitis, document failed manipulation under anesthesia before requesting arthroscopic release",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 58,
            },

            "neuropsychological_testing": {
                "policy_number": "CPB 0158",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Documented TBI or neurological condition with persistent cognitive deficits >3 months",
                    "Screening cognitive assessment showing impairment (MOCA <26 or equivalent)",
                    "Testing to guide treatment planning, return-to-work decisions, or educational accommodations",
                    "No testing within 12 months unless significant clinical change documented",
                    "Referral from neurologist, neurosurgeon, physiatrist, or psychiatrist",
                    "Maximum 12 hours of testing per evaluation with justification for >8 hours",
                ],
                "required_documentation": [
                    "Documentation of neurological condition or TBI",
                    "Screening cognitive test results",
                    "Clinical question to be answered by testing",
                    "Referral from qualified physician",
                    "Prior testing reports if available",
                    "Estimated testing hours with CPT code breakdown",
                ],
                "common_denial_reasons": [
                    "Testing requested within 12 months of prior evaluation without documented change",
                    "No screening cognitive test demonstrating impairment",
                    "Testing purpose not clearly stated (vague referral)",
                    "Requesting testing for non-covered indications (e.g., learning disability evaluation in adult)",
                ],
                "approval_tips": [
                    "Cite CPB 0158 by number in the submission",
                    "Clearly state the clinical question and how results will change management",
                    "Aetna allows up to 12 hours — more flexible than UHC's 8-hour standard",
                    "Include MOCA or other screening score to justify need for comprehensive testing",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 48,
            },

            "cognitive_rehabilitation": {
                "policy_number": "CPB 0158",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI or acquired brain injury with objective cognitive deficits",
                    "Neuropsychological testing within 12 months recommending rehabilitation",
                    "Specific measurable treatment goals established",
                    "Provider is licensed SLP, OT, or neuropsychologist",
                    "Initial authorization for 12 sessions; extensions require documented progress",
                    "Patient demonstrates functional improvement potential",
                ],
                "required_documentation": [
                    "Neuropsychological testing report",
                    "Treatment plan with measurable goals",
                    "Provider credentials",
                    "Progress notes for extension requests",
                    "Functional outcome measures",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing supporting the need",
                    "Goals not measurable or specific",
                    "No progress documented for extension requests",
                    "Maintenance therapy — no potential for further improvement",
                ],
                "approval_tips": [
                    "Cite CPB 0158 in the submission",
                    "Set specific measurable goals tied to functional outcomes (return-to-work, independent ADLs)",
                    "Document progress quantitatively at each session for easier extension approval",
                    "Aetna's initial 12-session block is standard — plan for extension request at session 10",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 42,
            },
        },
    },

    # ======================================================================
    #  3. BLUE CROSS BLUE SHIELD (BCBS) — National Policies
    # ======================================================================
    "bcbs": {
        "name": "Blue Cross Blue Shield (BCBS)",
        "type": "commercial",
        "source": "BCBS Medical Policy Reference Manual & Evidence Street",
        "pa_portal": "Availity.com or plan-specific BCBS portal",
        "phone": "Varies by plan — see back of member ID card",
        "avg_p2p_wait_days": 4,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "MED.00024",
                "policy_name": "Lumbar Spinal Fusion",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment including PT and medication management",
                    "MRI or CT demonstrating structural pathology at the proposed fusion level(s)",
                    "Documented spinal instability, spondylolisthesis Grade I+, or DDD at 1–2 levels",
                    "BMI <40 preferred; BMI ≥40 considered with additional justification",
                    "Functional outcome score (ODI ≥30) documented",
                    "At least 1 epidural steroid injection with documented response",
                    "Physical therapy minimum 8 sessions over 4 weeks",
                    "Tobacco status documented; cessation encouraged but not mandatory for approval",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "Physical therapy records",
                    "Medication history",
                    "Injection records with response",
                    "ODI score",
                    "Operative plan with levels and approach",
                    "H&P within 30 days",
                ],
                "common_denial_reasons": [
                    "Conservative treatment less than 3 months",
                    "Multi-level fusion (>2 levels) without individual level justification",
                    "No ODI or functional score included",
                    "Imaging does not demonstrate instability or DDD at proposed level",
                ],
                "approval_tips": [
                    "BCBS is generally moderate on lumbar fusion — 3 months conservative care is the key threshold",
                    "Reference BCBS Medical Policy MED.00024 in the narrative",
                    "BCBS does not mandate tobacco cessation like UHC — but document status",
                    "For multi-level, provide imaging correlation for each level",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 50,
            },

            "lumbar_decompression": {
                "policy_number": "MED.00024",
                "policy_name": "Lumbar Decompression",
                "criteria": [
                    "Failed minimum 4 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI showing disc herniation or stenosis with neural compression",
                    "Radiculopathy or neurogenic claudication correlating with imaging",
                    "Neurological examination findings documented",
                    "EMG/NCS if radiculopathy is clinically uncertain",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination",
                    "PT records (minimum 4 weeks)",
                    "Medication trial documentation",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Imaging does not show neural compression at the proposed level",
                    "Insufficient conservative treatment",
                    "No neurological exam findings in the submission",
                ],
                "approval_tips": [
                    "BCBS approves decompression more readily than fusion — ensure imaging clearly shows compression",
                    "Reference MED.00024 in the narrative",
                    "Document walking tolerance for stenosis cases — distance, blocks, and duration",
                    "Progressive motor deficit should be flagged as urgent",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 62,
            },

            "cervical_fusion_acdf": {
                "policy_number": "MED.00024",
                "policy_name": "Cervical Fusion / ACDF",
                "criteria": [
                    "Failed minimum 4 weeks of conservative care unless myelopathy is present",
                    "MRI demonstrating disc herniation or stenosis with cord or root compression",
                    "Radiculopathy or myelopathy correlating with imaging",
                    "NDI ≥30 documented",
                    "Maximum 3 levels for routine ACDF; 4 levels requires additional clinical justification",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI score",
                    "Conservative treatment records",
                    "Operative plan with levels",
                ],
                "common_denial_reasons": [
                    "No NDI score included",
                    "Conservative care less than 4 weeks without myelopathy",
                    "4-level ACDF without strong justification",
                ],
                "approval_tips": [
                    "BCBS generally approves 1–2 level ACDF with moderate criteria",
                    "For myelopathy, include mJOA score alongside NDI",
                    "Reference MED.00024 in the submission",
                    "BCBS is more flexible than UHC on BMI — document but don't worry about the cutoff as much",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "cervical_decompression": {
                "policy_number": "MED.00024",
                "policy_name": "Cervical Decompression",
                "criteria": [
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Failed 4 weeks of conservative treatment unless myelopathy is present",
                    "Clinical symptoms correlating with imaging",
                    "Neurological examination documenting deficits",
                    "NDI ≥30 or mJOA <14",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI or mJOA score",
                    "Conservative treatment records unless myelopathy",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No functional score documented",
                    "Imaging does not show significant compression",
                    "Conservative care inadequately documented",
                ],
                "approval_tips": [
                    "Reference MED.00024 in the narrative",
                    "BCBS tends to approve cervical decompression for myelopathy readily",
                    "Document upper motor neuron signs clearly",
                    "Include CT if bony pathology is the primary indication",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 58,
            },

            "spinal_cord_stimulator": {
                "policy_number": "MED.00079",
                "policy_name": "Spinal Cord Stimulation",
                "criteria": [
                    "Chronic neuropathic pain ≥6 months (FBSS, CRPS, peripheral neuropathy)",
                    "Failed comprehensive conservative management including medications, PT, and injections",
                    "Successful SCS trial ≥3 days with ≥50% pain reduction",
                    "Psychological evaluation within 12 months recommending implant",
                    "No active substance abuse",
                    "Not a candidate for further corrective surgery",
                ],
                "required_documentation": [
                    "SCS trial report with outcomes",
                    "Psychological evaluation",
                    "Pain management history",
                    "Urine drug screen",
                    "MRI or imaging",
                    "PT records",
                ],
                "common_denial_reasons": [
                    "Trial did not show ≥50% improvement",
                    "No psychological evaluation",
                    "Active substance abuse concerns",
                    "Less than 6 months of conservative care",
                ],
                "approval_tips": [
                    "Reference MED.00079 in the narrative",
                    "BCBS allows 12-month window for psychological evaluation — more flexible than UHC",
                    "Include functional outcomes from the trial, not just pain scores",
                    "Document opioid reduction during the trial period if applicable",
                ],
                "avg_decision_days": 18,
                "appeal_success_rate": 37,
            },

            "epidural_steroid_injection": {
                "policy_number": "MED.00052",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "Radicular pain correlating with imaging pathology",
                    "Failed initial trial of conservative treatment (medications, activity modification)",
                    "Maximum 3 injections per region per rolling 12-month period",
                    "Fluoroscopic guidance required",
                    "Documented response to prior injection before additional injection authorized",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Pain description and distribution",
                    "Medication trial records",
                    "Prior injection response if applicable",
                    "Planned approach and level",
                ],
                "common_denial_reasons": [
                    "Exceeded 3 injections per region in 12 months",
                    "No imaging correlation",
                    "No documented response to prior injection",
                ],
                "approval_tips": [
                    "Reference MED.00052 in the submission",
                    "BCBS uses 12-month rolling window (like UHC, unlike Aetna's 6-month window)",
                    "Document functional improvement from prior injections, not just pain relief",
                    "Include return-to-work or activity improvement data when available",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 67,
            },

            "total_knee_replacement": {
                "policy_number": "SURG.00035",
                "policy_name": "Total Knee Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, medications, injections)",
                    "Weight-bearing radiographs showing Kellgren-Lawrence Grade III or IV OA",
                    "Functional impairment documented with KOOS, WOMAC, or Knee Society Score",
                    "BMI <40 preferred but not mandatory with documentation",
                    "Trial of intra-articular injection (corticosteroid or viscosupplementation)",
                    "HbA1c <8.0 for diabetic patients",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "Functional outcome scores",
                    "PT records",
                    "Injection records with response",
                    "Medication history",
                    "HbA1c if diabetic",
                ],
                "common_denial_reasons": [
                    "Non-weight-bearing radiographs submitted",
                    "No functional outcome score",
                    "Less than 3 months conservative care",
                    "HbA1c ≥8.0 not optimized",
                ],
                "approval_tips": [
                    "BCBS tends to approve TKA more readily than many payers — ensure radiographs are weight-bearing",
                    "Reference SURG.00035 in the narrative",
                    "BCBS does not strictly require BMI <40 — document but it's not an automatic barrier",
                    "Include alignment views (long-standing AP) for varus/valgus deformity documentation",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 62,
            },

            "total_hip_replacement": {
                "policy_number": "SURG.00035",
                "policy_name": "Total Hip Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment",
                    "Radiographic evidence of severe OA or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Harris Hip Score <60 or HOOS documenting significant limitation",
                    "Corticosteroid injection trial or documented contraindication",
                    "HbA1c <8.0 for diabetic patients",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "PT records",
                    "Injection records",
                    "Medication history",
                    "HbA1c if diabetic",
                ],
                "common_denial_reasons": [
                    "Mild-moderate radiographic changes",
                    "No Harris Hip Score or HOOS",
                    "Insufficient conservative treatment",
                ],
                "approval_tips": [
                    "BCBS approves THA readily with KL Grade III-IV — one of the easier payers for hip replacement",
                    "Reference SURG.00035 in the narrative",
                    "Include AP pelvis showing both hips for side comparison",
                    "Document impact on gait, sleep, and daily activities",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 65,
            },

            "acl_reconstruction": {
                "policy_number": "SURG.00042",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "MRI confirming complete ACL tear",
                    "Functional instability with giving way episodes documented",
                    "Positive Lachman test and/or pivot shift on examination",
                    "Pre-habilitation PT recommended (2–4 weeks) to restore ROM",
                    "Active patient with functional demands requiring knee stability",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear",
                    "Physical examination findings",
                    "Instability episode documentation",
                    "Pre-hab PT records",
                    "Activity level description",
                ],
                "common_denial_reasons": [
                    "Partial tear without documented instability",
                    "No physical examination findings",
                    "Low-demand patient without functional instability",
                ],
                "approval_tips": [
                    "Reference SURG.00042 in the narrative",
                    "BCBS generally approves ACL reconstruction readily for complete tears",
                    "Document concomitant meniscal or cartilage injury",
                    "Include Tegner activity level score if available",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 68,
            },

            "rotator_cuff_repair": {
                "policy_number": "SURG.00050",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "MRI showing full-thickness tear or high-grade (>50%) partial tear",
                    "Failed minimum 6 weeks of conservative treatment (PT, NSAIDs, injection)",
                    "Acute traumatic tear may bypass conservative care",
                    "Functional impairment documented with ASES or DASH score",
                    "No irreparable tear (massive retracted tear with Goutallier Grade 4)",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "PT records (minimum 6 weeks)",
                    "Injection records with response",
                    "Physical examination",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% without failed conservative care",
                    "No functional outcome score",
                    "Less than 6 weeks PT",
                    "Irreparable tear based on MRI",
                ],
                "approval_tips": [
                    "Reference SURG.00050 in the narrative",
                    "BCBS weighs ASES scores in their decision — include with every submission",
                    "For acute tears, clearly document mechanism and temporal relationship",
                    "Document tear retraction and muscle quality on MRI to address reparability",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 63,
            },

            "carpal_tunnel_release": {
                "policy_number": "SURG.00055",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Failed minimum 4 weeks of conservative treatment (splinting, NSAIDs)",
                    "Positive Phalen and/or Tinel test on examination",
                    "Thenar atrophy or severe EMG findings may expedite approval",
                    "Injection trial recommended but not mandatory",
                ],
                "required_documentation": [
                    "EMG/NCS report within 12 months",
                    "Physical examination findings",
                    "Conservative treatment records",
                    "Functional impact statement",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS obtained",
                    "EMG showing only mild CTS without thenar atrophy",
                    "Insufficient conservative treatment",
                ],
                "approval_tips": [
                    "Reference SURG.00055 in the narrative",
                    "BCBS does not strictly require injection trial — document why it was not done if omitted",
                    "Moderate-severe EMG with positive exam findings is generally approved without difficulty",
                    "Document specific occupational impact for work-related cases",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 73,
            },

            "shoulder_arthroscopy": {
                "policy_number": "SURG.00050",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "MRI demonstrating intra-articular pathology",
                    "Failed minimum 6 weeks of conservative care",
                    "Mechanical symptoms or instability documented",
                    "Positive provocative tests on examination",
                    "Diagnostic arthroscopy alone requires MRI evidence of pathology",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination with provocative tests",
                    "PT records",
                    "Injection records if applicable",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No MRI prior to surgical request",
                    "No mechanical symptoms documented",
                    "Pure diagnostic arthroscopy without MRI pathology",
                ],
                "approval_tips": [
                    "Reference SURG.00050 in the narrative",
                    "BCBS prefers MRI arthrogram for labral pathology evaluation",
                    "Document specific instability events with dates and descriptions",
                    "List all planned procedures in the operative plan",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 60,
            },

            "neuropsychological_testing": {
                "policy_number": "MED.00110",
                "policy_name": "Neuropsychological and Psychological Testing",
                "criteria": [
                    "Documented TBI or neurological condition with persistent cognitive complaints",
                    "Screening assessment showing cognitive impairment",
                    "Clinical question clearly stated for testing to address",
                    "No testing within prior 12 months unless documented clinical change",
                    "Referral from treating physician",
                    "Maximum 10 hours of testing per evaluation",
                ],
                "required_documentation": [
                    "Documentation of TBI or neurological condition",
                    "Screening cognitive test results",
                    "Clinical question for testing",
                    "Referral from physician",
                    "Estimated testing hours",
                ],
                "common_denial_reasons": [
                    "Repeat testing within 12 months without clinical change",
                    "No screening test showing impairment",
                    "Vague clinical question",
                    "Testing exceeds 10-hour maximum without justification",
                ],
                "approval_tips": [
                    "Reference MED.00110 in the narrative",
                    "BCBS allows 10 hours — between UHC (8) and Aetna (12)",
                    "Clearly articulate how test results will change management",
                    "Include MOCA or similar screening score",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 50,
            },

            "cognitive_rehabilitation": {
                "policy_number": "MED.00110",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI or acquired brain injury with cognitive deficits on testing",
                    "Neuropsychological testing within 12 months recommending rehab",
                    "Measurable treatment goals established",
                    "Licensed provider (SLP, OT, neuropsychologist)",
                    "Initial 12 sessions; extensions require progress notes",
                    "Patient shows improvement potential",
                ],
                "required_documentation": [
                    "Neuropsychological testing report",
                    "Treatment plan with goals",
                    "Provider credentials",
                    "Progress notes for extensions",
                    "Functional outcome measures",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing supporting need",
                    "Non-measurable goals",
                    "No progress documented for extension",
                    "Maintenance-only therapy",
                ],
                "approval_tips": [
                    "Reference MED.00110 in the narrative",
                    "BCBS follows similar patterns to Aetna for cognitive rehab — 12-session blocks",
                    "Tie goals to functional outcomes (work, school, independent living)",
                    "Document progress quantitatively at each session",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 44,
            },
        },
    },

    # ======================================================================
    #  4. CIGNA
    # ======================================================================
    "cigna": {
        "name": "Cigna",
        "type": "commercial",
        "source": "Cigna Medical Coverage Policies & EviCore Clinical Guidelines",
        "pa_portal": "CignaforHCP.com or EviCore portal (evicore.com)",
        "phone": "1-800-768-4695 (EviCore: 1-888-693-3211)",
        "avg_p2p_wait_days": 7,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "MCP 0059",
                "policy_name": "Spinal Fusion — Lumbar",
                "criteria": [
                    "Failed minimum 3 months (12 weeks) of comprehensive conservative treatment",
                    "MRI or CT demonstrating structural pathology at proposed level(s)",
                    "Instability documented on flexion-extension radiographs (>4 mm translation or >10° angulation)",
                    "OR spondylolisthesis Grade I+ with neurological deficit or functional impairment",
                    "OR DDD at 1–2 levels with concordant symptoms after failed decompression",
                    "ODI ≥30 or equivalent validated functional measure",
                    "At least 1 therapeutic injection with documented response",
                    "Physical therapy ≥12 sessions documented with outcomes",
                    "BMI documented — BMI ≥40 requires weight management program documentation",
                    "Tobacco screening documented — cessation recommended but not mandatory",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "Flexion-extension radiographs if instability indication",
                    "PT records with session-by-session documentation",
                    "Medication history with response",
                    "Injection records with outcomes",
                    "ODI score",
                    "Operative plan with levels, approach, and CPT codes",
                    "H&P within 30 days",
                    "BMI and tobacco status",
                ],
                "common_denial_reasons": [
                    "Conservative treatment less than 12 weeks documented",
                    "EviCore reviewer requests peer-to-peer and surgeon does not complete it in time",
                    "No ODI score in the submission",
                    "Multi-level fusion without individual level justification",
                    "Missing injection documentation",
                ],
                "approval_tips": [
                    "Cigna uses EviCore for PA — be prepared for peer-to-peer review more often than other payers",
                    "Schedule P2P promptly — EviCore denies if P2P not completed within 5 business days",
                    "Reference Cigna MCP 0059 AND EviCore Spine Surgery Guidelines in the narrative",
                    "Submit through EviCore portal for faster processing than fax",
                    "Include ODI and VAS in every submission — EviCore reviewers look for these first",
                ],
                "avg_decision_days": 15,
                "appeal_success_rate": 42,
            },

            "lumbar_decompression": {
                "policy_number": "MCP 0059",
                "policy_name": "Lumbar Decompression (Laminectomy/Discectomy)",
                "criteria": [
                    "Failed minimum 6 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI demonstrating disc herniation or stenosis with neural compression",
                    "Radiculopathy or neurogenic claudication correlating with imaging",
                    "Positive SLR test or documented neurological deficit",
                    "EMG/NCS if radiculopathy is clinically equivocal",
                    "VAS leg ≥6 or equivalent pain severity documented",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination",
                    "PT records (minimum 6 weeks)",
                    "Medication trial documentation",
                    "VAS scores (back and leg separately)",
                    "Operative plan with levels",
                ],
                "common_denial_reasons": [
                    "Imaging does not correlate with symptoms",
                    "Conservative treatment less than 6 weeks without progressive deficit",
                    "No VAS scores documented",
                    "EviCore peer-to-peer not completed within deadline",
                ],
                "approval_tips": [
                    "EviCore processes decompression more quickly than fusion — but still prepare for P2P",
                    "Document VAS leg score separately — EviCore uses this as a threshold metric",
                    "For cauda equina or progressive motor deficit, mark as urgent on EviCore submission",
                    "Include walking tolerance in distance for stenosis cases",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "cervical_fusion_acdf": {
                "policy_number": "MCP 0059",
                "policy_name": "Cervical Fusion / ACDF",
                "criteria": [
                    "Failed minimum 6 weeks of conservative care unless myelopathy present",
                    "MRI demonstrating disc herniation or spondylotic stenosis with neural compression",
                    "Radiculopathy or myelopathy correlating with imaging",
                    "NDI ≥30 documented",
                    "For myelopathy: mJOA score documented showing functional decline",
                    "Maximum 3 levels without additional justification; 4 levels requires detailed rationale",
                    "Tobacco screening documented",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI score",
                    "mJOA if myelopathy",
                    "Conservative treatment records",
                    "Operative plan with levels and approach",
                    "Tobacco status",
                ],
                "common_denial_reasons": [
                    "No NDI score documented",
                    "EviCore peer-to-peer not completed",
                    "Conservative care less than 6 weeks without documented myelopathy",
                    "4-level ACDF without strong justification",
                ],
                "approval_tips": [
                    "EviCore commonly requests P2P for cervical fusion — schedule immediately upon notification",
                    "mJOA <12 is a strong indicator for approval with myelopathy indication",
                    "Reference Cigna MCP 0059 and EviCore Cervical Spine Guidelines",
                    "Submit via EviCore portal and call to confirm receipt within 24 hours",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 48,
            },

            "cervical_decompression": {
                "policy_number": "MCP 0059",
                "policy_name": "Cervical Decompression",
                "criteria": [
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Failed 6 weeks conservative treatment unless myelopathy present",
                    "Neurological examination findings correlating with imaging",
                    "NDI ≥30 or mJOA <14",
                    "For multilevel stenosis: CT recommended in addition to MRI",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "CT if bony pathology",
                    "Neurological examination",
                    "NDI and/or mJOA score",
                    "Conservative treatment records",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No functional scores (NDI/mJOA)",
                    "EviCore P2P not completed in time",
                    "Insufficient imaging to demonstrate compression",
                ],
                "approval_tips": [
                    "Schedule EviCore P2P call immediately upon request — do not delay",
                    "For posterior cervical decompression, document why anterior approach is not suitable",
                    "mJOA <12 strongly supports approval",
                    "Include CT scan for OPLL or complex bony stenosis",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 50,
            },

            "spinal_cord_stimulator": {
                "policy_number": "MCP 0135",
                "policy_name": "Spinal Cord Stimulation / Neuromodulation",
                "criteria": [
                    "Chronic neuropathic pain ≥6 months (FBSS, CRPS, chronic neuropathic pain)",
                    "Failed minimum 6 months of multimodal conservative treatment",
                    "Successful SCS trial ≥5 days with ≥50% pain reduction AND functional improvement",
                    "Psychological evaluation within 6 months clearing patient for implant",
                    "Negative urine drug screen within 30 days",
                    "No active untreated psychiatric disorder or substance use disorder",
                    "Not a candidate for corrective surgical intervention",
                    "BMI <40 or documented justification if ≥40",
                ],
                "required_documentation": [
                    "SCS trial report with daily pain and function logs",
                    "Psychological evaluation",
                    "Urine drug screen",
                    "Comprehensive pain treatment history",
                    "MRI/imaging",
                    "PT records",
                    "Medication history including opioid usage",
                    "Functional outcome measures (ODI, PCS)",
                ],
                "common_denial_reasons": [
                    "Trial did not demonstrate both ≥50% pain reduction AND functional improvement",
                    "EviCore peer-to-peer not completed",
                    "Psychological evaluation not within 6-month window",
                    "Positive UDS or substance abuse history",
                    "Conservative care less than 6 months",
                ],
                "approval_tips": [
                    "Cigna/EviCore requires BOTH pain reduction AND functional improvement from trial — document both explicitly",
                    "EviCore almost always requests P2P for SCS — have the surgeon prepared with trial data",
                    "Include daily activity logs from the trial period showing functional gains",
                    "Document opioid dose reduction during trial if applicable",
                    "Reference Cigna MCP 0135 in the clinical narrative",
                ],
                "avg_decision_days": 22,
                "appeal_success_rate": 32,
            },

            "epidural_steroid_injection": {
                "policy_number": "MCP 0093",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "Radicular pain correlating with MRI or CT pathology",
                    "Failed minimum 2 weeks of conservative treatment (medications, PT)",
                    "Maximum 3 injections per region per 12-month period",
                    "Minimum 14-day interval between injections at the same level",
                    "Fluoroscopic guidance required",
                    "Response to prior injection documented before additional injection",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Pain distribution description",
                    "Medication trial records",
                    "Prior injection response if applicable",
                    "Planned approach, level, and guidance",
                ],
                "common_denial_reasons": [
                    "Exceeded 3 injections per region per year",
                    "Less than 14 days between injections at same level",
                    "No imaging correlation to proposed injection level",
                    "No documented response to prior injection",
                ],
                "approval_tips": [
                    "Cigna/EviCore may not require PA for ESI in all plans — verify with member services first",
                    "Document both pain relief duration and functional improvement from each prior injection",
                    "Specify fluoroscopic guidance in the request — non-image-guided will be denied",
                    "Submit via EviCore portal for ESI — faster than phone or fax",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 62,
            },

            "total_knee_replacement": {
                "policy_number": "MCP 0218",
                "policy_name": "Total Knee Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, NSAIDs, injections)",
                    "Weight-bearing radiographs demonstrating Kellgren-Lawrence Grade III or IV",
                    "KOOS or WOMAC score documenting functional impairment",
                    "Trial of corticosteroid injection with documented response",
                    "BMI <40 preferred; BMI ≥40 requires weight management documentation",
                    "HbA1c <8.0 for diabetic patients",
                    "Preoperative medical optimization documented",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "KOOS or WOMAC scores",
                    "PT records",
                    "Injection records with response",
                    "Medication history",
                    "HbA1c if diabetic",
                    "BMI documented",
                    "Preoperative clearance if comorbidities",
                ],
                "common_denial_reasons": [
                    "Non-weight-bearing radiographs",
                    "No functional outcome score",
                    "HbA1c ≥8.0 not optimized",
                    "EviCore peer-to-peer not completed — Cigna uses EviCore for joint replacement",
                    "Less than 3 months conservative care",
                ],
                "approval_tips": [
                    "Cigna routes TKA through EviCore — prepare for potential P2P requirement",
                    "Submit through EviCore portal for fastest processing",
                    "Include bilateral weight-bearing radiographs for comparison",
                    "Document knee alignment (varus/valgus) and range of motion deficit",
                    "HbA1c documentation is critical — Cigna will delay or deny if missing for diabetic patients",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 52,
            },

            "total_hip_replacement": {
                "policy_number": "MCP 0218",
                "policy_name": "Total Hip Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative care",
                    "Radiographic evidence of severe OA (KL Grade III-IV) or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Harris Hip Score <60 or HOOS documenting significant limitation",
                    "Trial of corticosteroid injection or documented contraindication",
                    "HbA1c <8.0 for diabetic patients",
                    "Preoperative medical optimization",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "PT records",
                    "Injection records",
                    "Medication history",
                    "HbA1c if diabetic",
                    "Medical clearance if needed",
                ],
                "common_denial_reasons": [
                    "Mild radiographic changes (KL Grade I-II)",
                    "No functional score documented",
                    "EviCore P2P not completed",
                    "HbA1c not optimized",
                ],
                "approval_tips": [
                    "Submit through EviCore portal and monitor for P2P request",
                    "Harris Hip Score <50 strengthens the case significantly",
                    "For AVN, include MRI with Ficat staging and progression documentation",
                    "Document impact on ambulation, sleep, and activities of daily living",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 55,
            },

            "acl_reconstruction": {
                "policy_number": "MCP 0240",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "MRI confirming complete ACL tear",
                    "Functional instability with documented giving way events",
                    "Positive Lachman and/or pivot shift test",
                    "Pre-habilitation PT (minimum 2–4 weeks) to restore ROM and reduce swelling",
                    "Active patient with functional demands",
                    "For partial tears: documented persistent instability despite bracing and rehabilitation",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear",
                    "Physical examination findings (Lachman, anterior drawer, pivot shift)",
                    "Documentation of instability episodes",
                    "Pre-hab PT records",
                    "Activity level and functional demands",
                    "Graft choice rationale",
                ],
                "common_denial_reasons": [
                    "Partial tear without instability",
                    "No examination findings documenting laxity",
                    "No pre-hab PT documentation",
                    "EviCore P2P not completed (less common for ACL)",
                ],
                "approval_tips": [
                    "Cigna/EviCore generally approves ACL reconstruction readily for complete tears",
                    "Document concomitant meniscal injury — it strengthens the indication",
                    "Include KT-1000 if available for objective laxity measurement",
                    "For patients >40, document high activity demands and functional goals",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 65,
            },

            "rotator_cuff_repair": {
                "policy_number": "MCP 0252",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "MRI demonstrating full-thickness tear or high-grade partial tear (>50%)",
                    "Failed minimum 6 weeks of conservative care (PT, NSAIDs, subacromial injection)",
                    "Acute traumatic tear may bypass conservative care requirement",
                    "ASES or DASH score documenting functional impairment",
                    "Tear is reparable based on MRI assessment (retraction, muscle quality)",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "PT records (minimum 6 weeks)",
                    "Injection records with response",
                    "Physical examination with strength testing",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% without failed conservative care",
                    "No functional score documented",
                    "EviCore P2P not completed — Cigna uses EviCore for shoulder surgery",
                    "Irreparable tear on MRI without documentation of repair attempt rationale",
                ],
                "approval_tips": [
                    "Cigna routes shoulder surgery through EviCore — prepare for P2P",
                    "ASES score <60 strengthens the case",
                    "For acute traumatic tears, document mechanism and date clearly",
                    "Include tear dimensions (AP and ML) from MRI report",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 58,
            },

            "carpal_tunnel_release": {
                "policy_number": "MCP 0260",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Failed minimum 6 weeks of conservative treatment (splinting, NSAIDs, activity modification)",
                    "Positive Phalen and/or Tinel test",
                    "Injection trial with documented response (recommended but not mandatory for severe EMG)",
                    "Thenar atrophy or constant numbness may expedite approval",
                ],
                "required_documentation": [
                    "EMG/NCS within 12 months",
                    "Physical examination findings",
                    "Conservative treatment records (6 weeks)",
                    "Injection records if applicable",
                    "Functional impact statement",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS obtained",
                    "Conservative treatment less than 6 weeks",
                    "EMG showing only mild changes without failed conservative care",
                ],
                "approval_tips": [
                    "Cigna requires 6 weeks conservative care (vs. Aetna's 4 weeks)",
                    "Severe EMG findings with thenar atrophy may bypass injection requirement",
                    "Document specific work and ADL limitations",
                    "Submit through EviCore portal if required by the specific plan",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 70,
            },

            "shoulder_arthroscopy": {
                "policy_number": "MCP 0252",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "MRI demonstrating intra-articular pathology (labral tear, loose bodies, synovitis)",
                    "Failed minimum 6 weeks of conservative care",
                    "Mechanical symptoms (locking, catching, clicking) documented",
                    "Positive provocative tests on exam",
                    "For instability: recurrent dislocations or subluxations documented",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination with provocative tests",
                    "PT records (6 weeks)",
                    "Documentation of mechanical symptoms or instability events",
                    "Operative plan with procedures listed",
                ],
                "common_denial_reasons": [
                    "No MRI before surgical request",
                    "EviCore P2P not completed in time",
                    "No mechanical symptoms — pain alone insufficient",
                    "Diagnostic arthroscopy without MRI evidence",
                ],
                "approval_tips": [
                    "EviCore commonly requests P2P for shoulder arthroscopy — schedule immediately",
                    "MRI arthrogram is preferred for labral pathology",
                    "Document instability events with dates and circumstances",
                    "Reference Cigna MCP 0252 and EviCore Shoulder Surgery Guidelines",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "neuropsychological_testing": {
                "policy_number": "MCP 0320",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Documented TBI or neurological condition with persistent cognitive deficits",
                    "Screening assessment showing cognitive impairment (MOCA <26)",
                    "Testing to address specific clinical question (treatment planning, RTW, capacity)",
                    "No testing within 12 months unless significant clinical change",
                    "Referral from neurologist, neurosurgeon, or physiatrist",
                    "Maximum 8 hours of testing",
                ],
                "required_documentation": [
                    "Documentation of TBI or neurological condition",
                    "Screening cognitive test results",
                    "Clinical question for testing",
                    "Referral letter",
                    "Estimated testing hours and CPT codes",
                ],
                "common_denial_reasons": [
                    "Repeat testing within 12 months",
                    "No screening showing cognitive impairment",
                    "Testing purpose not clearly stated",
                    "Exceeds 8-hour limit without justification",
                ],
                "approval_tips": [
                    "Cigna uses 8-hour limit like UHC — justify additional hours with case complexity",
                    "State the clinical question explicitly — how will results change management?",
                    "Include MOCA score to objectively demonstrate need",
                    "If repeat testing, document specific interval changes in function",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 45,
            },

            "cognitive_rehabilitation": {
                "policy_number": "MCP 0320",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI with objective cognitive deficits on neuropsychological testing",
                    "Neuropsychological testing within 12 months recommending cognitive rehabilitation",
                    "Specific measurable treatment goals established",
                    "Licensed SLP, OT, or neuropsychologist provider",
                    "Initial 12 sessions authorized; extensions require documented progress",
                    "Patient demonstrates rehabilitation potential",
                ],
                "required_documentation": [
                    "Neuropsychological testing report with rehab recommendations",
                    "Treatment plan with measurable goals",
                    "Provider credentials",
                    "Progress notes for extensions",
                    "Functional outcome measures (FIM, MPAI)",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing supporting need",
                    "Goals not specific or measurable",
                    "No documented progress for extension request",
                    "Provider not appropriately credentialed",
                ],
                "approval_tips": [
                    "Set SMART goals for each cognitive domain targeted",
                    "Track progress quantitatively with standardized measures at each session",
                    "EviCore may be involved for some Cigna plans — verify routing",
                    "Tie goals to functional outcomes — return-to-work or return-to-school",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 38,
            },
        },
    },

    # ======================================================================
    #  5. HUMANA
    # ======================================================================
    "humana": {
        "name": "Humana",
        "type": "commercial",
        "source": "Humana Medical Coverage Policies & Value-Based Care Guidelines",
        "pa_portal": "Availity.com or Humana Provider Portal",
        "phone": "1-800-448-6262",
        "avg_p2p_wait_days": 5,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "HUM-MCP-0145",
                "policy_name": "Lumbar Spinal Fusion",
                "criteria": [
                    "Failed minimum 6 months of conservative treatment (PT, medications, injections, activity modification)",
                    "MRI or CT demonstrating structural pathology correlating with symptoms",
                    "Documented spinal instability on flexion-extension radiographs or spondylolisthesis Grade I+",
                    "ODI ≥40 or equivalent validated functional measure",
                    "BMI <40 or documented weight management and bariatric evaluation if ≥40",
                    "Tobacco cessation documented — active smokers require cessation program enrollment ≥4 weeks",
                    "Psychological evaluation recommended for chronic pain >6 months",
                    "At least 2 epidural or facet injections with documented response",
                    "PT minimum 12 sessions over 6 weeks with documented outcomes",
                    "Patient outcome data from prior surgeries if applicable (value-based metric)",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "Flexion-extension radiographs",
                    "PT records with outcomes per session",
                    "Medication history with response",
                    "Injection records with response",
                    "ODI and VAS scores",
                    "Operative plan with levels and approach",
                    "H&P within 30 days",
                    "BMI and tobacco documentation",
                    "Psychological evaluation if chronic pain >6 months",
                ],
                "common_denial_reasons": [
                    "Conservative care less than 6 months — Humana mirrors UHC on duration requirement",
                    "No ODI or functional scores documented",
                    "BMI ≥40 without weight management documentation",
                    "Active tobacco use without cessation program",
                    "Missing outcome data from prior spine surgeries (value-based requirement)",
                ],
                "approval_tips": [
                    "Humana emphasizes value-based outcomes — include outcome data from any prior spine surgery",
                    "Humana mirrors UHC in many spine criteria but adds outcome tracking requirements",
                    "Include patient satisfaction scores from prior procedures if available",
                    "Reference Humana MCP HUM-MCP-0145 in the narrative",
                    "Document expected outcomes and post-op rehabilitation plan — Humana values this",
                ],
                "avg_decision_days": 15,
                "appeal_success_rate": 43,
            },

            "lumbar_decompression": {
                "policy_number": "HUM-MCP-0145",
                "policy_name": "Lumbar Decompression",
                "criteria": [
                    "Failed minimum 6 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI demonstrating neural compression correlating with clinical symptoms",
                    "Radiculopathy or neurogenic claudication with appropriate dermatomal correlation",
                    "Neurological examination findings documented",
                    "VAS leg ≥5 or equivalent pain severity measure",
                    "Prior outcome data from any previous spine surgery (value-based)",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination",
                    "PT records (6 weeks)",
                    "VAS scores (back and leg separately)",
                    "Medication trial records",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Imaging does not correlate with symptoms",
                    "Conservative care less than 6 weeks",
                    "No separate VAS leg score documented",
                    "No neurological exam in submission",
                ],
                "approval_tips": [
                    "Document VAS leg score separately — Humana uses this as a key metric",
                    "Include walking tolerance for stenosis",
                    "Reference HUM-MCP-0145 in the narrative",
                    "Include outcome data from prior surgeries if applicable",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "cervical_fusion_acdf": {
                "policy_number": "HUM-MCP-0148",
                "policy_name": "Cervical Fusion / ACDF",
                "criteria": [
                    "Failed minimum 6 weeks of conservative treatment unless myelopathy present",
                    "MRI showing disc herniation or stenosis with cord or root compression",
                    "Radiculopathy or myelopathy correlating with imaging",
                    "NDI ≥30 or mJOA documented for myelopathy",
                    "BMI <40 or documented justification if ≥40",
                    "Tobacco screening with cessation enrollment if active smoker",
                    "Maximum 3 levels without additional justification",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI and/or mJOA score",
                    "Conservative treatment records",
                    "Operative plan with levels",
                    "BMI and tobacco status",
                ],
                "common_denial_reasons": [
                    "No NDI or mJOA score",
                    "Conservative care less than 6 weeks without documented myelopathy",
                    "Active tobacco use without cessation",
                    "BMI ≥40 without documentation",
                ],
                "approval_tips": [
                    "Reference HUM-MCP-0148 in the narrative",
                    "Humana criteria are similar to UHC for cervical fusion — same tips apply",
                    "For myelopathy, document progression timeline and functional decline",
                    "Include outcome expectations and post-op plan — Humana values this for their VBC metrics",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 48,
            },

            "cervical_decompression": {
                "policy_number": "HUM-MCP-0148",
                "policy_name": "Cervical Decompression",
                "criteria": [
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Failed 6 weeks of conservative treatment unless myelopathy",
                    "Clinical myelopathy or radiculopathy with imaging correlation",
                    "NDI ≥30 or mJOA <14",
                    "Neurological examination documenting deficits",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI and/or mJOA score",
                    "Conservative treatment records",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No functional scores documented",
                    "Imaging does not show significant compression",
                    "Conservative care not documented for non-myelopathy cases",
                ],
                "approval_tips": [
                    "Reference HUM-MCP-0148 in the narrative",
                    "mJOA <12 strongly supports approval",
                    "Document gait assessment and hand function deficits for myelopathy",
                    "Include timeline showing progression of symptoms",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 50,
            },

            "spinal_cord_stimulator": {
                "policy_number": "HUM-MCP-0190",
                "policy_name": "Spinal Cord Stimulation",
                "criteria": [
                    "Chronic neuropathic pain ≥6 months (FBSS, CRPS, peripheral neuropathy)",
                    "Failed minimum 6 months of comprehensive conservative management",
                    "Successful SCS trial ≥5 days with ≥50% pain reduction on VAS",
                    "Psychological evaluation within 6 months clearing patient",
                    "Negative urine drug screen within 30 days",
                    "No active substance use disorder",
                    "Not a candidate for further corrective surgery",
                    "ODI score documented pre- and post-trial",
                    "Opioid consumption data pre- and during trial (value-based metric)",
                ],
                "required_documentation": [
                    "SCS trial report with daily VAS and activity logs",
                    "Psychological evaluation report",
                    "Urine drug screen",
                    "Pain management history",
                    "MRI/imaging",
                    "PT records",
                    "ODI pre- and post-trial",
                    "Opioid consumption records",
                ],
                "common_denial_reasons": [
                    "Trial did not show ≥50% pain reduction",
                    "No psychological evaluation or evaluation too old",
                    "Positive UDS",
                    "No opioid consumption data (Humana tracks this for VBC)",
                    "Conservative care less than 6 months",
                ],
                "approval_tips": [
                    "Humana is particularly interested in opioid reduction — document MED (morphine equivalent dose) before and during trial",
                    "Include daily activity improvement data from the trial",
                    "Reference HUM-MCP-0190 in the narrative",
                    "ODI change from pre- to post-trial is a strong approval indicator",
                    "Document expected post-implant outcome targets — Humana values measurable goals",
                ],
                "avg_decision_days": 20,
                "appeal_success_rate": 33,
            },

            "epidural_steroid_injection": {
                "policy_number": "HUM-MCP-0095",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "Radicular pain correlating with imaging pathology",
                    "Failed minimum 2 weeks of conservative treatment",
                    "Maximum 3 injections per region per 12-month period",
                    "Fluoroscopic guidance required for all injections",
                    "Documented response to prior injection before additional injection",
                    "Functional improvement documented, not just pain relief (value-based)",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Pain and functional assessment",
                    "Medication trial records",
                    "Prior injection response with VAS and functional data",
                    "Planned approach and level",
                ],
                "common_denial_reasons": [
                    "Exceeded 3 per region per year",
                    "No documented response to prior injection",
                    "No imaging correlation",
                    "Non-fluoroscopic technique",
                ],
                "approval_tips": [
                    "Document functional improvement (walking distance, work capacity) not just VAS change",
                    "Humana values outcome data — include patient-reported functional measures",
                    "Reference HUM-MCP-0095 in the submission",
                    "Include the time interval since last injection",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 65,
            },

            "total_knee_replacement": {
                "policy_number": "HUM-MCP-0210",
                "policy_name": "Total Knee Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, NSAIDs, injections)",
                    "Weight-bearing radiographs showing KL Grade III or IV OA",
                    "KOOS or WOMAC score documenting functional impairment",
                    "Trial of corticosteroid or viscosupplementation injection with documented response",
                    "BMI <40 or documented weight management if ≥40",
                    "HbA1c <8.0 for diabetics",
                    "Preoperative medical optimization",
                    "Surgical site infection risk assessment documented (value-based metric)",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "KOOS or WOMAC scores",
                    "PT records",
                    "Injection records with response",
                    "Medication history",
                    "HbA1c if diabetic",
                    "BMI documentation",
                    "Infection risk assessment (albumin, nutrition status)",
                ],
                "common_denial_reasons": [
                    "Non-weight-bearing radiographs",
                    "No functional score",
                    "HbA1c ≥8.0 not optimized",
                    "No infection risk assessment documentation (Humana VBC requirement)",
                    "Less than 3 months conservative care",
                ],
                "approval_tips": [
                    "Humana requires infection risk documentation — include albumin and nutritional status",
                    "Reference HUM-MCP-0210 in the narrative",
                    "Include preoperative optimization plan (DVT prophylaxis, PT plan, discharge plan)",
                    "Document expected outcome targets — Humana tracks TKA outcomes for VBC contracts",
                    "KOOS is preferred over WOMAC for Humana submissions",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "total_hip_replacement": {
                "policy_number": "HUM-MCP-0210",
                "policy_name": "Total Hip Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative care",
                    "Radiographic severe OA (KL Grade III-IV) or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Harris Hip Score <60 or HOOS documenting limitation",
                    "Injection trial or documented contraindication",
                    "HbA1c <8.0 for diabetics",
                    "Infection risk assessment documented",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "PT records",
                    "Injection records",
                    "Medication history",
                    "HbA1c if diabetic",
                    "Infection risk assessment (albumin, nutrition)",
                ],
                "common_denial_reasons": [
                    "Mild radiographic changes",
                    "No Harris Hip Score or HOOS",
                    "No infection risk assessment",
                    "HbA1c not optimized",
                ],
                "approval_tips": [
                    "Reference HUM-MCP-0210 in the narrative",
                    "Include preoperative optimization and discharge plan",
                    "Document expected post-op milestones (Humana VBC metric)",
                    "Harris Hip Score <50 is a strong indicator for approval",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 58,
            },

            "acl_reconstruction": {
                "policy_number": "HUM-MCP-0225",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "MRI confirming complete ACL tear",
                    "Functional instability with documented giving way events",
                    "Positive Lachman and/or pivot shift on examination",
                    "Pre-hab PT recommended (2–4 weeks)",
                    "Active patient with functional demands",
                    "Expected post-op rehabilitation plan documented (value-based)",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear",
                    "Physical examination findings",
                    "Instability episode documentation",
                    "Pre-hab PT records",
                    "Activity level and functional goals",
                    "Post-op rehabilitation plan",
                ],
                "common_denial_reasons": [
                    "Partial tear without instability",
                    "No examination findings documented",
                    "No post-op rehabilitation plan submitted (Humana requirement)",
                ],
                "approval_tips": [
                    "Humana requires post-op rehabilitation plan with the PA submission — unique requirement",
                    "Reference HUM-MCP-0225 in the narrative",
                    "Document expected return-to-activity timeline",
                    "Include concomitant meniscal or cartilage injury",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 63,
            },

            "rotator_cuff_repair": {
                "policy_number": "HUM-MCP-0230",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "MRI confirming full-thickness or high-grade partial tear (>50%)",
                    "Failed minimum 6 weeks of conservative care (PT, NSAIDs, injection)",
                    "Acute traumatic tear may bypass conservative care",
                    "ASES or DASH score documenting impairment",
                    "Post-operative rehabilitation plan documented (value-based)",
                    "Tear is reparable based on MRI (retraction and muscle quality assessed)",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "PT records",
                    "Injection records with response",
                    "Physical examination",
                    "Operative and post-op rehab plan",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% without failed conservative care",
                    "No functional score",
                    "No post-op rehabilitation plan (Humana VBC requirement)",
                    "Irreparable tear without justification for attempt",
                ],
                "approval_tips": [
                    "Include post-op rehabilitation plan with expected milestones — Humana tracks this",
                    "Reference HUM-MCP-0230 in the narrative",
                    "ASES <60 with full-thickness tear is generally approved",
                    "Document expected return-to-function timeline",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 60,
            },

            "carpal_tunnel_release": {
                "policy_number": "HUM-MCP-0240",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Failed minimum 6 weeks of conservative treatment (splinting, NSAIDs)",
                    "Positive Phalen and/or Tinel test",
                    "Injection trial documented with response",
                    "Thenar atrophy or severe EMG may expedite approval",
                    "Functional impact on work or ADLs documented",
                ],
                "required_documentation": [
                    "EMG/NCS within 12 months",
                    "Physical examination findings",
                    "Conservative treatment records",
                    "Injection record with response",
                    "Functional impact statement",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS obtained",
                    "Conservative care less than 6 weeks",
                    "No injection trial documented",
                    "EMG mild without additional justification",
                ],
                "approval_tips": [
                    "Humana requires injection trial (unlike Aetna) — document it",
                    "Reference HUM-MCP-0240 in the narrative",
                    "Include specific occupational impact for work-related impairment",
                    "Document grip and pinch strength if measured",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 70,
            },

            "shoulder_arthroscopy": {
                "policy_number": "HUM-MCP-0230",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "MRI demonstrating intra-articular pathology",
                    "Failed minimum 6 weeks of conservative care",
                    "Mechanical symptoms documented (locking, catching)",
                    "Positive provocative tests on examination",
                    "For instability: recurrent dislocation/subluxation events documented",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination with provocative tests",
                    "PT records (6 weeks)",
                    "Documentation of mechanical symptoms or instability events",
                    "Operative plan",
                    "Post-op rehabilitation plan (value-based)",
                ],
                "common_denial_reasons": [
                    "No MRI before request",
                    "No mechanical symptoms — pain alone insufficient",
                    "No post-op rehabilitation plan submitted",
                    "Diagnostic arthroscopy without MRI pathology",
                ],
                "approval_tips": [
                    "Include post-op rehabilitation plan — Humana requires it for shoulder arthroscopy",
                    "MRI arthrogram preferred for labral pathology",
                    "Document specific instability events with dates",
                    "Reference HUM-MCP-0230 in the narrative",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 55,
            },

            "neuropsychological_testing": {
                "policy_number": "HUM-MCP-0300",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Documented TBI or neurological condition with persistent cognitive deficits",
                    "Screening cognitive assessment showing impairment",
                    "Testing to guide treatment or return-to-work decision",
                    "No testing within 12 months unless significant clinical change",
                    "Referral from treating neurologist, neurosurgeon, or physiatrist",
                    "Maximum 8 hours of testing per evaluation",
                ],
                "required_documentation": [
                    "Documentation of TBI or neurological event",
                    "Screening test results (MOCA, MMSE)",
                    "Clinical question for testing",
                    "Physician referral",
                    "Estimated hours and CPT codes",
                ],
                "common_denial_reasons": [
                    "Repeat testing within 12 months without clinical change",
                    "No screening test demonstrating impairment",
                    "Vague clinical question",
                    "Exceeds 8-hour maximum",
                ],
                "approval_tips": [
                    "Reference HUM-MCP-0300 in the narrative",
                    "State how results will change the treatment plan or work status",
                    "Include MOCA or equivalent screening score",
                    "Humana values outcome-driven testing — frame the request around functional decisions",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 47,
            },

            "cognitive_rehabilitation": {
                "policy_number": "HUM-MCP-0300",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI with cognitive deficits on neuropsychological testing",
                    "Testing within 12 months recommending rehabilitation",
                    "Measurable treatment goals with expected outcomes timeline",
                    "Licensed SLP, OT, or neuropsychologist provider",
                    "Initial 12 sessions; extensions require progress documentation",
                    "Improvement potential documented — not maintenance only",
                    "Outcome measures tracked at each session (value-based)",
                ],
                "required_documentation": [
                    "Neuropsychological testing report",
                    "Treatment plan with SMART goals and outcome timeline",
                    "Provider credentials",
                    "Progress notes for extensions",
                    "Functional outcome measures (FIM, MPAI) tracked per session",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing",
                    "Goals not SMART or not measurable",
                    "No session-by-session outcome tracking for extension",
                    "Maintenance therapy without improvement potential",
                ],
                "approval_tips": [
                    "Humana is the most outcome-focused payer — track progress quantitatively at every session",
                    "Include expected timeline for goal achievement",
                    "Reference HUM-MCP-0300 in the narrative",
                    "Tie goals to return-to-work, return-to-school, or independent living",
                    "Document patient engagement and compliance as a positive factor",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 40,
            },
        },
    },

    # ======================================================================
    #  6. EMBLEMHEALTH
    # ======================================================================
    "emblem_health": {
        "name": "EmblemHealth",
        "type": "commercial",
        "source": "EmblemHealth Medical Policy & Clinical Guidelines",
        "pa_portal": "EmblemHealth Provider Portal (emblemhealth.com/providers)",
        "phone": "1-877-842-3625",
        "avg_p2p_wait_days": 4,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "EH-MED-2023-045",
                "policy_name": "Lumbar Spinal Fusion",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment (PT, medications, injections)",
                    "MRI or CT demonstrating structural pathology at proposed level(s)",
                    "Documented instability on flexion-extension radiographs or spondylolisthesis",
                    "ODI ≥30 or equivalent functional impairment measure",
                    "At least 1 epidural steroid or facet injection with documented response",
                    "Physical therapy minimum 8 sessions",
                    "BMI <40 preferred but not mandatory with additional documentation",
                    "Tobacco status documented",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "PT records",
                    "Injection records with response",
                    "ODI score",
                    "Medication history",
                    "Operative plan",
                    "H&P within 30 days",
                ],
                "common_denial_reasons": [
                    "Conservative care less than 3 months",
                    "No ODI score included",
                    "No injection trial documented",
                    "Multi-level fusion without individual level justification",
                ],
                "approval_tips": [
                    "EmblemHealth is NY-focused and generally follows moderate criteria — 3 months conservative care",
                    "For WC cases, EmblemHealth often defers to NYS WCB MTG guidelines — cross-reference mtg_guidelines.py",
                    "Reference EH-MED-2023-045 in the narrative",
                    "Include ODI with every submission — it is EmblemHealth's primary functional measure",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 50,
            },

            "lumbar_decompression": {
                "policy_number": "EH-MED-2023-045",
                "policy_name": "Lumbar Decompression",
                "criteria": [
                    "Failed minimum 4 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI demonstrating neural compression with clinical correlation",
                    "Radiculopathy or neurogenic claudication documented",
                    "Neurological examination findings",
                    "EMG/NCS if radiculopathy uncertain",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination",
                    "PT records",
                    "Medication history",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No imaging correlation to symptoms",
                    "Conservative care less than 4 weeks without progressive deficit",
                    "No neurological exam findings",
                ],
                "approval_tips": [
                    "EmblemHealth approves decompression more readily than fusion",
                    "Reference EH-MED-2023-045 in the narrative",
                    "Document dermatomal correlation clearly",
                    "For WC cases, cite NYS WCB MTG alongside EmblemHealth policy",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 58,
            },

            "cervical_fusion_acdf": {
                "policy_number": "EH-MED-2023-048",
                "policy_name": "Cervical Fusion / ACDF",
                "criteria": [
                    "Failed minimum 4 weeks of conservative care unless myelopathy",
                    "MRI showing disc herniation or stenosis with cord or root compression",
                    "Radiculopathy or myelopathy with imaging correlation",
                    "NDI ≥30 documented",
                    "Maximum 3 levels for ACDF without additional justification",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI score",
                    "Conservative treatment records",
                    "Operative plan with levels",
                ],
                "common_denial_reasons": [
                    "No NDI score",
                    "Conservative care less than 4 weeks without myelopathy",
                    "Imaging does not show compression",
                ],
                "approval_tips": [
                    "Reference EH-MED-2023-048 in the narrative",
                    "EmblemHealth follows moderate criteria similar to BCBS for cervical fusion",
                    "For myelopathy, document upper motor neuron signs explicitly",
                    "Include mJOA alongside NDI for myelopathy cases",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 52,
            },

            "cervical_decompression": {
                "policy_number": "EH-MED-2023-048",
                "policy_name": "Cervical Decompression",
                "criteria": [
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Failed 4 weeks conservative treatment unless myelopathy",
                    "Neurological examination with documented deficits",
                    "NDI ≥30 or mJOA <14",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI and/or mJOA score",
                    "Conservative treatment records",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No functional scores",
                    "No imaging showing compression",
                    "Conservative care not documented for non-myelopathy",
                ],
                "approval_tips": [
                    "Reference EH-MED-2023-048 in the narrative",
                    "EmblemHealth approves cervical decompression for myelopathy readily",
                    "Document gait, hand function, and upper motor neuron signs",
                    "Include CT for bony pathology cases",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "spinal_cord_stimulator": {
                "policy_number": "EH-MED-2023-062",
                "policy_name": "Spinal Cord Stimulation",
                "criteria": [
                    "Chronic neuropathic pain ≥6 months (FBSS, CRPS, chronic neuropathic pain)",
                    "Failed minimum 6 months of conservative management",
                    "Successful SCS trial ≥3 days with ≥50% pain reduction",
                    "Psychological evaluation within 12 months",
                    "No active substance use disorder",
                    "Not a candidate for further corrective surgery",
                ],
                "required_documentation": [
                    "SCS trial report with pain scores",
                    "Psychological evaluation",
                    "Urine drug screen",
                    "Pain management history",
                    "MRI/imaging",
                    "PT records",
                ],
                "common_denial_reasons": [
                    "Trial did not show ≥50% improvement",
                    "No psychological evaluation",
                    "Active substance use concern",
                    "Conservative care less than 6 months",
                ],
                "approval_tips": [
                    "EmblemHealth allows 12-month window for psych eval and 3-day minimum trial — more flexible than UHC/Humana",
                    "Reference EH-MED-2023-062 in the narrative",
                    "Include functional data from the trial (not just pain scores)",
                    "Document all prior surgical and interventional treatments",
                ],
                "avg_decision_days": 18,
                "appeal_success_rate": 35,
            },

            "epidural_steroid_injection": {
                "policy_number": "EH-MED-2023-050",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "Radicular pain with imaging correlation",
                    "Failed initial conservative treatment (medications, PT)",
                    "Maximum 3 injections per region per 12-month period",
                    "Fluoroscopic guidance required",
                    "Prior injection response documented for subsequent injections",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Pain description",
                    "Medication trial records",
                    "Prior injection response if applicable",
                    "Planned approach and level",
                ],
                "common_denial_reasons": [
                    "Exceeded 3 per region per year",
                    "No imaging correlation",
                    "No response documentation for prior injection",
                ],
                "approval_tips": [
                    "Reference EH-MED-2023-050 in the submission",
                    "EmblemHealth follows standard 3-per-12-months guideline",
                    "Document response to each prior injection with VAS change and duration",
                    "Include functional improvement data",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 65,
            },

            "total_knee_replacement": {
                "policy_number": "EH-SURG-2023-030",
                "policy_name": "Total Knee Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative treatment",
                    "Weight-bearing radiographs showing KL Grade III or IV OA",
                    "KOOS or WOMAC score documenting functional impairment",
                    "Trial of corticosteroid injection",
                    "BMI <40 preferred with documentation if higher",
                    "HbA1c <8.0 for diabetics",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "KOOS or WOMAC scores",
                    "PT records",
                    "Injection records",
                    "Medication history",
                    "HbA1c if diabetic",
                ],
                "common_denial_reasons": [
                    "Non-weight-bearing radiographs",
                    "No functional score",
                    "HbA1c ≥8.0",
                    "Insufficient conservative care",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-030 in the narrative",
                    "EmblemHealth follows moderate criteria similar to BCBS for TKA",
                    "Weight-bearing films are essential — always include",
                    "Document alignment and range of motion deficit",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 58,
            },

            "total_hip_replacement": {
                "policy_number": "EH-SURG-2023-030",
                "policy_name": "Total Hip Arthroplasty",
                "criteria": [
                    "Failed minimum 3 months of conservative care",
                    "Radiographic severe OA or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Harris Hip Score <60 or HOOS",
                    "Injection trial or contraindication documented",
                    "HbA1c <8.0 for diabetics",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "PT records",
                    "Injection records",
                    "HbA1c if diabetic",
                ],
                "common_denial_reasons": [
                    "Mild radiographic changes",
                    "No functional score",
                    "HbA1c not optimized",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-030 in the narrative",
                    "EmblemHealth approves THA readily with moderate-severe radiographic changes",
                    "Include both hips on AP pelvis for comparison",
                    "Document gait and functional limitations explicitly",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 62,
            },

            "acl_reconstruction": {
                "policy_number": "EH-SURG-2023-035",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "MRI confirming complete ACL tear",
                    "Functional instability with giving way episodes",
                    "Positive Lachman and/or pivot shift",
                    "Pre-hab PT recommended (2–4 weeks)",
                    "Active patient with functional demands",
                ],
                "required_documentation": [
                    "MRI confirming tear",
                    "Physical examination findings",
                    "Instability documentation",
                    "Pre-hab PT records",
                    "Activity level description",
                ],
                "common_denial_reasons": [
                    "Partial tear without instability",
                    "No examination findings",
                    "No documentation of functional instability",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-035 in the narrative",
                    "EmblemHealth generally approves ACL reconstruction readily",
                    "Document concomitant meniscal injury",
                    "Include pre-hab PT documentation",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 65,
            },

            "rotator_cuff_repair": {
                "policy_number": "EH-SURG-2023-038",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "MRI showing full-thickness or high-grade partial tear (>50%)",
                    "Failed 6 weeks of conservative care (PT, NSAIDs, injection)",
                    "Acute traumatic tear may bypass conservative care",
                    "ASES or DASH score documenting impairment",
                    "Reparable tear on MRI assessment",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "PT records",
                    "Injection records",
                    "Physical examination",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Partial tear <50% without failed conservative care",
                    "No functional score",
                    "Less than 6 weeks PT",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-038 in the narrative",
                    "EmblemHealth follows standard criteria for rotator cuff — ASES is the key score",
                    "Document tear size and location from MRI",
                    "For acute tears, document date of injury and mechanism",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 62,
            },

            "carpal_tunnel_release": {
                "policy_number": "EH-SURG-2023-040",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Failed minimum 4 weeks of conservative treatment (splinting, NSAIDs)",
                    "Positive Phalen and/or Tinel test",
                    "Injection trial recommended",
                    "Thenar atrophy may expedite without full conservative care",
                ],
                "required_documentation": [
                    "EMG/NCS within 12 months",
                    "Physical examination",
                    "Conservative treatment records",
                    "Functional impact statement",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS",
                    "Conservative care less than 4 weeks",
                    "EMG showing only mild CTS without additional justification",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-040 in the narrative",
                    "EmblemHealth requires only 4 weeks conservative care — less strict than UHC/Cigna",
                    "Document occupational impact especially for NY workers",
                    "Bilateral requests can be submitted together",
                ],
                "avg_decision_days": 5,
                "appeal_success_rate": 72,
            },

            "shoulder_arthroscopy": {
                "policy_number": "EH-SURG-2023-038",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "MRI showing intra-articular pathology",
                    "Failed 6 weeks of conservative care",
                    "Mechanical symptoms documented",
                    "Positive provocative tests",
                    "Recurrent instability events for labral repair indication",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination",
                    "PT records",
                    "Documentation of mechanical symptoms or instability",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "No MRI obtained",
                    "No mechanical symptoms documented",
                    "Diagnostic-only arthroscopy without MRI findings",
                ],
                "approval_tips": [
                    "Reference EH-SURG-2023-038 in the narrative",
                    "MRI arthrogram preferred for labral pathology",
                    "Document instability events with specific dates and descriptions",
                    "List all planned arthroscopic procedures",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 58,
            },

            "neuropsychological_testing": {
                "policy_number": "EH-MED-2023-070",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Documented TBI or neurological condition with cognitive complaints >3 months",
                    "Screening showing cognitive impairment (MOCA <26)",
                    "Testing to guide treatment or return-to-work/school decisions",
                    "No testing within 12 months unless clinical change",
                    "Physician referral required",
                    "Maximum 10 hours of testing",
                ],
                "required_documentation": [
                    "Documentation of TBI or neurological event",
                    "Screening test results",
                    "Clinical question for testing",
                    "Physician referral",
                    "Estimated hours and CPT codes",
                ],
                "common_denial_reasons": [
                    "Repeat testing within 12 months",
                    "No screening test showing impairment",
                    "Vague referral question",
                    "Exceeds 10-hour maximum",
                ],
                "approval_tips": [
                    "Reference EH-MED-2023-070 in the narrative",
                    "EmblemHealth allows 10 hours — middle of the range",
                    "State clinical question clearly",
                    "Include MOCA score",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 48,
            },

            "cognitive_rehabilitation": {
                "policy_number": "EH-MED-2023-070",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Documented TBI with cognitive deficits on neuropsychological testing",
                    "Testing within 12 months recommending rehab",
                    "Measurable treatment goals",
                    "Licensed SLP, OT, or neuropsychologist",
                    "Initial 12 sessions with extension based on progress",
                    "Improvement potential documented",
                ],
                "required_documentation": [
                    "Neuropsychological testing report",
                    "Treatment plan with goals",
                    "Provider credentials",
                    "Progress notes for extensions",
                    "Functional outcome measures",
                ],
                "common_denial_reasons": [
                    "No neuropsychological testing",
                    "Vague goals",
                    "No progress for extension",
                    "Maintenance therapy only",
                ],
                "approval_tips": [
                    "Reference EH-MED-2023-070 in the narrative",
                    "EmblemHealth follows standard cognitive rehab criteria",
                    "Set measurable goals with timeline",
                    "Track progress quantitatively",
                ],
                "avg_decision_days": 8,
                "appeal_success_rate": 44,
            },
        },
    },

    # ======================================================================
    #  7. MEDICARE (Novitas Solutions / NGS — NY MAC)
    # ======================================================================
    "medicare": {
        "name": "Medicare (CMS)",
        "type": "government",
        "source": "CMS National Coverage Determinations (NCDs), Local Coverage Determinations (LCDs) — Novitas Solutions (MAC J-L) / NGS",
        "pa_portal": "Medicare Administrative Contractor portal (Novitas or NGS) — most procedures do not require prior auth",
        "phone": "Novitas: 1-855-252-8782 | NGS: 1-888-802-3898",
        "avg_p2p_wait_days": 0,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "LCD L35076 / NCD 150.1",
                "policy_name": "Lumbar Spinal Fusion",
                "criteria": [
                    "Medicare does not require prior authorization for lumbar fusion in most cases",
                    "Coverage based on medical necessity per LCD L35076",
                    "Documented instability, spondylolisthesis, or DDD with failed conservative treatment",
                    "MRI or CT demonstrating pathology at the proposed level(s)",
                    "Conservative treatment for minimum 3 months (PT, medications, injections) unless acute instability",
                    "Functional impairment documented — ODI or equivalent",
                    "Smoking status documented (not mandatory for denial but documented for quality metrics)",
                    "No specific BMI cutoff but obesity-related risks should be documented",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "Flexion-extension radiographs if instability",
                    "PT records",
                    "Medication and injection history",
                    "ODI or functional measure",
                    "Operative plan with CPT codes and levels",
                    "Medical necessity statement",
                ],
                "common_denial_reasons": [
                    "Post-service audit finding insufficient documentation of medical necessity",
                    "Coding errors (wrong CPT code, missing modifier, incorrect diagnosis pairing)",
                    "Documentation does not support the number of levels fused",
                    "Insufficient conservative treatment documentation in the chart",
                ],
                "approval_tips": [
                    "Medicare pays first and audits later — documentation must be bulletproof for audit defense",
                    "Reference LCD L35076 in the operative report and documentation",
                    "Ensure CPT-ICD10 pairing is correct per LCD — incorrect pairing triggers automatic denial",
                    "Document medical necessity in the operative report, not just the H&P",
                    "Medicare does not limit BMI or mandate tobacco cessation — but document risk mitigation",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 55,
            },

            "lumbar_decompression": {
                "policy_number": "LCD L35076",
                "policy_name": "Lumbar Decompression (Laminectomy/Discectomy)",
                "criteria": [
                    "No prior authorization required — coverage based on medical necessity",
                    "MRI demonstrating disc herniation or stenosis with neural compression",
                    "Clinical correlation with imaging findings",
                    "Conservative treatment failure or progressive neurological deficit",
                    "Appropriate CPT-ICD10 code pairing per LCD L35076",
                ],
                "required_documentation": [
                    "MRI within reasonable timeframe",
                    "Neurological examination",
                    "Conservative treatment records if applicable",
                    "Operative report documenting findings and medical necessity",
                ],
                "common_denial_reasons": [
                    "Incorrect CPT-ICD10 code pairing on the claim",
                    "Post-service audit — documentation does not support procedure performed",
                    "Same-level same-provider repeat decompression without clear documentation of recurrence",
                ],
                "approval_tips": [
                    "Ensure operative report clearly documents the pathology found and decompression performed",
                    "Reference LCD L35076 criteria in documentation",
                    "CPT code selection must match the extent of decompression (laminotomy vs. laminectomy)",
                    "For stenosis with neurogenic claudication, document walking tolerance pre-operatively",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 65,
            },

            "cervical_fusion_acdf": {
                "policy_number": "LCD L35076",
                "policy_name": "Cervical Fusion / ACDF",
                "criteria": [
                    "No prior authorization required for most Medicare plans",
                    "MRI demonstrating disc herniation or stenosis with cord or root compression",
                    "Clinical correlation with radiculopathy or myelopathy",
                    "Conservative treatment failure unless myelopathy present",
                    "Appropriate CPT-ICD10 code pairing",
                    "Number of levels must be justified individually in documentation",
                ],
                "required_documentation": [
                    "MRI cervical spine",
                    "Neurological examination",
                    "Conservative treatment records",
                    "Operative report with level-by-level justification",
                    "NDI or functional measure",
                ],
                "common_denial_reasons": [
                    "Incorrect CPT coding for multi-level ACDF",
                    "Documentation does not support number of levels",
                    "Post-service audit finding insufficient medical necessity documentation",
                ],
                "approval_tips": [
                    "Multi-level ACDF coding is a common audit trigger — ensure add-on codes are correct",
                    "Document level-by-level justification in the operative report",
                    "Reference LCD L35076 in documentation",
                    "For myelopathy, document progression and physical examination findings",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 58,
            },

            "cervical_decompression": {
                "policy_number": "LCD L35076",
                "policy_name": "Cervical Decompression",
                "criteria": [
                    "No prior authorization required",
                    "MRI or CT demonstrating cervical stenosis with cord or root compression",
                    "Clinical myelopathy or radiculopathy",
                    "Conservative treatment failure unless myelopathy",
                    "Appropriate CPT coding",
                ],
                "required_documentation": [
                    "MRI or CT cervical spine",
                    "Neurological examination",
                    "Conservative treatment records",
                    "Operative report",
                ],
                "common_denial_reasons": [
                    "CPT coding errors",
                    "Documentation insufficient for number of levels",
                    "Post-service audit",
                ],
                "approval_tips": [
                    "Posterior cervical decompression coding (63001, 63015, 63045-63048) must match the extent of procedure",
                    "Reference LCD L35076 in documentation",
                    "Document intraoperative findings in the operative report",
                    "For laminoplasty, ensure correct coding — this is commonly miscoded",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 60,
            },

            "spinal_cord_stimulator": {
                "policy_number": "NCD 160.7 / LCD L35936",
                "policy_name": "Spinal Cord Stimulation",
                "criteria": [
                    "Prior authorization may be required under Medicare Prior Authorization Model for certain DME MACs",
                    "Chronic pain of at least 3 months duration",
                    "Pain is the result of a documented condition (FBSS, CRPS, arachnoiditis)",
                    "Other treatment modalities have been tried and failed",
                    "Successful trial stimulation with documented pain relief",
                    "Psychological evaluation completed",
                    "No contraindications to implant",
                    "Patient is an appropriate surgical candidate",
                ],
                "required_documentation": [
                    "SCS trial report with outcomes",
                    "Psychological evaluation",
                    "Pain management history",
                    "MRI/imaging",
                    "Documentation of failed treatments",
                    "Medical necessity statement referencing NCD 160.7",
                ],
                "common_denial_reasons": [
                    "Trial stimulation did not demonstrate adequate pain relief",
                    "Psychological evaluation not completed",
                    "Diagnosis not covered under NCD 160.7 (e.g., axial back pain without neuropathic component)",
                    "Documentation does not reference NCD criteria",
                ],
                "approval_tips": [
                    "NCD 160.7 is narrow — ensure the diagnosis falls within covered indications",
                    "Reference NCD 160.7 AND LCD L35936 in all documentation",
                    "Medicare coverage for SCS is limited to specific neuropathic pain conditions — axial back pain alone is typically not covered",
                    "Trial data must clearly demonstrate benefit",
                    "Some Medicare Advantage plans require prior auth — verify with the specific MA plan",
                ],
                "avg_decision_days": 14,
                "appeal_success_rate": 40,
            },

            "epidural_steroid_injection": {
                "policy_number": "LCD L35937",
                "policy_name": "Epidural Steroid Injections",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "Radicular pain with imaging correlation",
                    "Conservative treatment attempted",
                    "Fluoroscopic or CT guidance required for coverage",
                    "Maximum frequency per LCD guidelines — typically 3 per region per year",
                    "Appropriate CPT coding for approach (transforaminal vs. interlaminar) and level",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Clinical notes documenting radicular symptoms",
                    "Fluoroscopic guidance documentation",
                    "Response to prior injections if applicable",
                ],
                "common_denial_reasons": [
                    "Incorrect CPT coding (transforaminal vs. interlaminar coding confusion)",
                    "No documentation of fluoroscopic guidance",
                    "Frequency exceeds LCD guidelines",
                    "Post-service audit — documentation does not support medical necessity",
                ],
                "approval_tips": [
                    "CPT coding for ESI is a top audit target — ensure correct code for approach and level",
                    "64483 (transforaminal lumbar) vs. 62322/62323 (interlaminar) — never use wrong code",
                    "Document fluoroscopic guidance in the procedure note explicitly",
                    "Reference LCD L35937 in documentation",
                    "Medicare Advantage plans may require PA — verify with specific plan",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 60,
            },

            "total_knee_replacement": {
                "policy_number": "CMS-1588-IFC / NCD none (covered by statute)",
                "policy_name": "Total Knee Arthroplasty",
                "criteria": [
                    "No prior authorization required for original Medicare (removed from PA list in 2024)",
                    "Medical necessity based on documented severe knee arthritis with functional impairment",
                    "Radiographic evidence of OA (weight-bearing preferred)",
                    "Conservative treatment failure documented",
                    "Appropriate CPT coding (27447 for primary TKA)",
                    "CMS Comprehensive Care for Joint Replacement (CJR) bundled payment model may apply",
                ],
                "required_documentation": [
                    "Radiographs showing OA",
                    "Documentation of conservative treatment",
                    "Functional impairment documentation",
                    "Medical necessity in H&P and operative report",
                    "Post-operative plan (required under CJR model)",
                ],
                "common_denial_reasons": [
                    "Incorrect CPT or ICD-10 coding",
                    "Post-service audit finding insufficient documentation",
                    "Readmission within 90 days triggers CJR penalty (not denial but financial impact)",
                    "Outpatient vs. inpatient status determination (Medicare 2-midnight rule)",
                ],
                "approval_tips": [
                    "TKA was removed from the inpatient-only list — can be done as outpatient for Medicare",
                    "Under CJR model, document comprehensive care plan including rehab and discharge planning",
                    "Ensure inpatient admission meets 2-midnight rule or procedure is coded as outpatient",
                    "Medicare does not have BMI cutoff or tobacco requirement — but document comorbidities",
                    "Medicare Advantage plans may still require PA — verify with specific MA plan",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 60,
            },

            "total_hip_replacement": {
                "policy_number": "CMS-1588-IFC / NCD none (covered by statute)",
                "policy_name": "Total Hip Arthroplasty",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "Medical necessity for severe hip arthritis or AVN with functional impairment",
                    "Radiographic evidence of severe OA or AVN",
                    "Conservative treatment failure documented",
                    "Appropriate CPT coding (27130 for primary THA)",
                    "CJR bundled payment model may apply",
                ],
                "required_documentation": [
                    "AP pelvis and hip radiographs",
                    "Documentation of conservative treatment",
                    "Functional impairment documentation",
                    "Medical necessity in H&P and operative report",
                    "Post-operative and discharge plan",
                ],
                "common_denial_reasons": [
                    "Incorrect CPT/ICD-10 coding",
                    "Post-service documentation audit",
                    "Inpatient/outpatient status determination",
                    "CJR readmission penalty",
                ],
                "approval_tips": [
                    "THA removed from inpatient-only list — document rationale for inpatient vs. outpatient",
                    "CJR model requires comprehensive discharge and post-acute care planning",
                    "No BMI cutoff or tobacco requirement for Medicare",
                    "Medicare Advantage plans may require PA — verify with the MA plan",
                    "Document approach (anterior vs. posterior) and rationale",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 62,
            },

            "acl_reconstruction": {
                "policy_number": "LCD varies by MAC",
                "policy_name": "ACL Reconstruction",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "MRI confirming ACL tear",
                    "Functional instability documented",
                    "Medical necessity documented in H&P",
                    "Appropriate CPT coding (29888)",
                    "Age and activity level considerations documented (Medicare population is typically >65)",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear",
                    "Physical examination findings",
                    "Documentation of instability and functional demands",
                    "Medical necessity statement",
                    "Operative plan",
                ],
                "common_denial_reasons": [
                    "Post-service audit questioning medical necessity in elderly patient",
                    "Incorrect CPT coding",
                    "Insufficient documentation of functional demands in Medicare-age patient",
                ],
                "approval_tips": [
                    "ACL reconstruction in Medicare patients (>65) requires strong functional justification",
                    "Document specific high-demand activities and why stability is needed",
                    "Consider documenting why non-operative management is not appropriate for this patient",
                    "Medicare does not require PA but will audit — document thoroughly",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 55,
            },

            "rotator_cuff_repair": {
                "policy_number": "LCD varies by MAC",
                "policy_name": "Rotator Cuff Repair",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "MRI documenting rotator cuff tear",
                    "Failed conservative treatment or acute traumatic tear",
                    "Medical necessity documented",
                    "Appropriate CPT coding (29827 arthroscopic, 23412 open)",
                    "Tear reparability documented on MRI",
                ],
                "required_documentation": [
                    "MRI shoulder",
                    "Physical examination with strength testing",
                    "Conservative treatment records or trauma documentation",
                    "Operative plan",
                    "Medical necessity statement",
                ],
                "common_denial_reasons": [
                    "Post-service audit — documentation does not support medical necessity",
                    "CPT coding errors (arthroscopic vs. open, single vs. multiple tendon)",
                    "Repair attempted on irreparable tear — documentation must address reparability",
                ],
                "approval_tips": [
                    "Medicare pays well for rotator cuff repair — ensure documentation is audit-proof",
                    "Document tear size, number of tendons, and reparability assessment",
                    "CPT 29827 (arthroscopic) vs. 23412 (open) must match the procedure performed",
                    "For massive tears, document why repair was attempted vs. reverse arthroplasty",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 58,
            },

            "carpal_tunnel_release": {
                "policy_number": "LCD varies by MAC",
                "policy_name": "Carpal Tunnel Release",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "EMG/NCS confirming median neuropathy recommended by most MACs",
                    "Clinical CTS with positive provocative tests",
                    "Conservative treatment failure",
                    "Medical necessity documented",
                    "Appropriate CPT coding (64721 open, 29848 endoscopic)",
                ],
                "required_documentation": [
                    "EMG/NCS report",
                    "Physical examination",
                    "Conservative treatment records",
                    "Medical necessity statement",
                ],
                "common_denial_reasons": [
                    "No EMG/NCS in the chart — most MACs require it",
                    "Incorrect CPT coding (open vs. endoscopic)",
                    "Post-service audit finding insufficient documentation",
                ],
                "approval_tips": [
                    "Most MACs require EMG/NCS even though there is no national requirement",
                    "Document the EMG/NCS results in your operative report for audit defense",
                    "Medicare does not limit by conservative care duration but document treatment history",
                    "Bilateral same-day CTR is covered with appropriate modifier (bilateral modifier -50)",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 70,
            },

            "shoulder_arthroscopy": {
                "policy_number": "LCD varies by MAC",
                "policy_name": "Shoulder Arthroscopy",
                "criteria": [
                    "No prior authorization required for original Medicare",
                    "MRI or MRI arthrogram documenting pathology",
                    "Failed conservative treatment or mechanical symptoms",
                    "Medical necessity documented",
                    "Appropriate CPT coding for each arthroscopic procedure",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram",
                    "Physical examination",
                    "Conservative treatment records",
                    "Operative plan with procedures",
                    "Medical necessity statement",
                ],
                "common_denial_reasons": [
                    "CPT coding errors — unbundling of arthroscopic procedures",
                    "Diagnostic arthroscopy billed separately when therapeutic procedure performed",
                    "Post-service audit finding insufficient documentation",
                ],
                "approval_tips": [
                    "Arthroscopic procedure coding is complex — avoid unbundling errors",
                    "Do not bill diagnostic arthroscopy (29805) separately when therapeutic procedure is performed",
                    "Document each procedure performed arthroscopically in the operative report",
                    "Medicare Advantage plans may require PA — verify with specific plan",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 58,
            },

            "neuropsychological_testing": {
                "policy_number": "LCD L36861 (Novitas)",
                "policy_name": "Neuropsychological Testing",
                "criteria": [
                    "Prior authorization not required for original Medicare but subject to medical necessity review",
                    "Documented TBI, stroke, dementia, or other neurological condition with cognitive complaints",
                    "Testing to diagnose cognitive disorder, guide treatment, or assess capacity",
                    "Referral from treating physician with specific clinical question",
                    "Testing must be performed or supervised by qualified neuropsychologist",
                    "No specific hour limit but must be reasonable for the clinical question",
                ],
                "required_documentation": [
                    "Documentation of neurological condition",
                    "Clinical question for testing",
                    "Physician referral",
                    "Test selection rationale",
                    "Testing report with interpretation",
                ],
                "common_denial_reasons": [
                    "Testing not medically necessary — performed for non-covered indication",
                    "Excessive testing hours without documentation of complexity",
                    "CPT coding errors (96132/96133 vs. 96136/96137 — psychologist vs. technician billing)",
                    "Repeat testing without documentation of interval change",
                ],
                "approval_tips": [
                    "Medicare covers neuropsychological testing for cognitive disorders, TBI, stroke, and dementia",
                    "Reference LCD L36861 in documentation for Novitas MAC",
                    "CPT 96132/96133 (psychologist) vs. 96136/96137 (technician under supervision) — bill correctly",
                    "Document the clinical question and how results change management",
                    "Medicare does not have strict hour limits but documentation must support time billed",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 52,
            },

            "cognitive_rehabilitation": {
                "policy_number": "NCD 30.1 / LCD varies by MAC",
                "policy_name": "Cognitive Rehabilitation Therapy",
                "criteria": [
                    "Medicare covers cognitive rehabilitation under speech therapy (SLP) or occupational therapy benefits",
                    "Documented TBI, stroke, or acquired brain injury with cognitive deficits",
                    "Skilled therapy required — patient must demonstrate rehabilitation potential",
                    "Treatment plan with measurable goals",
                    "Must meet Medicare skilled therapy criteria (improvement, maintenance with skilled need, or establishing plan)",
                    "Licensed SLP or OT provider",
                    "Subject to therapy cap and exceptions process",
                ],
                "required_documentation": [
                    "Physician order for therapy",
                    "Evaluation with cognitive deficits documented",
                    "Treatment plan with measurable goals and estimated duration",
                    "Progress notes per session demonstrating skilled need",
                    "Functional outcome measures",
                    "KX modifier if therapy cap threshold is exceeded",
                ],
                "common_denial_reasons": [
                    "Documentation does not demonstrate skilled need — appears to be maintenance therapy",
                    "No measurable progress documented in progress notes",
                    "Therapy cap exceeded without KX modifier",
                    "Treatment goals not specific or measurable",
                    "Provider billing under incorrect benefit category",
                ],
                "approval_tips": [
                    "Medicare covers cognitive rehab under therapy benefits — not a separate benefit category",
                    "Use KX modifier when therapy cap threshold is exceeded and document medical necessity",
                    "Progress notes must clearly demonstrate skilled need at each session",
                    "Reference NCD 30.1 for rehabilitation therapy coverage",
                    "Document functional progress toward goals at every session — Medicare audits therapy notes",
                    "Maintenance therapy may be covered under Jimmo v. Sebelius if skilled need exists",
                ],
                "avg_decision_days": 0,
                "appeal_success_rate": 48,
            },
        },
    },

    # ======================================================================
    #  8. MEDICAID NY (eMedNY)
    # ======================================================================
    "medicaid_ny": {
        "name": "Medicaid New York (eMedNY)",
        "type": "government",
        "source": "NYS Medicaid Program — eMedNY Provider Manuals & Fee Schedules",
        "pa_portal": "eMedNY HIPAA Transaction Portal (emedny.org)",
        "phone": "1-800-343-9000 (eMedNY Provider Services)",
        "avg_p2p_wait_days": 0,
        "procedures": {

            "lumbar_fusion": {
                "policy_number": "EMEDNY-SURG-SPINE-001",
                "policy_name": "Lumbar Spinal Fusion — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED for all spinal fusion procedures under Medicaid NY",
                    "Failed minimum 3 months of conservative treatment (PT, medications, injections)",
                    "MRI or CT demonstrating structural pathology at proposed level(s)",
                    "Documented instability, spondylolisthesis Grade I+, or DDD with failed conservative care",
                    "Functional outcome score (ODI) documented",
                    "At least 1 epidural or facet injection with documented response",
                    "Physical therapy minimum 8 sessions",
                    "Managed care plan (MCO) may have additional requirements — verify with MCO",
                    "Psychological evaluation recommended for chronic pain >6 months",
                ],
                "required_documentation": [
                    "MRI or CT within 6 months",
                    "PT records",
                    "Injection records with response",
                    "ODI score",
                    "Medication history",
                    "Operative plan with levels and CPT codes",
                    "H&P within 30 days",
                    "Prior authorization form (eMedNY PA request)",
                ],
                "common_denial_reasons": [
                    "Prior authorization not obtained before surgery — retroactive PA rarely approved",
                    "Conservative treatment less than 3 months",
                    "No ODI or functional score in submission",
                    "MCO-specific additional criteria not met",
                    "Incorrect PA submission through eMedNY portal",
                ],
                "approval_tips": [
                    "ALWAYS obtain PA before surgery — Medicaid NY rarely approves retroactive PA for elective fusion",
                    "Submit PA through eMedNY portal or by phone — fax is slowest option",
                    "If patient is in a Medicaid MCO (Fidelis, Healthfirst, MetroPlus, Amerigroup), PA goes through MCO, not eMedNY",
                    "MCO criteria may differ from fee-for-service Medicaid — verify with the specific plan",
                    "Document ODI and VAS — these are weighted in the PA review",
                    "Medicaid NY generally follows criteria similar to BCBS but with stricter PA enforcement",
                ],
                "avg_decision_days": 14,
                "appeal_success_rate": 40,
            },

            "lumbar_decompression": {
                "policy_number": "EMEDNY-SURG-SPINE-002",
                "policy_name": "Lumbar Decompression — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED for lumbar decompression under Medicaid NY",
                    "Failed minimum 4 weeks of conservative treatment unless progressive neurological deficit",
                    "MRI demonstrating neural compression correlating with symptoms",
                    "Neurological examination findings documented",
                    "EMG/NCS if radiculopathy uncertain",
                    "For cauda equina or progressive motor deficit: PA may be obtained emergently",
                ],
                "required_documentation": [
                    "MRI within 6 months",
                    "Neurological examination",
                    "PT records (minimum 4 weeks)",
                    "Medication trial documentation",
                    "PA request form through eMedNY or MCO",
                ],
                "common_denial_reasons": [
                    "PA not obtained prior to surgery",
                    "Conservative care less than 4 weeks without progressive deficit",
                    "No imaging correlation documented",
                    "MCO-specific criteria not met",
                ],
                "approval_tips": [
                    "For urgent cases (cauda equina, progressive motor deficit), call eMedNY/MCO for expedited PA",
                    "Document progressive deficit timeline clearly — this bypasses conservative care requirement",
                    "MCO PA process is separate from FFS Medicaid — know which your patient has",
                    "Keep PA approval letter on file — you will need it for billing",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 50,
            },

            "cervical_fusion_acdf": {
                "policy_number": "EMEDNY-SURG-SPINE-003",
                "policy_name": "Cervical Fusion / ACDF — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED",
                    "Failed minimum 4 weeks of conservative care unless myelopathy present",
                    "MRI demonstrating disc herniation or stenosis with cord or root compression",
                    "Radiculopathy or myelopathy with imaging correlation",
                    "NDI score documented",
                    "Maximum 3 levels without additional justification",
                    "If myelopathy: document upper motor neuron signs and functional decline",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI score",
                    "Conservative treatment records",
                    "Operative plan with levels",
                    "PA request through eMedNY or MCO",
                ],
                "common_denial_reasons": [
                    "PA not obtained prior to surgery",
                    "No NDI score",
                    "Conservative care inadequate without documented myelopathy",
                    "MCO additional criteria not addressed",
                ],
                "approval_tips": [
                    "Myelopathy cases should be submitted with expedited PA request",
                    "Include NDI and mJOA for myelopathy — strengthens the submission",
                    "For MCO patients, verify which MCO and submit to their PA department",
                    "Document progression of symptoms with timeline",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 45,
            },

            "cervical_decompression": {
                "policy_number": "EMEDNY-SURG-SPINE-004",
                "policy_name": "Cervical Decompression — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED",
                    "MRI or CT demonstrating cervical stenosis with neural compression",
                    "Failed 4 weeks conservative treatment unless myelopathy",
                    "Neurological examination documenting deficits",
                    "NDI ≥30 or mJOA <14",
                ],
                "required_documentation": [
                    "MRI cervical spine within 6 months",
                    "Neurological examination",
                    "NDI and/or mJOA score",
                    "Conservative treatment records",
                    "PA request form",
                ],
                "common_denial_reasons": [
                    "PA not obtained",
                    "No functional scores",
                    "Conservative care not documented for non-myelopathy",
                ],
                "approval_tips": [
                    "Request expedited PA for myelopathy",
                    "Document gait instability and hand function deficits",
                    "MCO patients require MCO-specific PA",
                    "Include CT if bony pathology",
                ],
                "avg_decision_days": 12,
                "appeal_success_rate": 48,
            },

            "spinal_cord_stimulator": {
                "policy_number": "EMEDNY-SURG-NEURO-010",
                "policy_name": "Spinal Cord Stimulation — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED — Medicaid NY is very strict on SCS",
                    "Chronic neuropathic pain ≥6 months (FBSS, CRPS only — limited diagnostic coverage)",
                    "Failed minimum 6 months of comprehensive conservative management",
                    "Successful trial ≥5 days with ≥50% pain reduction",
                    "Psychological evaluation within 6 months",
                    "Negative urine drug screen",
                    "No active substance use disorder",
                    "Not a candidate for corrective surgery",
                    "Medicaid MCO review is particularly stringent for SCS",
                ],
                "required_documentation": [
                    "SCS trial report with daily outcomes",
                    "Psychological evaluation",
                    "Urine drug screen",
                    "Comprehensive pain treatment history",
                    "MRI/imaging",
                    "PT records (6+ months)",
                    "PA request through eMedNY or MCO",
                ],
                "common_denial_reasons": [
                    "Diagnosis not within Medicaid NY covered indications for SCS",
                    "Trial did not show ≥50% improvement",
                    "PA not obtained — SCS will not be covered retroactively",
                    "Psychological evaluation not completed or too old",
                    "MCO applies additional restrictions beyond eMedNY",
                ],
                "approval_tips": [
                    "Medicaid NY covers SCS for limited diagnoses — verify coverage for the specific diagnosis before trial",
                    "MCO PA for SCS is extremely difficult to obtain — consider peer-to-peer early in the process",
                    "Document comprehensive trial data with daily logs",
                    "Include opioid reduction data if applicable — Medicaid NY tracks this",
                    "Budget for the possibility of denial and have appeal strategy ready",
                ],
                "avg_decision_days": 21,
                "appeal_success_rate": 25,
            },

            "epidural_steroid_injection": {
                "policy_number": "EMEDNY-SURG-PAIN-001",
                "policy_name": "Epidural Steroid Injections — Prior Authorization May Be Required",
                "criteria": [
                    "Prior authorization required by most Medicaid MCOs; FFS may not require PA for first injection",
                    "Radicular pain with imaging correlation",
                    "Conservative treatment attempted",
                    "Maximum 3 injections per region per 12-month period",
                    "Fluoroscopic guidance required",
                    "Response to prior injection documented for subsequent requests",
                ],
                "required_documentation": [
                    "MRI or CT showing pathology",
                    "Pain description and distribution",
                    "Medication trial records",
                    "Prior injection response if applicable",
                    "Planned approach and level",
                    "PA request if MCO requires it",
                ],
                "common_denial_reasons": [
                    "MCO PA not obtained when required",
                    "Exceeded 3 per region per year",
                    "No imaging correlation",
                    "Non-fluoroscopic technique",
                ],
                "approval_tips": [
                    "Check whether patient is FFS or MCO — PA requirements differ significantly",
                    "Most MCOs (Healthfirst, Fidelis, MetroPlus) require PA for ESI",
                    "Document fluoroscopic guidance explicitly",
                    "Include functional improvement data from prior injections",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 55,
            },

            "total_knee_replacement": {
                "policy_number": "EMEDNY-SURG-ORTHO-001",
                "policy_name": "Total Knee Arthroplasty — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED for TKA under Medicaid NY",
                    "Failed minimum 3 months of conservative treatment",
                    "Weight-bearing radiographs showing KL Grade III-IV OA",
                    "Functional impairment documented (KOOS or WOMAC)",
                    "Corticosteroid injection trial",
                    "HbA1c <8.0 for diabetics",
                    "Preoperative medical clearance",
                    "MCO may have additional criteria",
                ],
                "required_documentation": [
                    "Weight-bearing radiographs within 6 months",
                    "KOOS or WOMAC scores",
                    "PT records",
                    "Injection records",
                    "HbA1c if diabetic",
                    "Medical clearance",
                    "PA request through eMedNY or MCO",
                ],
                "common_denial_reasons": [
                    "PA not obtained before surgery",
                    "Non-weight-bearing radiographs",
                    "No functional score",
                    "HbA1c not optimized",
                    "MCO additional criteria not met",
                ],
                "approval_tips": [
                    "Submit PA early — Medicaid NY processing can take up to 14 days",
                    "Weight-bearing radiographs are mandatory — submit them with the PA request",
                    "If MCO patient, PA goes through MCO, not eMedNY",
                    "Document discharge plan including post-acute care — Medicaid NY tracks readmissions",
                    "Include BMI but Medicaid NY does not have strict BMI cutoff",
                ],
                "avg_decision_days": 14,
                "appeal_success_rate": 48,
            },

            "total_hip_replacement": {
                "policy_number": "EMEDNY-SURG-ORTHO-002",
                "policy_name": "Total Hip Arthroplasty — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED",
                    "Failed minimum 3 months of conservative care",
                    "Radiographic severe OA or AVN",
                    "AP pelvis and lateral hip radiographs",
                    "Harris Hip Score <60 or HOOS",
                    "Injection trial or documented contraindication",
                    "HbA1c <8.0 for diabetics",
                    "Preoperative medical clearance",
                ],
                "required_documentation": [
                    "AP pelvis and lateral hip radiographs within 6 months",
                    "Harris Hip Score or HOOS",
                    "PT records",
                    "Injection records",
                    "HbA1c if diabetic",
                    "Medical clearance",
                    "PA request form",
                ],
                "common_denial_reasons": [
                    "PA not obtained",
                    "Mild radiographic changes",
                    "No functional score",
                    "HbA1c not optimized",
                ],
                "approval_tips": [
                    "Submit PA with complete documentation to avoid back-and-forth",
                    "Include discharge plan — Medicaid tracks post-acute utilization",
                    "For MCO patients, submit to MCO PA department",
                    "Harris Hip Score <50 strongly supports approval",
                ],
                "avg_decision_days": 14,
                "appeal_success_rate": 50,
            },

            "acl_reconstruction": {
                "policy_number": "EMEDNY-SURG-ORTHO-005",
                "policy_name": "ACL Reconstruction — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED for ACL reconstruction under Medicaid NY",
                    "MRI confirming complete ACL tear",
                    "Functional instability documented",
                    "Positive Lachman and/or pivot shift",
                    "Pre-hab PT recommended",
                    "Active patient with documented functional demands",
                ],
                "required_documentation": [
                    "MRI confirming ACL tear",
                    "Physical examination findings",
                    "Instability documentation",
                    "Pre-hab PT records if available",
                    "Activity level description",
                    "PA request form",
                ],
                "common_denial_reasons": [
                    "PA not obtained",
                    "Partial tear without instability",
                    "No examination findings documented",
                    "MCO additional criteria not met",
                ],
                "approval_tips": [
                    "Submit PA early — plan for 10-14 day processing time",
                    "Document functional demands clearly — Medicaid reviewers may question surgical indication in low-demand patients",
                    "Include MRI images if possible with the PA submission",
                    "MCO patients go through MCO PA process",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 55,
            },

            "rotator_cuff_repair": {
                "policy_number": "EMEDNY-SURG-ORTHO-008",
                "policy_name": "Rotator Cuff Repair — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED",
                    "MRI showing full-thickness or high-grade partial tear (>50%)",
                    "Failed 6 weeks of conservative care (PT, NSAIDs, injection) or acute traumatic tear",
                    "ASES or DASH score documenting impairment",
                    "Tear is reparable on MRI",
                ],
                "required_documentation": [
                    "MRI shoulder within 6 months",
                    "ASES or DASH score",
                    "PT records (6 weeks)",
                    "Injection records",
                    "Physical examination",
                    "PA request form",
                ],
                "common_denial_reasons": [
                    "PA not obtained",
                    "Partial tear <50% without failed conservative care",
                    "No functional score",
                    "MCO additional criteria not met",
                ],
                "approval_tips": [
                    "Submit PA with complete documentation upfront",
                    "For acute traumatic tears, document mechanism and date — may qualify for expedited PA",
                    "ASES is the preferred functional score for Medicaid NY shoulder submissions",
                    "MCO patients go through MCO PA process",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 52,
            },

            "carpal_tunnel_release": {
                "policy_number": "EMEDNY-SURG-HAND-001",
                "policy_name": "Carpal Tunnel Release — Prior Authorization May Be Required",
                "criteria": [
                    "Prior authorization required by most Medicaid MCOs; FFS may not require PA",
                    "EMG/NCS confirming median neuropathy",
                    "Failed minimum 4 weeks of conservative treatment",
                    "Positive Phalen and/or Tinel test",
                    "Thenar atrophy may expedite",
                ],
                "required_documentation": [
                    "EMG/NCS within 12 months",
                    "Physical examination",
                    "Conservative treatment records",
                    "Functional impact statement",
                    "PA request if MCO requires",
                ],
                "common_denial_reasons": [
                    "MCO PA not obtained when required",
                    "No EMG/NCS obtained",
                    "Conservative care less than 4 weeks",
                ],
                "approval_tips": [
                    "Verify PA requirement — FFS Medicaid may not require PA for CTR but most MCOs do",
                    "EMG/NCS is essential for Medicaid NY CTR approval",
                    "Document specific work and ADL limitations",
                    "Medicaid NY reimburses at lower rate — ensure PA is in place to avoid non-payment",
                ],
                "avg_decision_days": 7,
                "appeal_success_rate": 65,
            },

            "shoulder_arthroscopy": {
                "policy_number": "EMEDNY-SURG-ORTHO-010",
                "policy_name": "Shoulder Arthroscopy — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED",
                    "MRI demonstrating intra-articular pathology",
                    "Failed 6 weeks of conservative care",
                    "Mechanical symptoms or instability documented",
                    "Positive provocative tests on examination",
                ],
                "required_documentation": [
                    "MRI or MRI arthrogram within 6 months",
                    "Physical examination",
                    "PT records (6 weeks)",
                    "Documentation of mechanical symptoms or instability",
                    "Operative plan",
                    "PA request form",
                ],
                "common_denial_reasons": [
                    "PA not obtained",
                    "No MRI before request",
                    "No mechanical symptoms — pain alone insufficient",
                    "MCO criteria not met",
                ],
                "approval_tips": [
                    "Submit PA with complete documentation including MRI and exam findings",
                    "MRI arthrogram for labral pathology increases approval likelihood",
                    "Document all planned procedures in the operative plan",
                    "MCO patients go through MCO PA — verify which MCO",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 52,
            },

            "neuropsychological_testing": {
                "policy_number": "EMEDNY-MED-NEURO-001",
                "policy_name": "Neuropsychological Testing — Prior Authorization Required",
                "criteria": [
                    "Prior authorization REQUIRED for neuropsychological testing under Medicaid NY",
                    "Documented TBI, stroke, or neurological condition with cognitive deficits",
                    "Screening showing cognitive impairment",
                    "Testing to guide treatment, return-to-work, or capacity determination",
                    "Referral from treating physician",
                    "Maximum 8 hours of testing per evaluation",
                    "No testing within 12 months unless documented clinical change",
                ],
                "required_documentation": [
                    "Documentation of neurological condition",
                    "Screening test results (MOCA, MMSE)",
                    "Clinical question for testing",
                    "Physician referral",
                    "Estimated hours and CPT codes",
                    "PA request through eMedNY or MCO",
                ],
                "common_denial_reasons": [
                    "PA not obtained — testing will not be reimbursed without PA",
                    "Repeat testing within 12 months",
                    "No screening showing impairment",
                    "Exceeds 8-hour limit",
                    "MCO additional restrictions not met",
                ],
                "approval_tips": [
                    "PA is mandatory — never proceed without it under Medicaid NY",
                    "Medicaid NY limits to 8 hours — plan testing battery accordingly",
                    "State clinical question clearly in the PA request",
                    "MCO patients may have additional restrictions — verify with MCO",
                    "Include MOCA score to demonstrate objective impairment",
                ],
                "avg_decision_days": 14,
                "appeal_success_rate": 42,
            },

            "cognitive_rehabilitation": {
                "policy_number": "EMEDNY-MED-REHAB-005",
                "policy_name": "Cognitive Rehabilitation Therapy — Prior Authorization Required for Extensions",
                "criteria": [
                    "Initial evaluation and 12 sessions may be covered without PA under therapy benefit for FFS",
                    "Extensions beyond 12 sessions require PA",
                    "MCOs typically require PA from the first session",
                    "Documented TBI or acquired brain injury with cognitive deficits",
                    "Neuropsychological testing recommending rehabilitation",
                    "Measurable treatment goals",
                    "Licensed SLP or OT provider",
                    "Progress documented toward goals for extensions",
                    "Improvement potential — not maintenance-only therapy",
                ],
                "required_documentation": [
                    "Neuropsychological testing report",
                    "Treatment plan with measurable goals",
                    "Provider credentials",
                    "Progress notes for extension requests",
                    "Functional outcome measures",
                    "PA request for extensions or if MCO",
                ],
                "common_denial_reasons": [
                    "MCO PA not obtained from the start",
                    "No neuropsychological testing supporting need",
                    "Goals not measurable",
                    "No progress documented for extension",
                    "Maintenance therapy without improvement potential",
                ],
                "approval_tips": [
                    "Check FFS vs. MCO status — PA requirements differ significantly",
                    "For MCO patients, obtain PA before starting therapy",
                    "Document progress quantitatively at every session",
                    "Set SMART goals tied to functional outcomes",
                    "Medicaid NY tracks utilization — excessive sessions without documented progress will trigger review",
                    "Plan for extension PA request at session 10 to avoid gap in treatment",
                ],
                "avg_decision_days": 10,
                "appeal_success_rate": 38,
            },
        },
    },
}


# ---------------------------------------------------------------------------
#  PAYER NAME ALIASES — used by match_payer()
# ---------------------------------------------------------------------------

_PAYER_ALIASES: dict[str, list[str]] = {
    "united_healthcare": [
        "uhc", "unitedhealthcare", "united healthcare", "united health care",
        "united health", "optum", "uhg", "golden rule",
    ],
    "aetna": [
        "aetna", "aetna better health", "aetna health", "cvs aetna",
        "cvs health", "aetna us healthcare",
    ],
    "bcbs": [
        "bcbs", "blue cross", "blue shield", "bluecross", "blueshield",
        "blue cross blue shield", "anthem", "carefirst", "horizon bcbs",
        "empire bcbs", "empire blue cross", "excellus", "highmark",
        "independence blue cross", "premera", "regence",
    ],
    "cigna": [
        "cigna", "cigna healthcare", "evernorth", "evicore",
        "cigna health and life", "cigna group",
    ],
    "humana": [
        "humana", "humana health", "humana insurance",
        "humana medical plan", "humana gold",
    ],
    "emblem_health": [
        "emblemhealth", "emblem health", "emblem", "hip", "ghi",
        "group health incorporated", "health insurance plan of ny",
        "connecticare", "emblemhealth plan",
    ],
    "medicare": [
        "medicare", "cms", "novitas", "ngs", "national government services",
        "medicare advantage", "medicare part a", "medicare part b",
        "original medicare", "traditional medicare",
    ],
    "medicaid_ny": [
        "medicaid", "medicaid ny", "medicaid new york", "emedny",
        "nys medicaid", "new york medicaid", "fidelis", "healthfirst",
        "metroplus", "amerigroup", "wellcare ny", "molina ny",
        "affinity health plan", "fidelis care",
    ],
}


# ---------------------------------------------------------------------------
#  HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_payer_criteria(payer_key: str, procedure_key: str) -> dict | None:
    """Return the full criteria dict for a specific payer + procedure combination.

    Args:
        payer_key: Key in PAYER_AUTH_GUIDELINES (e.g. "united_healthcare").
        procedure_key: Key in the payer's procedures dict (e.g. "lumbar_fusion").

    Returns:
        The procedure criteria dict, or None if not found.
    """
    payer = PAYER_AUTH_GUIDELINES.get(payer_key)
    if payer is None:
        return None
    return payer.get("procedures", {}).get(procedure_key)


def get_all_payers() -> list[dict]:
    """Return a summary list of all payers in the knowledge base.

    Returns:
        List of dicts with keys: key, name, type, source, procedure_count.
    """
    result: list[dict] = []
    for key, payer in PAYER_AUTH_GUIDELINES.items():
        result.append({
            "key": key,
            "name": payer["name"],
            "type": payer["type"],
            "source": payer["source"],
            "pa_portal": payer.get("pa_portal", ""),
            "phone": payer.get("phone", ""),
            "procedure_count": len(payer.get("procedures", {})),
        })
    return result


def compare_payer_criteria(
    procedure_key: str,
    payer_keys: list[str] | None = None,
) -> list[dict]:
    """Compare criteria for a given procedure across multiple payers side-by-side.

    Args:
        procedure_key: The procedure to compare (e.g. "lumbar_fusion").
        payer_keys: Specific payers to compare. Defaults to all payers.

    Returns:
        List of dicts, one per payer, containing payer name, criteria,
        required_documentation, common_denial_reasons, approval_tips,
        avg_decision_days, and appeal_success_rate.
    """
    if payer_keys is None:
        payer_keys = list(PAYER_AUTH_GUIDELINES.keys())

    comparisons: list[dict] = []
    for payer_key in payer_keys:
        payer = PAYER_AUTH_GUIDELINES.get(payer_key)
        if payer is None:
            continue
        proc = payer.get("procedures", {}).get(procedure_key)
        if proc is None:
            continue
        comparisons.append({
            "payer_key": payer_key,
            "payer_name": payer["name"],
            "payer_type": payer["type"],
            "policy_number": proc.get("policy_number", ""),
            "policy_name": proc.get("policy_name", ""),
            "criteria": proc.get("criteria", []),
            "required_documentation": proc.get("required_documentation", []),
            "common_denial_reasons": proc.get("common_denial_reasons", []),
            "approval_tips": proc.get("approval_tips", []),
            "avg_decision_days": proc.get("avg_decision_days", 0),
            "appeal_success_rate": proc.get("appeal_success_rate", 0),
        })
    return comparisons


def get_payer_tips(payer_key: str, procedure_key: str) -> dict | None:
    """Return only the approval tips and denial reasons for a payer/procedure.

    Args:
        payer_key: Key in PAYER_AUTH_GUIDELINES.
        procedure_key: Key in the payer's procedures dict.

    Returns:
        Dict with approval_tips, common_denial_reasons, avg_decision_days,
        and appeal_success_rate — or None if not found.
    """
    proc = get_payer_criteria(payer_key, procedure_key)
    if proc is None:
        return None
    return {
        "payer_key": payer_key,
        "payer_name": PAYER_AUTH_GUIDELINES[payer_key]["name"],
        "procedure": procedure_key,
        "policy_number": proc.get("policy_number", ""),
        "approval_tips": proc.get("approval_tips", []),
        "common_denial_reasons": proc.get("common_denial_reasons", []),
        "avg_decision_days": proc.get("avg_decision_days", 0),
        "appeal_success_rate": proc.get("appeal_success_rate", 0),
    }


def match_payer(payer_name: str) -> str | None:
    """Fuzzy-match an input payer name to a key in PAYER_AUTH_GUIDELINES.

    Tries exact alias matching first, then falls back to SequenceMatcher
    with a 0.6 threshold.

    Args:
        payer_name: The payer name string to match (e.g. "United Health",
                    "BCBS", "Fidelis").

    Returns:
        The matching payer key (e.g. "united_healthcare") or None.
    """
    if not payer_name:
        return None

    normalized = payer_name.strip().lower()

    # 1. Direct key match
    if normalized in PAYER_AUTH_GUIDELINES:
        return normalized
    # Underscore / dash normalization
    normalized_under = normalized.replace(" ", "_").replace("-", "_")
    if normalized_under in PAYER_AUTH_GUIDELINES:
        return normalized_under

    # 2. Alias exact match
    for payer_key, aliases in _PAYER_ALIASES.items():
        if normalized in aliases:
            return payer_key

    # 3. Alias substring match
    for payer_key, aliases in _PAYER_ALIASES.items():
        for alias in aliases:
            if alias in normalized or normalized in alias:
                return payer_key

    # 4. Fuzzy match against aliases
    best_score = 0.0
    best_key: str | None = None
    for payer_key, aliases in _PAYER_ALIASES.items():
        for alias in aliases:
            score = SequenceMatcher(None, normalized, alias).ratio()
            if score > best_score:
                best_score = score
                best_key = payer_key

    if best_score >= 0.6 and best_key is not None:
        return best_key

    # 5. Fuzzy match against payer display names
    for payer_key, payer_data in PAYER_AUTH_GUIDELINES.items():
        score = SequenceMatcher(
            None, normalized, payer_data["name"].lower()
        ).ratio()
        if score >= 0.6:
            return payer_key

    return None
