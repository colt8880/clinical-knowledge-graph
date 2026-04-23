// Cross-guideline MODIFIES edges: KDIGO 2024 CKD → ADA 2024 Diabetes.
//
// Clinician-reviewed 2026-04-23. Only edges with explicit sign-off are included.
// Review document: docs/review/cross-edges-ada.md
// Reviewer: Colton Ortolf
//
// Pattern: KDIGO provides CKD-specific guidance that adjusts how ADA
// recommendations should be applied for the CKD overlap population.
// These are complementary (not competing) recommendations where KDIGO's
// renal expertise informs ADA's diabetes management.
//
// 2 edges total (M1–M2 from the review document).
//
// No PREEMPTED_BY edges: ADA doesn't preempt other guidelines (it's
// complementary). Statin overlap with ACC/AHA is convergence, handled by
// shared entity layer. USPSTF preemption already handled by existing
// ACC/AHA edges (P1-P6 in cross-edges-uspstf-accaha.cypher).

// --- M1: KDIGO SGLT2i modifies ADA intensification (agent preference) ---
// Overlap: adults 18+ with T2DM, A1C >= 7%, on metformin, eGFR 20–<60 or
// albuminuria (ACR >= 200). KDIGO's SGLT2i rec (1A) provides a CKD-specific
// preference signal for ADA's intensification agent selection.
MATCH (source:Recommendation {id: 'rec:kdigo-sglt2-for-ckd'})
MATCH (target:Recommendation {id: 'rec:ada-intensification'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'agent_preference',
  r.note = 'KDIGO 2024 (1A) independently recommends SGLT2i for CKD with T2DM or significant albuminuria. When a patient has CKD + uncontrolled diabetes requiring intensification, SGLT2i should be preferred over other intensification agents (GLP-1 RA, insulin) because the cardiorenal benefit is independently indicated. ADA lists multiple agents without CKD-specific preference; KDIGO provides that preference signal.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-23',
  r.provenance_source = 'cross-edges-ada',
  r.provenance_date = '2026-04-23';

// --- M2: KDIGO CKD monitoring modifies ADA metformin first-line (dose adjustment) ---
// Overlap: adults 18+ with T2DM, eGFR 15–<60 (CKD G3–G5). KDIGO eGFR
// monitoring output feeds ADA metformin dosing: eGFR < 45 requires dose
// reduction; eGFR < 30 contraindicates metformin.
MATCH (source:Recommendation {id: 'rec:kdigo-ckd-monitoring'})
MATCH (target:Recommendation {id: 'rec:ada-metformin-first-line'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'dose_adjustment',
  r.note = 'KDIGO 2024 CKD monitoring (eGFR and urine ACR tracking) directly informs ADA metformin dosing. eGFR < 45 mL/min/1.73m2 requires metformin dose reduction; eGFR < 30 contraindicates metformin entirely. This is a cross-domain dependency: one guideline''s monitoring output feeds another guideline''s dosing decision.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-23',
  r.provenance_source = 'cross-edges-ada',
  r.provenance_date = '2026-04-23';
