"""
NYS Workers' Compensation Board Medical Treatment Guidelines (MTG) — Knowledge Base.

Comprehensive reference data for three specialties: Spine, Orthopedic, and Concussion/TBI.
Each procedure entry includes CPT/ICD-10 codes, conservative care requirements, imaging,
diagnostics, clinical criteria, exclusion criteria, approval factors, and MTG references.

This module is consumed by compliance_checker.py to evaluate prior authorization requests
against the NYS WCB MTG standards.
"""

WCB_TREATMENT_GUIDELINES = {
    # =========================================================================
    # SPINE — 13 procedures
    # =========================================================================
    "spine": {
        "category": "Spine",
        "procedures": {
            # -----------------------------------------------------------------
            # 1. Lumbar Spinal Fusion
            # -----------------------------------------------------------------
            "lumbar_fusion": {
                "name": "Lumbar Spinal Fusion",
                "cpt_codes": ["22612", "22614", "22630", "22632", "22633", "22634"],
                "icd10_codes": [
                    "M43.16", "M43.17", "M47.816", "M47.817", "M48.06",
                    "M51.16", "M51.17", "M96.1", "M53.2X7", "M99.23",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 8,
                        "min_sessions": 16,
                        "description": "Supervised PT with core stabilization, flexibility, and aerobic conditioning",
                    },
                    "medications": {
                        "required": ["NSAIDs", "muscle_relaxants"],
                        "optional": ["neuropathic_agents", "short_term_opioids"],
                        "min_duration_weeks": 6,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["epidural_steroid", "facet_block", "medial_branch_block"],
                        "description": "At least 1 therapeutic injection with documented response",
                    },
                    "activity_modification": {
                        "min_weeks": 6,
                        "description": "Documented work restrictions and activity modification",
                    },
                    "total_conservative_duration_weeks": 12,
                },
                "imaging_requirements": {
                    "required": ["MRI_lumbar"],
                    "conditional": ["CT_lumbar", "flexion_extension_xrays", "myelogram"],
                    "findings_required": [
                        "disc_herniation_or_stenosis_correlating_with_symptoms",
                        "instability_on_dynamic_films_for_fusion",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS_if_radiculopathy_uncertain"],
                },
                "clinical_criteria": [
                    "Documented instability (>4mm translation or >10 degrees angular motion on flex/ext)",
                    "OR spondylolisthesis Grade I or higher with neurological deficit",
                    "OR failed previous decompression with recurrent stenosis",
                    "OR degenerative disc disease with concordant discography (controversial)",
                    "Correlation between imaging findings and clinical symptoms",
                    "Failed minimum 12 weeks of conservative care",
                    "Functional impairment documented (ODI >= 40 or equivalent)",
                ],
                "exclusion_criteria": [
                    "Active infection at surgical site",
                    "Uncontrolled psychiatric condition affecting pain perception",
                    "Active substance abuse disorder",
                    "BMI >40 (relative contraindication, must document medical necessity)",
                    "Severe osteoporosis precluding instrumentation",
                ],
                "approval_factors": {
                    "strong": [
                        "instability_documented",
                        "neurological_deficit",
                        "failed_injections",
                        "completed_PT",
                        "ODI_above_40",
                    ],
                    "moderate": [
                        "correlating_MRI_findings",
                        "failed_medications",
                        "work_disability_documented",
                    ],
                    "weak": [
                        "pain_alone_without_objective_findings",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 4.2: Lumbar Fusion",
            },

            # -----------------------------------------------------------------
            # 2. Lumbar Decompression
            # -----------------------------------------------------------------
            "lumbar_decompression": {
                "name": "Lumbar Decompression (Laminectomy / Laminotomy / Discectomy / Microdiscectomy)",
                "cpt_codes": ["63005", "63012", "63017", "63030", "63042", "63047", "63048"],
                "icd10_codes": [
                    "M51.16", "M51.17", "M51.06", "M51.07", "M48.06",
                    "M47.816", "M47.817", "G83.4", "M54.16", "M54.17",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "Active PT program focusing on McKenzie approach, core strengthening, and flexibility",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "oral_steroids_taper", "neuropathic_agents"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["epidural_steroid"],
                        "description": "ESI recommended but not strictly required if progressive neurological deficit",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Documented activity modification and ergonomic adjustments",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_lumbar"],
                    "conditional": ["CT_lumbar", "myelogram"],
                    "findings_required": [
                        "disc_herniation_or_stenosis_correlating_with_radiculopathy",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS_if_radiculopathy_uncertain", "diagnostic_selective_nerve_root_block"],
                },
                "clinical_criteria": [
                    "Radiculopathy with correlating MRI findings",
                    "OR progressive neurological deficit (immediate surgery may be indicated)",
                    "OR cauda equina syndrome (emergent — no conservative care required)",
                    "Failed minimum 6 weeks of conservative care unless emergent",
                    "Positive tension signs (straight leg raise or femoral nerve stretch)",
                    "Neurological findings on exam correlating with imaging level",
                ],
                "exclusion_criteria": [
                    "Active infection",
                    "Coagulopathy not correctable",
                    "No imaging correlation with symptoms",
                ],
                "approval_factors": {
                    "strong": [
                        "progressive_neurological_deficit",
                        "cauda_equina_syndrome",
                        "correlating_MRI_and_exam",
                        "positive_tension_signs",
                        "failed_conservative_6_weeks",
                    ],
                    "moderate": [
                        "failed_ESI",
                        "work_disability",
                        "positive_EMG",
                    ],
                    "weak": [
                        "pain_without_neurological_findings",
                        "mild_bulge_without_compression",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 4.1: Lumbar Decompression",
            },

            # -----------------------------------------------------------------
            # 3. Lumbar Disc Replacement (Artificial Disc)
            # -----------------------------------------------------------------
            "lumbar_disc_replacement": {
                "name": "Lumbar Total Disc Replacement (Arthroplasty)",
                "cpt_codes": ["22857", "22862", "0163T"],
                "icd10_codes": [
                    "M51.16", "M51.17", "M51.06", "M51.07", "M51.36", "M51.37",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 12,
                        "min_sessions": 24,
                        "description": "Comprehensive PT with core stabilization, flexibility training, and functional restoration",
                    },
                    "medications": {
                        "required": ["NSAIDs", "muscle_relaxants"],
                        "optional": ["neuropathic_agents", "short_term_opioids"],
                        "min_duration_weeks": 8,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["epidural_steroid", "facet_block"],
                        "description": "At least 1 therapeutic injection with documented outcome",
                    },
                    "activity_modification": {
                        "min_weeks": 8,
                        "description": "Documented restrictions and activity modification program",
                    },
                    "total_conservative_duration_weeks": 12,
                },
                "imaging_requirements": {
                    "required": ["MRI_lumbar", "flexion_extension_xrays"],
                    "conditional": ["CT_lumbar", "discography"],
                    "findings_required": [
                        "single_level_disc_disease_L3_S1",
                        "disc_height_preserved_at_least_50_percent",
                        "no_significant_facet_arthrosis",
                    ],
                },
                "diagnostic_requirements": {
                    "required": ["provocative_discography_recommended"],
                    "conditional": ["EMG_NCS"],
                },
                "clinical_criteria": [
                    "Single-level symptomatic disc disease between L3 and S1",
                    "Failed minimum 12 weeks of conservative care",
                    "Disc height preserved (at least 50% of normal)",
                    "No significant facet arthrosis at the affected level",
                    "No spondylolisthesis greater than Grade I",
                    "No prior surgery at the same level (relative contraindication)",
                    "Age typically 18-60 (relative guideline)",
                    "BMI <35 preferred",
                    "Functional impairment documented (ODI >= 40)",
                ],
                "exclusion_criteria": [
                    "Multi-level disc disease",
                    "Significant facet arthrosis at index level",
                    "Spondylolisthesis > Grade I",
                    "Osteoporosis (DEXA T-score < -1.5)",
                    "Active infection or tumor",
                    "Allergy to implant materials",
                    "Prior laminectomy at the level (relative)",
                    "BMI >40",
                ],
                "approval_factors": {
                    "strong": [
                        "single_level_disease",
                        "concordant_discography",
                        "preserved_disc_height",
                        "no_facet_arthrosis",
                        "completed_12_weeks_conservative",
                    ],
                    "moderate": [
                        "age_under_60",
                        "BMI_under_35",
                        "failed_injections",
                    ],
                    "weak": [
                        "axial_pain_only_without_discography",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 4.3: Lumbar Disc Arthroplasty",
            },

            # -----------------------------------------------------------------
            # 4. Cervical Fusion — ACDF
            # -----------------------------------------------------------------
            "cervical_fusion_acdf": {
                "name": "Anterior Cervical Discectomy and Fusion (ACDF)",
                "cpt_codes": ["22551", "22552", "22554", "22585"],
                "icd10_codes": [
                    "M50.10", "M50.11", "M50.12", "M50.13", "M50.120", "M50.121",
                    "M50.020", "M50.021", "M50.022", "M50.023",
                    "M47.11", "M47.12", "M47.13", "M48.02",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "Cervical PT with isometric strengthening, postural training, and manual therapy",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "oral_steroids_taper", "neuropathic_agents", "short_term_opioids"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["cervical_epidural_steroid", "selective_nerve_root_block"],
                        "description": "Cervical ESI recommended but not required if progressive myelopathy",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Cervical collar use if needed, ergonomic modifications, activity restriction",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_cervical"],
                    "conditional": ["CT_cervical", "flexion_extension_xrays", "myelogram_CT"],
                    "findings_required": [
                        "disc_herniation_or_osteophyte_causing_neural_compression",
                        "correlation_with_clinical_radiculopathy_or_myelopathy",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS_if_radiculopathy_uncertain", "SSEP_if_myelopathy"],
                },
                "clinical_criteria": [
                    "Cervical radiculopathy with correlating imaging findings",
                    "OR cervical myelopathy (may be urgent/emergent — reduced conservative requirement)",
                    "Failed minimum 6 weeks of conservative care (unless myelopathy)",
                    "Neurological findings consistent with affected level",
                    "Imaging findings correlate with clinical presentation",
                    "Functional impairment documented (NDI >= 30 or equivalent)",
                ],
                "exclusion_criteria": [
                    "Active cervical infection",
                    "Severe osteoporosis precluding fusion",
                    "Diffuse multi-level disease without clear surgical target",
                    "Untreated coagulopathy",
                ],
                "approval_factors": {
                    "strong": [
                        "myelopathy_signs",
                        "progressive_neurological_deficit",
                        "correlating_MRI_and_exam",
                        "failed_conservative_6_weeks",
                        "positive_EMG",
                    ],
                    "moderate": [
                        "failed_cervical_ESI",
                        "NDI_above_30",
                        "work_disability",
                    ],
                    "weak": [
                        "neck_pain_without_radiculopathy_or_myelopathy",
                        "degenerative_changes_without_neural_compression",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Neck Injury, Section 5.1: Anterior Cervical Discectomy and Fusion",
            },

            # -----------------------------------------------------------------
            # 5. Cervical Fusion — Posterior
            # -----------------------------------------------------------------
            "cervical_fusion_posterior": {
                "name": "Posterior Cervical Fusion (with or without Decompression)",
                "cpt_codes": ["22590", "22595", "22600", "22614", "63001", "63015", "63045", "63048"],
                "icd10_codes": [
                    "M47.11", "M47.12", "M47.13", "M48.02", "M50.00",
                    "M50.01", "M50.02", "M50.03", "M43.12",
                    "S12.000A", "S12.100A", "S12.200A",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "Supervised cervical PT program — may be abbreviated if myelopathy present",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "neuropathic_agents", "oral_steroids"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["cervical_epidural_steroid"],
                        "description": "Not required, especially if myelopathy or instability present",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Cervical immobilization or activity restriction as indicated",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_cervical"],
                    "conditional": ["CT_cervical", "flexion_extension_xrays", "CT_angiography"],
                    "findings_required": [
                        "multi_level_stenosis_or_posterior_compression",
                        "instability_requiring_posterior_stabilization",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS", "SSEP"],
                },
                "clinical_criteria": [
                    "Multi-level cervical stenosis with myelopathy",
                    "OR posterior compression requiring posterior approach",
                    "OR cervical instability requiring posterior fixation",
                    "OR failed prior anterior approach requiring revision",
                    "Neurological findings correlating with imaging",
                    "Failed conservative care (unless emergent myelopathy)",
                ],
                "exclusion_criteria": [
                    "Active infection",
                    "Severe medical comorbidities precluding general anesthesia",
                    "No imaging correlation",
                ],
                "approval_factors": {
                    "strong": [
                        "myelopathy",
                        "multi_level_stenosis",
                        "instability",
                        "progressive_deficit",
                        "correlating_imaging",
                    ],
                    "moderate": [
                        "failed_anterior_approach",
                        "failed_ESI",
                        "functional_impairment",
                    ],
                    "weak": [
                        "neck_pain_without_neural_compromise",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Neck Injury, Section 5.2: Posterior Cervical Fusion",
            },

            # -----------------------------------------------------------------
            # 6. Cervical Disc Replacement
            # -----------------------------------------------------------------
            "cervical_disc_replacement": {
                "name": "Cervical Total Disc Replacement (Arthroplasty)",
                "cpt_codes": ["22856", "22858", "0095T", "0098T"],
                "icd10_codes": [
                    "M50.10", "M50.11", "M50.12", "M50.13",
                    "M50.020", "M50.021", "M50.022", "M50.023",
                    "M50.120", "M50.121",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "Structured cervical PT program with isometric strengthening and manual therapy",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "neuropathic_agents", "oral_steroids_taper"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["cervical_epidural_steroid", "selective_nerve_root_block"],
                        "description": "Cervical ESI recommended but not required",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Activity modification and ergonomic workplace adjustments",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_cervical"],
                    "conditional": ["CT_cervical", "flexion_extension_xrays"],
                    "findings_required": [
                        "single_or_two_level_disc_disease_C3_C7",
                        "neural_compression_correlating_with_symptoms",
                        "maintained_disc_height",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS"],
                },
                "clinical_criteria": [
                    "Cervical radiculopathy at 1-2 contiguous levels (C3-C7)",
                    "Failed minimum 6 weeks of conservative care",
                    "Imaging correlation with clinical presentation",
                    "No significant facet arthrosis at affected levels",
                    "Adequate disc height for implant",
                    "No cervical instability or spondylolisthesis",
                    "Age typically 18-65",
                ],
                "exclusion_criteria": [
                    "Cervical myelopathy (relative — ACDF preferred)",
                    "Significant facet arthrosis at index level",
                    "Cervical instability",
                    "Osteoporosis",
                    "Prior surgery at the same level",
                    "Systemic inflammatory arthropathy (RA)",
                    "More than 2 levels of disease",
                    "Active infection or tumor",
                ],
                "approval_factors": {
                    "strong": [
                        "single_level_radiculopathy",
                        "correlating_MRI",
                        "failed_conservative_care",
                        "maintained_disc_height",
                        "no_facet_arthrosis",
                    ],
                    "moderate": [
                        "age_under_65",
                        "failed_ESI",
                        "positive_EMG",
                    ],
                    "weak": [
                        "neck_pain_predominant_without_radiculopathy",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Neck Injury, Section 5.3: Cervical Disc Arthroplasty",
            },

            # -----------------------------------------------------------------
            # 7. Cervical Decompression
            # -----------------------------------------------------------------
            "cervical_decompression": {
                "name": "Cervical Decompression (Foraminotomy / Laminectomy / Laminoplasty)",
                "cpt_codes": ["63020", "63035", "63040", "63045", "63050", "63051"],
                "icd10_codes": [
                    "M50.10", "M50.11", "M50.12", "M50.13",
                    "M47.11", "M47.12", "M48.02",
                    "M50.020", "M50.021", "M50.022",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "Cervical PT emphasizing postural correction, isometric strengthening, and manual therapy",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "oral_steroids_taper", "neuropathic_agents"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["cervical_epidural_steroid", "selective_nerve_root_block"],
                        "description": "Recommended for radiculopathy, not required for myelopathy",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Ergonomic adjustments and activity restriction",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_cervical"],
                    "conditional": ["CT_cervical", "myelogram_CT"],
                    "findings_required": [
                        "foraminal_stenosis_or_central_stenosis",
                        "neural_compression_at_symptomatic_level",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS", "SSEP_if_myelopathy_suspected"],
                },
                "clinical_criteria": [
                    "Cervical radiculopathy or myelopathy with correlating imaging",
                    "Failed minimum 6 weeks of conservative care (unless myelopathy or progressive deficit)",
                    "Neurological examination consistent with level of compression",
                    "Functional impairment documented",
                ],
                "exclusion_criteria": [
                    "Cervical instability at affected level (fusion may be needed)",
                    "Active infection",
                    "No imaging correlation",
                ],
                "approval_factors": {
                    "strong": [
                        "myelopathy",
                        "progressive_neurological_deficit",
                        "correlating_imaging_and_exam",
                        "failed_conservative_6_weeks",
                    ],
                    "moderate": [
                        "radiculopathy_with_positive_EMG",
                        "failed_cervical_ESI",
                        "NDI_above_30",
                    ],
                    "weak": [
                        "neck_pain_only",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Neck Injury, Section 5.4: Cervical Decompression",
            },

            # -----------------------------------------------------------------
            # 8. Spinal Cord Stimulator
            # -----------------------------------------------------------------
            "spinal_cord_stimulator": {
                "name": "Spinal Cord Stimulator (Trial and Permanent Implant)",
                "cpt_codes": [
                    "63650", "63655", "63661", "63662", "63663", "63664",
                    "63685", "63688",
                ],
                "icd10_codes": [
                    "M54.5", "M54.16", "M54.17", "G89.29", "G89.4",
                    "M96.1", "G62.9", "M79.2",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 12,
                        "min_sessions": 24,
                        "description": "Comprehensive PT including functional restoration, aquatic therapy, and pain management strategies",
                    },
                    "medications": {
                        "required": ["NSAIDs", "neuropathic_agents"],
                        "optional": ["muscle_relaxants", "opioids_stable_dose", "topical_analgesics"],
                        "min_duration_weeks": 12,
                    },
                    "injections": {
                        "min_attempts": 2,
                        "types": ["epidural_steroid", "facet_block", "medial_branch_block", "nerve_block"],
                        "description": "Multiple injection modalities attempted and failed or provided only temporary relief",
                    },
                    "activity_modification": {
                        "min_weeks": 12,
                        "description": "Documented functional limitations and activity modification program",
                    },
                    "total_conservative_duration_weeks": 24,
                    "additional_requirements": [
                        "Psychological evaluation by licensed psychologist clearing patient for implant",
                        "Failed or contraindicated for surgical intervention",
                        "Stable medication regimen",
                    ],
                },
                "imaging_requirements": {
                    "required": ["MRI_spine_at_pain_level"],
                    "conditional": ["CT_spine", "myelogram"],
                    "findings_required": [
                        "post_surgical_changes_or_chronic_pathology",
                        "no_surgically_correctable_lesion",
                    ],
                },
                "diagnostic_requirements": {
                    "required": ["psychological_evaluation"],
                    "conditional": ["EMG_NCS", "quantitative_sensory_testing"],
                },
                "clinical_criteria": [
                    "Chronic neuropathic pain for at least 6 months",
                    "Failed at least 6 months of comprehensive conservative care",
                    "Failed or not a candidate for further surgical intervention",
                    "Psychological evaluation clearing patient (no untreated depression, personality disorders, or secondary gain)",
                    "Trial stimulator period required (3-10 days) with >= 50% pain relief to proceed to permanent",
                    "Stable opioid dose or decreasing trend",
                    "Patient demonstrates understanding and realistic expectations",
                    "Functional improvement goals identified",
                ],
                "exclusion_criteria": [
                    "Untreated psychiatric disorder (major depression, psychosis, somatization)",
                    "Active substance abuse",
                    "Pending litigation as primary motivation (relative)",
                    "Surgically correctable lesion not yet addressed",
                    "Coagulopathy",
                    "Active infection",
                    "Inability to operate the device",
                    "Failed SCS trial (<50% relief during trial period)",
                ],
                "approval_factors": {
                    "strong": [
                        "successful_trial_50_percent_relief",
                        "positive_psych_eval",
                        "failed_surgery_FBSS",
                        "neuropathic_pain_documented",
                        "6_months_conservative_care",
                    ],
                    "moderate": [
                        "failed_multiple_injections",
                        "stable_medications",
                        "functional_improvement_during_trial",
                    ],
                    "weak": [
                        "axial_pain_predominant",
                        "secondary_gain_concerns",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 6.1: Spinal Cord Stimulation",
            },

            # -----------------------------------------------------------------
            # 9. Epidural Steroid Injection
            # -----------------------------------------------------------------
            "epidural_steroid_injection": {
                "name": "Epidural Steroid Injection (Interlaminar / Transforaminal / Caudal)",
                "cpt_codes": ["62320", "62321", "62322", "62323", "64479", "64480", "64483", "64484"],
                "icd10_codes": [
                    "M51.16", "M51.17", "M54.16", "M54.17",
                    "M50.10", "M50.11", "M50.12",
                    "M47.816", "M47.817", "M48.06",
                    "G55", "M54.5",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 2,
                        "min_sessions": 4,
                        "description": "Initial PT trial or concurrent PT preferred — may proceed without PT if acute radiculopathy",
                    },
                    "medications": {
                        "required": ["NSAIDs_or_oral_steroids"],
                        "optional": ["muscle_relaxants", "neuropathic_agents"],
                        "min_duration_weeks": 2,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "This IS the injection procedure — no prior injection required",
                    },
                    "activity_modification": {
                        "min_weeks": 2,
                        "description": "Brief activity modification trial",
                    },
                    "total_conservative_duration_weeks": 2,
                },
                "imaging_requirements": {
                    "required": ["MRI_at_affected_level"],
                    "conditional": ["CT_if_MRI_contraindicated"],
                    "findings_required": [
                        "disc_herniation_or_stenosis_at_symptomatic_level",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_NCS_if_diagnosis_uncertain"],
                },
                "clinical_criteria": [
                    "Radiculopathy with correlating imaging findings",
                    "Failed initial conservative measures (medication, brief PT)",
                    "Maximum 3 injections per region per 12-month period",
                    "At least 2-week interval between injections in same region",
                    "Documented response to each prior injection before repeat",
                    "If no improvement after 2 injections, third generally not recommended",
                    "Fluoroscopic or CT guidance required",
                ],
                "exclusion_criteria": [
                    "Active infection (systemic or local)",
                    "Uncontrolled diabetes (relative — glucose control required)",
                    "Allergy to contrast or steroids",
                    "Coagulopathy or therapeutic anticoagulation",
                    "Pregnancy",
                    "More than 3 injections in 12 months at same region",
                ],
                "approval_factors": {
                    "strong": [
                        "acute_radiculopathy",
                        "correlating_MRI_findings",
                        "first_or_second_injection_in_series",
                        "documented_relief_from_prior_injection",
                    ],
                    "moderate": [
                        "failed_oral_medications",
                        "avoiding_surgery",
                        "concurrent_PT",
                    ],
                    "weak": [
                        "axial_pain_only",
                        "third_injection_without_documented_prior_benefit",
                        "no_MRI_findings",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "max_per_region_per_year": 3,
                    "min_interval_days": 14,
                    "reassess_after_injections": 2,
                },
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.4: Epidural Steroid Injections",
            },

            # -----------------------------------------------------------------
            # 10. Facet Joint Injection
            # -----------------------------------------------------------------
            "facet_joint_injection": {
                "name": "Facet Joint Injection (Diagnostic and Therapeutic)",
                "cpt_codes": ["64490", "64491", "64492", "64493", "64494", "64495"],
                "icd10_codes": [
                    "M47.812", "M47.816", "M47.817", "M54.5",
                    "M54.2", "M54.16", "M54.17",
                    "M46.96", "M46.97",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 8,
                        "description": "PT trial including core stabilization and flexibility program",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "oral_analgesics"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "This IS the diagnostic/therapeutic injection",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Activity modification with documented response",
                    },
                    "total_conservative_duration_weeks": 4,
                },
                "imaging_requirements": {
                    "required": ["MRI_or_CT_at_affected_level"],
                    "conditional": ["plain_xrays"],
                    "findings_required": [
                        "facet_arthrosis_or_hypertrophy_at_symptomatic_level",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Axial pain consistent with facet-mediated pain pattern",
                    "Pain with extension and rotation",
                    "Paraspinal tenderness at affected level",
                    "No predominant radiculopathy",
                    "Failed 4 weeks of conservative care",
                    "Fluoroscopic guidance required",
                    "Maximum 3 sessions per region per 12-month period for therapeutic",
                    "Diagnostic block: must achieve >= 80% pain relief to confirm facet source",
                ],
                "exclusion_criteria": [
                    "Active infection",
                    "Coagulopathy",
                    "Predominant radicular symptoms (ESI preferred)",
                    "Allergy to injectate",
                ],
                "approval_factors": {
                    "strong": [
                        "classic_facet_pain_pattern",
                        "imaging_showing_facet_arthrosis",
                        "failed_conservative_4_weeks",
                        "diagnostic_purpose",
                    ],
                    "moderate": [
                        "prior_positive_diagnostic_block",
                        "pain_with_extension_and_rotation",
                    ],
                    "weak": [
                        "diffuse_pain_without_facet_pattern",
                        "multiple_prior_injections_without_benefit",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "max_per_region_per_year": 3,
                    "min_interval_days": 14,
                },
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.5: Facet Joint Injections",
            },

            # -----------------------------------------------------------------
            # 11. Medial Branch Block
            # -----------------------------------------------------------------
            "medial_branch_block": {
                "name": "Medial Branch Block (Diagnostic — for Radiofrequency Ablation Candidacy)",
                "cpt_codes": ["64490", "64491", "64492", "64493", "64494", "64495"],
                "icd10_codes": [
                    "M47.812", "M47.816", "M47.817", "M54.5",
                    "M54.2", "M54.89",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 8,
                        "description": "PT trial focused on core stability and active exercise program",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "This IS the diagnostic block — two positive blocks required before RFA",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Activity modification trial",
                    },
                    "total_conservative_duration_weeks": 4,
                },
                "imaging_requirements": {
                    "required": ["MRI_or_CT_at_affected_level"],
                    "conditional": ["plain_xrays"],
                    "findings_required": [
                        "facet_arthrosis_or_hypertrophy",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Axial pain consistent with facet-mediated pain (non-radicular)",
                    "Pain with extension and rotation at affected levels",
                    "Two separate diagnostic medial branch blocks required for RFA candidacy",
                    "Each block must achieve >= 80% pain relief for at least the expected duration of the anesthetic",
                    "Use low-volume local anesthetic (0.3-0.5 mL per nerve) to avoid false positive",
                    "Blocks performed on separate dates with different duration anesthetics (dual comparative blocks preferred)",
                    "Fluoroscopic guidance required",
                ],
                "exclusion_criteria": [
                    "Radicular pain pattern",
                    "Active infection",
                    "Coagulopathy",
                    "Prior negative MBB at same levels",
                ],
                "approval_factors": {
                    "strong": [
                        "classic_facet_pain_pattern",
                        "failed_conservative_care",
                        "purpose_is_RFA_candidacy_evaluation",
                        "imaging_facet_arthrosis",
                    ],
                    "moderate": [
                        "first_diagnostic_block",
                        "confirmation_block_after_positive_first",
                    ],
                    "weak": [
                        "multiple_prior_negative_blocks",
                        "diffuse_pain_pattern",
                    ],
                },
                "global_period_days": 0,
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.5.1: Medial Branch Blocks",
            },

            # -----------------------------------------------------------------
            # 12. Radiofrequency Ablation (RFA / Neurotomy)
            # -----------------------------------------------------------------
            "radiofrequency_ablation": {
                "name": "Radiofrequency Ablation / Neurotomy (Facet Denervation)",
                "cpt_codes": ["64625", "64633", "64634", "64635", "64636"],
                "icd10_codes": [
                    "M47.812", "M47.816", "M47.817", "M54.5",
                    "M54.2", "M54.89",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 8,
                        "description": "PT completed before or concurrent with diagnostic block phase",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 2,
                        "types": ["medial_branch_block"],
                        "description": "TWO positive diagnostic medial branch blocks with >= 80% relief each required before RFA",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Documented activity modification",
                    },
                    "total_conservative_duration_weeks": 8,
                },
                "imaging_requirements": {
                    "required": ["MRI_or_CT_at_affected_level"],
                    "conditional": ["plain_xrays"],
                    "findings_required": [
                        "facet_arthrosis_or_hypertrophy_at_treatment_levels",
                    ],
                },
                "diagnostic_requirements": {
                    "required": ["two_positive_medial_branch_blocks"],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Two positive diagnostic medial branch blocks with >= 80% pain relief each",
                    "Blocks performed on separate dates",
                    "Axial pain pattern consistent with facet-mediated pain",
                    "Failed conservative care including PT and medications",
                    "Pain duration at least 3 months",
                    "Fluoroscopic guidance required",
                    "Repeat RFA may be performed if relief from prior RFA lasted >= 6 months",
                    "Maximum treatment: 3 levels per side per session",
                ],
                "exclusion_criteria": [
                    "Negative or equivocal diagnostic medial branch blocks (<80% relief)",
                    "Only one diagnostic block performed (need two)",
                    "Active infection",
                    "Coagulopathy",
                    "Pregnancy",
                ],
                "approval_factors": {
                    "strong": [
                        "two_positive_MBB_80_percent_relief",
                        "documented_duration_of_relief_from_blocks",
                        "failed_conservative_care",
                        "axial_pain_pattern",
                    ],
                    "moderate": [
                        "imaging_showing_facet_arthrosis",
                        "functional_impairment",
                        "prior_successful_RFA_with_recurrence",
                    ],
                    "weak": [
                        "single_positive_block_only",
                        "diffuse_pain",
                    ],
                },
                "global_period_days": 10,
                "frequency_limits": {
                    "repeat_if_relief_lasted_months": 6,
                    "max_levels_per_session": 3,
                },
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.6: Radiofrequency Neurotomy",
            },

            # -----------------------------------------------------------------
            # 13. Sacroiliac Joint Injection
            # -----------------------------------------------------------------
            "sacroiliac_joint_injection": {
                "name": "Sacroiliac (SI) Joint Injection (Diagnostic and Therapeutic)",
                "cpt_codes": ["27096"],
                "icd10_codes": [
                    "M53.3", "M46.1", "M46.28", "M54.5",
                    "S33.6XXA", "S33.6XXD", "S33.6XXS",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 8,
                        "description": "PT with SI joint stabilization exercises, pelvic alignment, and core strengthening",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "topical_analgesics"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "This IS the SI joint injection",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Activity modification and SI belt use if indicated",
                    },
                    "total_conservative_duration_weeks": 4,
                },
                "imaging_requirements": {
                    "required": ["plain_xrays_pelvis_or_SI_joints"],
                    "conditional": ["MRI_pelvis", "CT_pelvis", "bone_scan"],
                    "findings_required": [
                        "SI_joint_pathology_or_clinical_suspicion",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["HLA_B27_if_inflammatory_suspected"],
                },
                "clinical_criteria": [
                    "Pain localized to SI joint region (positive pointing test)",
                    "At least 3 of 5 provocative SI joint tests positive (compression, distraction, thigh thrust, Gaenslen, sacral thrust)",
                    "Failed 4 weeks of conservative care",
                    "Fluoroscopic guidance with arthrographic confirmation required",
                    "Maximum 3 therapeutic injections per joint per 12 months",
                    "Diagnostic injection: >= 75% pain relief confirms SI joint as source",
                ],
                "exclusion_criteria": [
                    "Active infection",
                    "Coagulopathy",
                    "Overlying skin infection",
                    "Allergy to injectate",
                    "Pregnancy (relative)",
                ],
                "approval_factors": {
                    "strong": [
                        "positive_provocative_tests_3_of_5",
                        "pain_localized_to_SI_joint",
                        "failed_conservative_4_weeks",
                        "diagnostic_purpose",
                    ],
                    "moderate": [
                        "imaging_showing_SI_pathology",
                        "post_fusion_SI_dysfunction",
                        "prior_positive_diagnostic_injection",
                    ],
                    "weak": [
                        "vague_low_back_pain",
                        "negative_provocative_tests",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "max_per_joint_per_year": 3,
                    "min_interval_days": 14,
                },
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.7: Sacroiliac Joint Injection",
            },

            # -----------------------------------------------------------------
            # 14. Trigger Point Injection
            # -----------------------------------------------------------------
            "trigger_point_injection": {
                "name": "Trigger Point Injection",
                "cpt_codes": ["20552", "20553"],
                "icd10_codes": [
                    "M79.1", "M79.10", "M79.11", "M79.12", "M79.18",
                    "M54.2", "M54.5", "M54.6", "M54.9",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 2,
                        "min_sessions": 4,
                        "description": "PT with stretching, manual therapy, and myofascial release techniques",
                    },
                    "medications": {
                        "required": ["NSAIDs_or_muscle_relaxants"],
                        "optional": ["topical_analgesics"],
                        "min_duration_weeks": 2,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "This IS the trigger point injection",
                    },
                    "activity_modification": {
                        "min_weeks": 2,
                        "description": "Ergonomic modifications and stretching program",
                    },
                    "total_conservative_duration_weeks": 2,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["plain_xrays", "MRI_if_underlying_pathology_suspected"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Palpable taut band with reproducible trigger point",
                    "Pain pattern consistent with myofascial pain syndrome",
                    "Failed stretch-and-spray or manual therapy",
                    "Limited to 3-4 trigger points per session",
                    "Maximum 4 sessions over initial 8-week period",
                    "Continued injections only if documented functional improvement",
                    "Must be combined with active PT and stretching program",
                ],
                "exclusion_criteria": [
                    "Active infection at injection site",
                    "Coagulopathy",
                    "Allergy to local anesthetic",
                    "No identifiable trigger point on exam",
                ],
                "approval_factors": {
                    "strong": [
                        "palpable_trigger_point",
                        "failed_manual_therapy",
                        "concurrent_PT",
                        "documented_functional_improvement",
                    ],
                    "moderate": [
                        "myofascial_pain_pattern",
                        "limited_sessions_requested",
                    ],
                    "weak": [
                        "diffuse_pain_without_trigger_points",
                        "prolonged_series_without_improvement",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "max_sessions_initial_8_weeks": 4,
                    "max_trigger_points_per_session": 4,
                    "reassess_after_sessions": 4,
                },
                "mtg_reference": "NYS WCB MTG - Mid and Lower Back, Section 3.3: Trigger Point Injections",
            },
        },
    },

    # =========================================================================
    # ORTHOPEDIC — 10 procedures
    # =========================================================================
    "orthopedic": {
        "category": "Orthopedic",
        "procedures": {
            # -----------------------------------------------------------------
            # 1. Knee Arthroscopy (Meniscus)
            # -----------------------------------------------------------------
            "knee_arthroscopy": {
                "name": "Knee Arthroscopy (Meniscus Repair / Meniscectomy / Chondroplasty)",
                "cpt_codes": ["29880", "29881", "29882", "29883", "29877", "29876"],
                "icd10_codes": [
                    "M23.20", "M23.21", "M23.22", "M23.30", "M23.31",
                    "S83.200A", "S83.210A", "S83.220A", "S83.280A",
                    "M17.11", "M17.12",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "PT with quadriceps strengthening, ROM exercises, and functional training",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["intra_articular_corticosteroid", "topical_analgesics"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": ["intra_articular_corticosteroid"],
                        "description": "Corticosteroid injection may be attempted but not required",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Activity modification, bracing, and weight-bearing as tolerated",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_knee"],
                    "conditional": ["plain_xrays_knee_weight_bearing"],
                    "findings_required": [
                        "meniscus_tear_on_MRI",
                        "correlation_with_clinical_findings",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Mechanical symptoms (locking, catching, giving way) with MRI-confirmed meniscus tear",
                    "OR acute traumatic tear with persistent symptoms after 6 weeks",
                    "OR bucket-handle tear causing locked knee (may proceed urgently)",
                    "Failed minimum 6 weeks of conservative care (unless locked knee)",
                    "Positive McMurray test or joint line tenderness",
                    "Functional limitation affecting work or daily activities",
                ],
                "exclusion_criteria": [
                    "Degenerative meniscus tear without mechanical symptoms (arthroscopy not recommended)",
                    "Advanced tricompartmental arthritis (TKR may be more appropriate)",
                    "Active joint infection",
                    "Uncorrectable coagulopathy",
                ],
                "approval_factors": {
                    "strong": [
                        "mechanical_symptoms",
                        "MRI_confirmed_tear",
                        "acute_traumatic_onset",
                        "locked_knee",
                        "failed_conservative_6_weeks",
                    ],
                    "moderate": [
                        "positive_McMurray",
                        "joint_line_tenderness",
                        "functional_limitation",
                    ],
                    "weak": [
                        "degenerative_tear_without_mechanical_symptoms",
                        "pain_only_without_mechanical_signs",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Knee Injury, Section 4.1: Knee Arthroscopy",
            },

            # -----------------------------------------------------------------
            # 2. ACL Reconstruction
            # -----------------------------------------------------------------
            "acl_reconstruction": {
                "name": "Anterior Cruciate Ligament (ACL) Reconstruction",
                "cpt_codes": ["29888", "27427", "27428", "27429"],
                "icd10_codes": [
                    "S83.511A", "S83.512A", "S83.519A",
                    "M23.611", "M23.612", "M23.619",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 8,
                        "description": "Pre-surgical rehabilitation (prehab) to restore ROM, reduce swelling, and strengthen quadriceps",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["analgesics"],
                        "min_duration_weeks": 2,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Injections generally not indicated for ACL tears",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Bracing, crutches, activity modification — assess for functional instability",
                    },
                    "total_conservative_duration_weeks": 4,
                },
                "imaging_requirements": {
                    "required": ["MRI_knee"],
                    "conditional": ["plain_xrays_knee", "stress_xrays"],
                    "findings_required": [
                        "ACL_tear_complete_or_high_grade_partial",
                        "assess_for_concurrent_meniscus_or_cartilage_injury",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "MRI-confirmed complete ACL tear (or high-grade partial with instability)",
                    "Positive Lachman test and/or positive pivot shift",
                    "Functional instability affecting work or activities",
                    "Patient willing to complete post-operative rehabilitation (6-9 months)",
                    "Pre-operative ROM near full extension required",
                    "Swelling controlled before surgery",
                    "Young or active patients with instability — surgery generally recommended",
                    "Older sedentary patients may trial bracing and PT as alternative",
                ],
                "exclusion_criteria": [
                    "Active joint infection",
                    "Fixed flexion contracture > 10 degrees (address before surgery)",
                    "Significant swelling (delay surgery until resolved)",
                    "Advanced arthritic changes (relative contraindication)",
                    "Patient unwilling to comply with rehabilitation protocol",
                ],
                "approval_factors": {
                    "strong": [
                        "complete_ACL_tear_on_MRI",
                        "positive_Lachman_test",
                        "functional_instability",
                        "active_patient",
                        "pre_op_ROM_restored",
                    ],
                    "moderate": [
                        "concurrent_meniscus_tear",
                        "work_requires_physical_activity",
                        "young_age",
                    ],
                    "weak": [
                        "partial_tear_without_instability",
                        "sedentary_patient",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Knee Injury, Section 4.3: ACL Reconstruction",
            },

            # -----------------------------------------------------------------
            # 3. Total Knee Replacement
            # -----------------------------------------------------------------
            "total_knee_replacement": {
                "name": "Total Knee Arthroplasty (TKA / Total Knee Replacement)",
                "cpt_codes": ["27447"],
                "icd10_codes": [
                    "M17.0", "M17.10", "M17.11", "M17.12",
                    "M17.2", "M17.30", "M17.31",
                    "M87.051", "M87.052",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 8,
                        "min_sessions": 16,
                        "description": "Supervised PT with strengthening, ROM, aquatic therapy, and functional training",
                    },
                    "medications": {
                        "required": ["NSAIDs", "acetaminophen"],
                        "optional": ["topical_NSAIDs", "duloxetine", "short_term_opioids"],
                        "min_duration_weeks": 8,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["intra_articular_corticosteroid", "viscosupplementation"],
                        "description": "At least 1 corticosteroid injection; viscosupplementation may be trialed",
                    },
                    "activity_modification": {
                        "min_weeks": 8,
                        "description": "Weight management counseling, assistive devices, activity modification",
                    },
                    "total_conservative_duration_weeks": 12,
                },
                "imaging_requirements": {
                    "required": ["plain_xrays_knee_weight_bearing", "plain_xrays_knee_AP_lateral_sunrise"],
                    "conditional": ["MRI_knee", "long_leg_alignment_films"],
                    "findings_required": [
                        "moderate_to_severe_joint_space_narrowing",
                        "Kellgren_Lawrence_grade_3_or_4",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["aspiration_if_infection_suspected", "lab_work_ESR_CRP"],
                },
                "clinical_criteria": [
                    "Moderate to severe osteoarthritis (KL Grade 3-4) on weight-bearing X-rays",
                    "Failed minimum 3 months of comprehensive conservative care",
                    "Significant functional impairment (KOOS or WOMAC scores)",
                    "Pain affecting sleep, work, and daily activities",
                    "BMI ideally <40 (BMI >40 is relative contraindication — must document necessity and optimization)",
                    "Medical comorbidities optimized (diabetes HbA1c <8, tobacco cessation)",
                    "Age typically >50 (younger patients require strong justification)",
                    "Failed non-operative management including injections",
                ],
                "exclusion_criteria": [
                    "Active joint infection",
                    "Remote active infection (UTI, dental — must clear first)",
                    "BMI >40 without documented optimization efforts",
                    "Uncontrolled diabetes (HbA1c >8)",
                    "Active tobacco use (relative — cessation required or documented counseling)",
                    "Neuropathic joint (Charcot)",
                    "Inadequate bone stock or severe vascular insufficiency",
                ],
                "approval_factors": {
                    "strong": [
                        "KL_grade_3_or_4",
                        "failed_conservative_12_weeks",
                        "significant_functional_impairment",
                        "failed_injections",
                        "BMI_under_40",
                    ],
                    "moderate": [
                        "HbA1c_under_8",
                        "tobacco_cessation",
                        "bone_on_bone_xray",
                        "age_over_50",
                    ],
                    "weak": [
                        "mild_arthritis_KL_1_2",
                        "BMI_over_40",
                        "young_patient_under_50",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Knee Injury, Section 4.5: Total Knee Arthroplasty",
            },

            # -----------------------------------------------------------------
            # 4. Total Hip Replacement
            # -----------------------------------------------------------------
            "total_hip_replacement": {
                "name": "Total Hip Arthroplasty (THA / Total Hip Replacement)",
                "cpt_codes": ["27130"],
                "icd10_codes": [
                    "M16.0", "M16.10", "M16.11", "M16.12",
                    "M16.2", "M16.30", "M16.31",
                    "M87.051", "M87.052", "S72.001A", "S72.002A",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 8,
                        "min_sessions": 16,
                        "description": "Supervised PT with hip strengthening, ROM, gait training, and functional activities",
                    },
                    "medications": {
                        "required": ["NSAIDs", "acetaminophen"],
                        "optional": ["topical_NSAIDs", "short_term_opioids"],
                        "min_duration_weeks": 8,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["intra_articular_hip_corticosteroid"],
                        "description": "At least 1 fluoroscopic-guided intra-articular hip injection",
                    },
                    "activity_modification": {
                        "min_weeks": 8,
                        "description": "Assistive devices (cane), weight management, activity modification",
                    },
                    "total_conservative_duration_weeks": 12,
                },
                "imaging_requirements": {
                    "required": ["plain_xrays_hip_AP_pelvis_and_lateral"],
                    "conditional": ["MRI_hip", "CT_hip"],
                    "findings_required": [
                        "moderate_to_severe_joint_space_narrowing",
                        "osteophytes_sclerosis_or_cyst_formation",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["aspiration_if_infection_suspected", "lab_work_ESR_CRP"],
                },
                "clinical_criteria": [
                    "Moderate to severe hip osteoarthritis on X-rays",
                    "Significant pain and functional limitation (Harris Hip Score)",
                    "Failed minimum 3 months of conservative care",
                    "Pain affecting sleep, ambulation, and daily activities",
                    "BMI ideally <40",
                    "Medical comorbidities optimized",
                    "Failed injection therapy",
                ],
                "exclusion_criteria": [
                    "Active joint infection",
                    "Remote active infection",
                    "BMI >40 without optimization documentation",
                    "Uncontrolled diabetes",
                    "Active tobacco use (relative)",
                    "Severe vascular insufficiency",
                    "Neuropathic joint",
                ],
                "approval_factors": {
                    "strong": [
                        "severe_joint_space_narrowing",
                        "failed_conservative_12_weeks",
                        "significant_functional_impairment",
                        "failed_injection",
                        "avascular_necrosis",
                    ],
                    "moderate": [
                        "BMI_under_40",
                        "comorbidities_optimized",
                        "age_appropriate",
                    ],
                    "weak": [
                        "mild_arthritis",
                        "BMI_over_40",
                        "young_patient_without_AVN",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Hip and Groin Injury, Section 4.1: Total Hip Arthroplasty",
            },

            # -----------------------------------------------------------------
            # 5. Rotator Cuff Repair
            # -----------------------------------------------------------------
            "rotator_cuff_repair": {
                "name": "Rotator Cuff Repair (Arthroscopic or Open)",
                "cpt_codes": ["29827", "23410", "23412", "23420"],
                "icd10_codes": [
                    "M75.10", "M75.11", "M75.12", "M75.100", "M75.110", "M75.120",
                    "S46.011A", "S46.012A", "S46.019A",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "PT with rotator cuff strengthening, scapular stabilization, and ROM exercises",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["topical_analgesics", "acetaminophen"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["subacromial_corticosteroid"],
                        "description": "At least 1 subacromial injection with documented response",
                    },
                    "activity_modification": {
                        "min_weeks": 6,
                        "description": "Overhead activity restriction, ergonomic workplace modifications",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_shoulder"],
                    "conditional": ["plain_xrays_shoulder", "ultrasound_shoulder"],
                    "findings_required": [
                        "rotator_cuff_tear_partial_or_full_thickness",
                        "tear_size_and_retraction_documented",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["EMG_if_nerve_injury_suspected"],
                },
                "clinical_criteria": [
                    "MRI-confirmed rotator cuff tear (full-thickness or significant partial >50%)",
                    "Failed 6-12 weeks of conservative care for chronic tears",
                    "Acute traumatic full-thickness tear: surgery may proceed without prolonged conservative trial",
                    "Weakness in rotator cuff testing (supraspinatus, infraspinatus, subscapularis)",
                    "Functional impairment affecting work or daily activities",
                    "Age and tear reparability considered (massive retracted tears in elderly may not be reparable)",
                ],
                "exclusion_criteria": [
                    "Irreparable massive tear with fatty infiltration (Goutallier Grade 3-4)",
                    "Advanced cuff tear arthropathy (reverse shoulder replacement may be indicated)",
                    "Active infection",
                    "Frozen shoulder (address ROM first)",
                    "Active tobacco use (relative — delays healing)",
                ],
                "approval_factors": {
                    "strong": [
                        "full_thickness_tear_on_MRI",
                        "acute_traumatic_tear",
                        "failed_conservative_6_weeks",
                        "weakness_on_exam",
                        "work_related_functional_loss",
                    ],
                    "moderate": [
                        "significant_partial_tear_over_50_percent",
                        "failed_injection",
                        "young_active_patient",
                    ],
                    "weak": [
                        "small_partial_tear",
                        "elderly_with_massive_retracted_tear",
                        "tendinopathy_without_tear",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Shoulder Injury, Section 4.3: Rotator Cuff Repair",
            },

            # -----------------------------------------------------------------
            # 6. Shoulder Arthroscopy
            # -----------------------------------------------------------------
            "shoulder_arthroscopy": {
                "name": "Shoulder Arthroscopy (Labrum Repair / Subacromial Decompression / Distal Clavicle Excision)",
                "cpt_codes": ["29806", "29807", "29822", "29823", "29824", "29826"],
                "icd10_codes": [
                    "M75.00", "M75.01", "M75.02",
                    "S43.401A", "S43.402A", "S43.409A",
                    "M75.40", "M75.41", "M75.42",
                    "M19.011", "M19.012",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 6,
                        "min_sessions": 12,
                        "description": "PT with rotator cuff and scapular strengthening, ROM restoration, and functional training",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["muscle_relaxants", "topical_analgesics"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["subacromial_corticosteroid", "intra_articular_corticosteroid"],
                        "description": "At least 1 injection with documented response",
                    },
                    "activity_modification": {
                        "min_weeks": 6,
                        "description": "Overhead activity restriction and ergonomic modification",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": ["MRI_shoulder"],
                    "conditional": ["plain_xrays_shoulder", "MR_arthrogram"],
                    "findings_required": [
                        "labral_tear_or_impingement_pathology",
                        "correlation_with_clinical_presentation",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["diagnostic_lidocaine_injection_for_impingement"],
                },
                "clinical_criteria": [
                    "Labral tear: recurrent instability or positive labral tests (O'Brien, crank, apprehension)",
                    "OR subacromial impingement: failed 6 weeks conservative with positive impingement signs",
                    "OR AC joint arthritis: failed injection, positive cross-body adduction",
                    "MRI or MR arthrogram confirming pathology",
                    "Failed minimum 6 weeks of conservative care",
                    "Functional limitation documented",
                ],
                "exclusion_criteria": [
                    "Frozen shoulder (address ROM first with PT or MUA)",
                    "Active infection",
                    "Degenerative labral changes without instability (age-related, not surgical)",
                    "Impingement responding to conservative care",
                ],
                "approval_factors": {
                    "strong": [
                        "recurrent_instability_events",
                        "MRI_confirmed_labral_tear",
                        "failed_conservative_6_weeks",
                        "positive_clinical_tests",
                        "young_active_patient",
                    ],
                    "moderate": [
                        "failed_injection",
                        "impingement_with_positive_diagnostic_injection",
                        "functional_limitation",
                    ],
                    "weak": [
                        "degenerative_labral_changes",
                        "impingement_without_failed_conservative",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Shoulder Injury, Section 4.1: Shoulder Arthroscopy",
            },

            # -----------------------------------------------------------------
            # 7. Carpal Tunnel Release
            # -----------------------------------------------------------------
            "carpal_tunnel_release": {
                "name": "Carpal Tunnel Release (Open or Endoscopic)",
                "cpt_codes": ["64721", "29848"],
                "icd10_codes": [
                    "G56.00", "G56.01", "G56.02",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 4,
                        "min_sessions": 6,
                        "description": "Hand therapy with nerve gliding exercises, splint use education, and ergonomic training",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["oral_steroids_taper", "vitamin_B6"],
                        "min_duration_weeks": 4,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["carpal_tunnel_corticosteroid"],
                        "description": "At least 1 carpal tunnel corticosteroid injection with documented response",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Night splinting, ergonomic workplace modifications, activity modification",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["plain_xrays_wrist", "ultrasound_carpal_tunnel", "MRI_wrist"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["EMG_NCS_confirming_median_neuropathy"],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "EMG/NCS confirming median neuropathy at the wrist",
                    "Symptoms consistent with CTS (numbness/tingling in median distribution)",
                    "Positive Phalen and/or Tinel signs",
                    "Failed minimum 6 weeks of conservative care including splinting and injection",
                    "If thenar atrophy or severe EMG findings, may proceed with reduced conservative trial",
                    "Night symptoms and functional impairment",
                ],
                "exclusion_criteria": [
                    "Normal EMG/NCS (surgery generally not indicated)",
                    "Cervical radiculopathy mimicking CTS (double crush must be evaluated)",
                    "Active infection",
                    "Acute inflammatory arthritis in wrist",
                ],
                "approval_factors": {
                    "strong": [
                        "positive_EMG_NCS",
                        "thenar_atrophy",
                        "failed_splinting_and_injection",
                        "severe_NCS_findings",
                        "night_symptoms",
                    ],
                    "moderate": [
                        "positive_Phalen_Tinel",
                        "failed_conservative_6_weeks",
                        "functional_work_limitation",
                    ],
                    "weak": [
                        "mild_NCS_findings",
                        "symptoms_only_without_objective_findings",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Hand, Wrist, and Forearm, Section 4.1: Carpal Tunnel Release",
            },

            # -----------------------------------------------------------------
            # 8. Ankle Fracture ORIF
            # -----------------------------------------------------------------
            "ankle_fracture_orif": {
                "name": "Ankle Fracture Open Reduction Internal Fixation (ORIF)",
                "cpt_codes": ["27766", "27769", "27792", "27814", "27822", "27823", "27826", "27827", "27828"],
                "icd10_codes": [
                    "S82.51XA", "S82.52XA", "S82.53XA",
                    "S82.61XA", "S82.62XA", "S82.63XA",
                    "S82.101A", "S82.102A",
                    "S82.891A", "S82.892A",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "PT not required pre-operatively for acute displaced fractures",
                    },
                    "medications": {
                        "required": ["analgesics"],
                        "optional": ["NSAIDs_after_acute_phase"],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Injections not applicable for acute fracture management",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Immobilization and non-weight-bearing as fracture management",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": ["plain_xrays_ankle_AP_lateral_mortise"],
                    "conditional": ["CT_ankle_for_complex_fractures", "MRI_if_ligament_injury_suspected"],
                    "findings_required": [
                        "displaced_ankle_fracture_requiring_fixation",
                        "fracture_pattern_classification_documented",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": ["vascular_assessment_if_dislocation"],
                },
                "clinical_criteria": [
                    "Displaced ankle fracture not reducible to acceptable alignment with closed reduction",
                    "OR bimalleolar or trimalleolar fracture (generally require ORIF)",
                    "OR fracture-dislocation of the ankle",
                    "OR unstable fracture pattern (Weber B with medial injury, Weber C)",
                    "OR lateral malleolus displaced >2mm",
                    "Neurovascular status documented",
                    "Surgery typically within 2 weeks of injury (sooner if dislocation)",
                ],
                "exclusion_criteria": [
                    "Non-displaced stable fracture (cast treatment appropriate)",
                    "Severe peripheral vascular disease precluding healing",
                    "Active infection or severe soft tissue compromise (may need staged approach)",
                    "Medical instability precluding surgery",
                ],
                "approval_factors": {
                    "strong": [
                        "displaced_fracture_on_xray",
                        "bimalleolar_or_trimalleolar_pattern",
                        "fracture_dislocation",
                        "failed_closed_reduction",
                        "unstable_pattern",
                    ],
                    "moderate": [
                        "lateral_malleolus_displacement_over_2mm",
                        "acute_injury",
                    ],
                    "weak": [
                        "minimally_displaced_stable_pattern",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Ankle and Foot, Section 4.1: Ankle Fracture ORIF",
            },

            # -----------------------------------------------------------------
            # 9. Achilles Tendon Repair
            # -----------------------------------------------------------------
            "achilles_repair": {
                "name": "Achilles Tendon Repair (Open or Percutaneous)",
                "cpt_codes": ["27650", "27652", "27654"],
                "icd10_codes": [
                    "S86.011A", "S86.012A", "S86.019A",
                    "S86.091A", "S86.092A",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "PT not required pre-operatively for acute complete rupture — immediate surgical referral indicated",
                    },
                    "medications": {
                        "required": ["analgesics"],
                        "optional": ["NSAIDs"],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Injections contraindicated for acute Achilles rupture",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Splinting or walking boot for immobilization before surgery",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["MRI_ankle_if_diagnosis_uncertain", "ultrasound_Achilles"],
                    "findings_required": [
                        "complete_or_near_complete_Achilles_rupture_clinical_or_imaging",
                    ],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Clinical diagnosis of complete Achilles tendon rupture (palpable gap, positive Thompson test)",
                    "OR imaging-confirmed complete rupture if clinical exam equivocal",
                    "Active, working-age patient (surgical repair generally preferred)",
                    "Surgery ideally within 2 weeks of injury",
                    "Chronic rupture (>4 weeks) may require reconstruction with tendon transfer",
                    "Non-operative management acceptable for select patients (elderly, sedentary, high surgical risk)",
                ],
                "exclusion_criteria": [
                    "Severe peripheral vascular disease",
                    "Active infection at surgical site",
                    "Medical instability precluding surgery",
                    "Elderly sedentary patient (may manage non-operatively)",
                    "Recent fluoroquinolone use (does not exclude but increases risk)",
                ],
                "approval_factors": {
                    "strong": [
                        "complete_rupture_clinical_or_imaging",
                        "positive_Thompson_test",
                        "active_working_patient",
                        "acute_injury_under_2_weeks",
                    ],
                    "moderate": [
                        "work_related_injury",
                        "MRI_confirmed_rupture",
                    ],
                    "weak": [
                        "partial_tear",
                        "chronic_rupture_over_4_weeks",
                    ],
                },
                "global_period_days": 90,
                "mtg_reference": "NYS WCB MTG - Ankle and Foot, Section 4.2: Achilles Tendon Repair",
            },

            # -----------------------------------------------------------------
            # 10. Trigger Finger Release
            # -----------------------------------------------------------------
            "trigger_finger_release": {
                "name": "Trigger Finger Release (Open or Percutaneous)",
                "cpt_codes": ["26055", "26060"],
                "icd10_codes": [
                    "M65.30", "M65.311", "M65.312", "M65.319",
                    "M65.321", "M65.322", "M65.329",
                    "M65.331", "M65.332", "M65.339",
                    "M65.341", "M65.342", "M65.349",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 2,
                        "min_sessions": 4,
                        "description": "Hand therapy with tendon gliding exercises and splinting",
                    },
                    "medications": {
                        "required": ["NSAIDs"],
                        "optional": ["topical_analgesics"],
                        "min_duration_weeks": 2,
                    },
                    "injections": {
                        "min_attempts": 1,
                        "types": ["tendon_sheath_corticosteroid"],
                        "description": "At least 1 corticosteroid injection into the tendon sheath — up to 2 attempts before surgery",
                    },
                    "activity_modification": {
                        "min_weeks": 4,
                        "description": "Splinting in extension, activity modification to reduce repetitive gripping",
                    },
                    "total_conservative_duration_weeks": 6,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["plain_xrays_hand", "ultrasound_tendon"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": [],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Clinical diagnosis of trigger finger (catching, locking, or clicking of the digit)",
                    "Failed at least 1 corticosteroid injection",
                    "Locked digit that cannot be passively extended (may proceed directly to surgery)",
                    "Failed minimum 6 weeks of conservative care including splinting",
                    "Thumb triggering: may have lower threshold for surgery given functional impact",
                    "Recurrent triggering after 2 injections is indication for release",
                ],
                "exclusion_criteria": [
                    "Active infection",
                    "No clinical triggering on exam (diagnosis uncertain)",
                    "Trigger finger responding to injection (continue conservative)",
                ],
                "approval_factors": {
                    "strong": [
                        "locked_digit",
                        "failed_2_injections",
                        "persistent_triggering",
                        "functional_limitation",
                    ],
                    "moderate": [
                        "failed_1_injection",
                        "thumb_involvement",
                        "failed_splinting",
                    ],
                    "weak": [
                        "intermittent_catching_only",
                        "no_injection_trial",
                    ],
                },
                "global_period_days": 10,
                "mtg_reference": "NYS WCB MTG - Hand, Wrist, and Forearm, Section 4.3: Trigger Finger Release",
            },
        },
    },

    # =========================================================================
    # CONCUSSION / TRAUMATIC BRAIN INJURY — 8 procedures
    # =========================================================================
    "concussion": {
        "category": "Concussion / Traumatic Brain Injury",
        "procedures": {
            # -----------------------------------------------------------------
            # 1. Neuropsychological Testing
            # -----------------------------------------------------------------
            "neuropsychological_testing": {
                "name": "Neuropsychological Testing (Comprehensive Battery)",
                "cpt_codes": ["96132", "96133", "96136", "96137", "96138", "96139", "96146"],
                "icd10_codes": [
                    "S06.0X0A", "S06.0X1A", "S06.0X9A",
                    "S06.0X0D", "S06.0X1D",
                    "F07.81", "R41.840", "R41.841", "R41.3",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "PT not required prior to neuropsychological testing",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Cognitive rest and gradual return to activity protocol should be in place",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["CT_head_if_acute", "MRI_brain_if_prolonged_symptoms"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["documented_concussion_or_TBI_diagnosis"],
                    "conditional": ["neurology_evaluation"],
                },
                "clinical_criteria": [
                    "Documented concussion or TBI with persistent cognitive symptoms beyond 4 weeks",
                    "Cognitive complaints affecting work, school, or daily functioning",
                    "Testing performed by licensed neuropsychologist",
                    "Baseline testing: may be approved for established diagnosis with cognitive complaints",
                    "Repeat testing: generally not before 6 months unless clinical change",
                    "Testing to guide cognitive rehabilitation planning",
                    "Assessment of effort/validity measures required to ensure reliable results",
                    "Maximum 8 hours of testing (face-to-face) per evaluation",
                ],
                "exclusion_criteria": [
                    "Active substance intoxication",
                    "Acute medical delirium",
                    "Less than 2 weeks post-injury (too early for reliable assessment)",
                    "Repeat testing within 6 months without clinical justification",
                    "Testing solely for litigation purposes (not medically indicated)",
                ],
                "approval_factors": {
                    "strong": [
                        "persistent_cognitive_symptoms_over_4_weeks",
                        "documented_TBI",
                        "cognitive_functional_impairment",
                        "referral_from_treating_physician",
                        "first_evaluation",
                    ],
                    "moderate": [
                        "planning_cognitive_rehabilitation",
                        "return_to_work_assessment",
                        "baseline_established",
                    ],
                    "weak": [
                        "symptoms_less_than_4_weeks",
                        "repeat_testing_within_6_months",
                        "litigation_context_only",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "max_hours_per_evaluation": 8,
                    "min_interval_months": 6,
                },
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 3.2: Neuropsychological Assessment",
            },

            # -----------------------------------------------------------------
            # 2. Cognitive Rehabilitation
            # -----------------------------------------------------------------
            "cognitive_rehabilitation": {
                "name": "Cognitive Rehabilitation Therapy",
                "cpt_codes": ["97129", "97130", "97110", "97530"],
                "icd10_codes": [
                    "S06.0X0D", "S06.0X1D", "S06.0X9D",
                    "F07.81", "R41.840", "R41.841", "R41.3",
                    "R41.0", "G31.84",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Cognitive rehabilitation IS the conservative treatment for cognitive deficits",
                    },
                    "medications": {
                        "required": [],
                        "optional": ["cognitive_enhancers_if_prescribed"],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 2,
                        "description": "Cognitive rest followed by graduated return to cognitive activity",
                    },
                    "total_conservative_duration_weeks": 2,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["MRI_brain", "CT_head"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["documented_TBI_with_cognitive_deficits"],
                    "conditional": ["neuropsychological_testing_recommended_before_starting"],
                },
                "clinical_criteria": [
                    "Documented TBI or concussion with persistent cognitive deficits",
                    "Neuropsychological testing demonstrating measurable cognitive impairment (recommended)",
                    "Deficits in attention, memory, executive function, or processing speed",
                    "Cognitive deficits affecting functional activities and/or return to work",
                    "Treatment by qualified provider (neuropsychologist, speech-language pathologist, occupational therapist)",
                    "Initial authorization: typically 12-16 sessions over 6-8 weeks",
                    "Continued authorization requires documented progress toward functional goals",
                    "Maximum duration: typically 6 months, extensions with documentation of ongoing progress",
                ],
                "exclusion_criteria": [
                    "No documented cognitive deficits on testing",
                    "Pre-existing cognitive disorder unrelated to work injury",
                    "Plateau in progress without functional improvement",
                    "Non-compliance with treatment program",
                ],
                "approval_factors": {
                    "strong": [
                        "neuropsych_testing_showing_deficits",
                        "documented_TBI",
                        "functional_cognitive_impairment",
                        "initial_authorization",
                        "qualified_provider",
                    ],
                    "moderate": [
                        "documented_progress_for_continuation",
                        "return_to_work_goal",
                        "measurable_improvement",
                    ],
                    "weak": [
                        "no_neuropsych_testing_done",
                        "symptoms_only_without_objective_deficits",
                        "treatment_plateau",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "initial_sessions": 16,
                    "initial_duration_weeks": 8,
                    "max_duration_months": 6,
                    "reassess_every_sessions": 8,
                },
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 4.1: Cognitive Rehabilitation",
            },

            # -----------------------------------------------------------------
            # 3. Vestibular Rehabilitation
            # -----------------------------------------------------------------
            "vestibular_rehabilitation": {
                "name": "Vestibular Rehabilitation Therapy (VRT)",
                "cpt_codes": ["97110", "97112", "97530", "97750", "92507", "92508"],
                "icd10_codes": [
                    "S06.0X0D", "S06.0X1D",
                    "H81.10", "H81.11", "H81.12", "H81.13",
                    "H81.391", "H81.392", "H81.393",
                    "R42", "H83.2X1", "H83.2X2",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Vestibular rehabilitation IS the treatment — no prior PT required",
                    },
                    "medications": {
                        "required": [],
                        "optional": ["meclizine_short_term", "ondansetron_for_nausea"],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 1,
                        "description": "Initial vestibular symptom management and graded activity protocol",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["MRI_brain_if_central_cause_suspected", "CT_temporal_bones"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["vestibular_assessment_documenting_dysfunction"],
                    "conditional": [
                        "videonystagmography_VNG",
                        "balance_platform_testing",
                        "BPPV_testing_Dix_Hallpike",
                        "audiometry_if_hearing_complaints",
                    ],
                },
                "clinical_criteria": [
                    "Documented vestibular dysfunction following TBI/concussion",
                    "Dizziness, imbalance, or vertigo persisting beyond 2 weeks post-injury",
                    "Vestibular testing confirming peripheral or central vestibular deficit",
                    "BPPV: canalith repositioning maneuvers (Epley, Semont) as initial treatment",
                    "Treatment by qualified vestibular therapist (PT or OT with vestibular training)",
                    "Initial authorization: 8-12 sessions over 4-6 weeks",
                    "Continuation requires documented improvement in vestibular function",
                    "Home exercise program compliance documented",
                ],
                "exclusion_criteria": [
                    "Active CNS pathology requiring neurosurgical intervention",
                    "Unstable medical condition causing dizziness (cardiac, metabolic)",
                    "Medication-induced dizziness (address medication first)",
                    "No vestibular deficit on testing",
                ],
                "approval_factors": {
                    "strong": [
                        "positive_vestibular_testing",
                        "documented_TBI_with_vestibular_symptoms",
                        "BPPV_confirmed",
                        "functional_balance_deficit",
                        "initial_authorization",
                    ],
                    "moderate": [
                        "dizziness_persisting_over_2_weeks",
                        "qualified_vestibular_therapist",
                        "documented_progress",
                    ],
                    "weak": [
                        "subjective_dizziness_without_objective_findings",
                        "symptoms_less_than_2_weeks",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "initial_sessions": 12,
                    "initial_duration_weeks": 6,
                    "reassess_every_sessions": 6,
                },
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 4.2: Vestibular Rehabilitation",
            },

            # -----------------------------------------------------------------
            # 4. Vision Therapy (Post-Concussion)
            # -----------------------------------------------------------------
            "vision_therapy": {
                "name": "Vision Therapy / Neuro-Optometric Rehabilitation",
                "cpt_codes": ["92065", "92066", "92540", "92060"],
                "icd10_codes": [
                    "H53.2", "H53.30", "H53.31", "H53.32", "H53.33",
                    "H49.00", "H49.10", "H49.20",
                    "H51.11", "H51.12", "H50.9",
                    "S06.0X0D", "S06.0X1D",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Vision therapy is the specific treatment — no prior general PT required",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 1,
                        "description": "Screen time limitation, reading breaks, tinted lenses if photosensitive",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["MRI_brain_orbits_if_cranial_nerve_palsy"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["comprehensive_neuro_optometric_evaluation"],
                    "conditional": ["visual_field_testing", "OCT"],
                },
                "clinical_criteria": [
                    "Documented TBI or concussion with persistent visual symptoms",
                    "Neuro-optometric evaluation confirming oculomotor dysfunction, convergence insufficiency, or accommodative dysfunction",
                    "Visual symptoms affecting reading, screen use, or functional activities",
                    "Treatment by qualified neuro-optometrist or vision therapist",
                    "Initial authorization: 12-16 sessions over 6-8 weeks",
                    "Continuation requires documented measurable improvement in visual function",
                    "Home exercises prescribed and compliance documented",
                ],
                "exclusion_criteria": [
                    "Pre-existing visual disorder unrelated to injury",
                    "Structural eye pathology requiring ophthalmologic surgery",
                    "No measurable oculomotor deficit on testing",
                    "Non-compliance with home exercise program",
                ],
                "approval_factors": {
                    "strong": [
                        "documented_oculomotor_dysfunction",
                        "convergence_insufficiency_measured",
                        "post_TBI_visual_symptoms",
                        "neuro_optometric_evaluation_done",
                        "initial_authorization",
                    ],
                    "moderate": [
                        "functional_visual_impairment",
                        "qualified_provider",
                        "documented_improvement",
                    ],
                    "weak": [
                        "subjective_visual_complaints_only",
                        "no_objective_testing_done",
                    ],
                },
                "global_period_days": 0,
                "frequency_limits": {
                    "initial_sessions": 16,
                    "initial_duration_weeks": 8,
                    "reassess_every_sessions": 8,
                },
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 4.3: Vision Therapy",
            },

            # -----------------------------------------------------------------
            # 5. Specialist Referral — Neurology
            # -----------------------------------------------------------------
            "specialist_referral_neurology": {
                "name": "Neurology Specialist Referral and Evaluation",
                "cpt_codes": ["99243", "99244", "99245", "99213", "99214", "99215"],
                "icd10_codes": [
                    "S06.0X0A", "S06.0X1A", "S06.0X0D", "S06.0X1D",
                    "G43.909", "G43.911", "R51.0", "R51.9",
                    "G44.301", "G44.309", "G40.909",
                    "R56.9", "G93.1",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Not required before neurology referral",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable for initial referral",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Cognitive and physical rest protocol should be in place",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["CT_head_if_acute", "MRI_brain"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["documented_TBI_or_concussion"],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Concussion or TBI with symptoms not resolving within expected timeframe (2-4 weeks)",
                    "Post-traumatic headaches not responding to standard treatment",
                    "Suspected post-traumatic seizure or seizure-like events",
                    "Focal neurological deficits on examination",
                    "Persistent cognitive complaints requiring specialist assessment",
                    "Sleep disturbances post-TBI not responding to initial management",
                    "Referral within workers' compensation treatment framework",
                ],
                "exclusion_criteria": [
                    "Routine concussion resolving within normal timeframe (does not require specialist)",
                    "Symptoms clearly explained by non-neurological cause",
                ],
                "approval_factors": {
                    "strong": [
                        "persistent_symptoms_over_4_weeks",
                        "focal_neurological_deficit",
                        "post_traumatic_seizures",
                        "moderate_or_severe_TBI",
                        "treatment_not_responding",
                    ],
                    "moderate": [
                        "post_traumatic_headaches",
                        "sleep_disturbance",
                        "cognitive_complaints",
                    ],
                    "weak": [
                        "mild_concussion_resolving_normally",
                        "symptoms_under_2_weeks",
                    ],
                },
                "global_period_days": 0,
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 2.3: Specialist Referral — Neurology",
            },

            # -----------------------------------------------------------------
            # 6. Specialist Referral — Neuropsychology
            # -----------------------------------------------------------------
            "specialist_referral_neuropsychology": {
                "name": "Neuropsychology Specialist Referral and Evaluation",
                "cpt_codes": ["96132", "96133", "96136", "96137", "99244", "99245"],
                "icd10_codes": [
                    "S06.0X0D", "S06.0X1D", "F07.81",
                    "R41.840", "R41.841", "R41.3", "R41.0",
                    "F06.30", "F06.8",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Not required before neuropsychology referral",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Cognitive rest protocol should be in place",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["MRI_brain_if_not_already_done"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["documented_TBI_with_cognitive_or_behavioral_symptoms"],
                    "conditional": ["neurology_evaluation_recommended_first"],
                },
                "clinical_criteria": [
                    "Documented TBI with persistent cognitive or behavioral symptoms beyond 4 weeks",
                    "Cognitive complaints affecting work or daily functioning",
                    "Behavioral or emotional changes post-TBI requiring assessment",
                    "Need for cognitive rehabilitation treatment planning",
                    "Assessment of capacity for return to work or modified duty",
                    "Differentiation of TBI-related deficits from pre-existing or comorbid conditions",
                    "Evaluation by board-eligible or board-certified neuropsychologist",
                ],
                "exclusion_criteria": [
                    "Cognitive symptoms less than 2 weeks post-injury (too early)",
                    "Active substance intoxication during testing",
                    "Patient unable to cooperate with testing requirements",
                    "Testing solely for legal purposes without clinical indication",
                ],
                "approval_factors": {
                    "strong": [
                        "persistent_cognitive_symptoms_over_4_weeks",
                        "documented_TBI",
                        "functional_cognitive_impairment",
                        "return_to_work_planning",
                        "treatment_planning_purpose",
                    ],
                    "moderate": [
                        "behavioral_changes_post_TBI",
                        "neurology_referral_first",
                        "moderate_or_severe_TBI",
                    ],
                    "weak": [
                        "mild_concussion_symptoms_under_4_weeks",
                        "litigation_only_purpose",
                    ],
                },
                "global_period_days": 0,
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 2.4: Specialist Referral — Neuropsychology",
            },

            # -----------------------------------------------------------------
            # 7. CT Head Imaging
            # -----------------------------------------------------------------
            "imaging_ct_head": {
                "name": "CT Head (Non-Contrast and/or Contrast)",
                "cpt_codes": ["70450", "70460", "70470"],
                "icd10_codes": [
                    "S06.0X0A", "S06.0X1A", "S06.0X9A",
                    "S06.1X0A", "S06.2X0A", "S06.300A",
                    "S06.4X0A", "S06.5X0A", "S06.6X0A",
                    "S09.90XA", "R51.0", "R51.9",
                    "R41.0", "R55",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Not applicable — imaging is a diagnostic procedure",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Not applicable",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": [],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["clinical_indication_documented"],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "Acute head injury with any of the Canadian CT Head Rule criteria:",
                    "  - GCS <15 at 2 hours post-injury",
                    "  - Suspected open or depressed skull fracture",
                    "  - Signs of basilar skull fracture (raccoon eyes, Battle sign, CSF leak)",
                    "  - Two or more episodes of vomiting",
                    "  - Age >= 65 years",
                    "  - Amnesia before impact >= 30 minutes",
                    "  - Dangerous mechanism (pedestrian vs. vehicle, ejected from vehicle, fall > 3 feet)",
                    "Loss of consciousness with any high-risk feature",
                    "Focal neurological deficit on examination",
                    "Post-traumatic seizure",
                    "Anticoagulant use with head injury",
                    "Worsening symptoms after initial improvement",
                ],
                "exclusion_criteria": [
                    "Minor head injury with none of the above criteria (observation preferred)",
                    "GCS 15 with no risk factors (clinical observation appropriate)",
                    "Repeat CT without new symptoms or clinical change",
                ],
                "approval_factors": {
                    "strong": [
                        "GCS_below_15",
                        "focal_neurological_deficit",
                        "skull_fracture_suspected",
                        "post_traumatic_seizure",
                        "anticoagulant_use",
                        "loss_of_consciousness",
                    ],
                    "moderate": [
                        "vomiting",
                        "age_over_65",
                        "dangerous_mechanism",
                        "amnesia_over_30_minutes",
                    ],
                    "weak": [
                        "headache_only_GCS_15",
                        "no_risk_factors",
                    ],
                },
                "global_period_days": 0,
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 2.1: Diagnostic Imaging — CT Head",
            },

            # -----------------------------------------------------------------
            # 8. MRI Brain
            # -----------------------------------------------------------------
            "imaging_mri_brain": {
                "name": "MRI Brain (With and/or Without Contrast)",
                "cpt_codes": ["70551", "70552", "70553"],
                "icd10_codes": [
                    "S06.0X0D", "S06.0X1D", "S06.0X9D",
                    "S06.1X0D", "S06.2X0D", "S06.300D",
                    "F07.81", "G93.1", "R51.0",
                    "R41.840", "R41.3",
                ],
                "conservative_requirements": {
                    "physical_therapy": {
                        "min_weeks": 0,
                        "min_sessions": 0,
                        "description": "Not applicable — imaging is diagnostic",
                    },
                    "medications": {
                        "required": [],
                        "optional": [],
                        "min_duration_weeks": 0,
                    },
                    "injections": {
                        "min_attempts": 0,
                        "types": [],
                        "description": "Not applicable",
                    },
                    "activity_modification": {
                        "min_weeks": 0,
                        "description": "Not applicable",
                    },
                    "total_conservative_duration_weeks": 0,
                },
                "imaging_requirements": {
                    "required": [],
                    "conditional": ["CT_head_typically_done_first_in_acute_setting"],
                    "findings_required": [],
                },
                "diagnostic_requirements": {
                    "required": ["clinical_indication_documented"],
                    "conditional": [],
                },
                "clinical_criteria": [
                    "TBI with persistent neurological symptoms beyond expected recovery (typically >2-4 weeks)",
                    "Focal neurological deficits not explained by CT findings",
                    "Suspected diffuse axonal injury (DAI) not visible on CT",
                    "Post-traumatic seizures requiring further evaluation",
                    "Worsening cognitive or behavioral symptoms post-TBI",
                    "Pre-operative planning for neurosurgical intervention",
                    "CT showing abnormality requiring further characterization",
                    "Persistent post-concussive syndrome beyond 4 weeks requiring further workup",
                    "Not indicated as routine screening for uncomplicated mild concussion",
                ],
                "exclusion_criteria": [
                    "MRI contraindications (pacemaker, certain implants, severe claustrophobia unmanageable)",
                    "Routine uncomplicated mild concussion resolving normally",
                    "Repeat MRI without interval change in symptoms or new clinical findings",
                ],
                "approval_factors": {
                    "strong": [
                        "focal_neurological_deficit",
                        "CT_abnormality_needing_characterization",
                        "suspected_DAI",
                        "persistent_symptoms_over_4_weeks",
                        "post_traumatic_seizures",
                    ],
                    "moderate": [
                        "worsening_cognitive_symptoms",
                        "post_concussive_syndrome_4_weeks",
                        "neurosurgical_planning",
                    ],
                    "weak": [
                        "uncomplicated_mild_concussion",
                        "headache_only_without_neurological_signs",
                    ],
                },
                "global_period_days": 0,
                "mtg_reference": "NYS WCB MTG - Traumatic Brain Injury, Section 2.1: Diagnostic Imaging — MRI Brain",
            },
        },
    },
}


# =============================================================================
# Helper structures for cross-referencing and lookup
# =============================================================================

# Flat lookup: procedure_key -> (category_key, procedure_data)
_PROCEDURE_INDEX = {}
# CPT code lookup: cpt_code -> list of (category_key, procedure_key)
_CPT_INDEX = {}
# ICD-10 lookup: icd10_code -> list of (category_key, procedure_key)
_ICD10_INDEX = {}

for _cat_key, _cat_data in WCB_TREATMENT_GUIDELINES.items():
    for _proc_key, _proc_data in _cat_data["procedures"].items():
        _PROCEDURE_INDEX[_proc_key] = (_cat_key, _proc_data)
        for _cpt in _proc_data.get("cpt_codes", []):
            _CPT_INDEX.setdefault(_cpt, []).append((_cat_key, _proc_key))
        for _icd in _proc_data.get("icd10_codes", []):
            _ICD10_INDEX.setdefault(_icd, []).append((_cat_key, _proc_key))


def get_procedure(procedure_key: str) -> dict | None:
    """Return procedure data by key, or None if not found."""
    entry = _PROCEDURE_INDEX.get(procedure_key)
    return entry[1] if entry else None


def get_category_for_procedure(procedure_key: str) -> str | None:
    """Return the category key (spine, orthopedic, concussion) for a procedure."""
    entry = _PROCEDURE_INDEX.get(procedure_key)
    return entry[0] if entry else None


def find_procedures_by_cpt(cpt_code: str) -> list[tuple[str, str]]:
    """Return list of (category_key, procedure_key) matching a CPT code."""
    return _CPT_INDEX.get(cpt_code, [])


def find_procedures_by_icd10(icd10_code: str) -> list[tuple[str, str]]:
    """Return list of (category_key, procedure_key) matching an ICD-10 code.
    Supports exact match and wildcard prefix matching.
    """
    results = _ICD10_INDEX.get(icd10_code, [])
    if not results:
        # Try prefix matching (for codes stored with wildcards like M43.1*)
        for stored_code, entries in _ICD10_INDEX.items():
            if stored_code.endswith("*") and icd10_code.startswith(stored_code[:-1]):
                results.extend(entries)
            elif icd10_code.startswith(stored_code.rstrip("*")):
                # Also match if the stored code is a prefix
                pass  # Only match explicit wildcards
    return results


def get_all_procedure_keys() -> list[str]:
    """Return all procedure keys."""
    return list(_PROCEDURE_INDEX.keys())


def get_all_categories() -> list[dict]:
    """Return summary of all categories with their procedures."""
    result = []
    for cat_key, cat_data in WCB_TREATMENT_GUIDELINES.items():
        procs = []
        for proc_key, proc_data in cat_data["procedures"].items():
            procs.append({
                "key": proc_key,
                "name": proc_data["name"],
                "cpt_codes": proc_data["cpt_codes"],
            })
        result.append({
            "category_key": cat_key,
            "category_name": cat_data["category"],
            "procedure_count": len(procs),
            "procedures": procs,
        })
    return result
