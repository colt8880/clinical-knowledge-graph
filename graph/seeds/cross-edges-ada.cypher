// Cross-guideline MODIFIES edge: KDIGO 2024 CKD → ADA 2024 Diabetes.
//
// Clinician-reviewed 2026-04-23. Only edges with explicit sign-off are included.
// Review document: docs/review/cross-edges-ada.md
// Reviewer: Colton Ortolf
//
// Pattern: KDIGO provides CKD-specific guidance that adjusts how ADA
// recommendations should be applied for the CKD overlap population.
//
// 1 edge total (M1 from the review document).
//
// Original review approved 2 MODIFIES edges, but M1 (KDIGO SGLT2i → ADA
// intensification) used nature=agent_preference which is not in the ADR 0019
// enum. Reclassified to convergence — the shared entity layer handles the
// SGLT2i overlap, and the evaluator fires both recs for the overlap patient.
//
// No PREEMPTED_BY edges: ADA doesn't preempt other guidelines (it's
// complementary). Statin overlap with ACC/AHA is convergence, handled by
// shared entity layer. USPSTF preemption already handled by existing
// ACC/AHA edges (P1-P6 in cross-edges-uspstf-accaha.cypher).

// --- M1: KDIGO CKD monitoring modifies ADA metformin first-line (dose adjustment) ---
// Overlap: adults 18+ with T2DM, eGFR 15–<60 (CKD G3–G5). KDIGO eGFR
// monitoring output feeds ADA metformin dosing: eGFR < 45 requires dose
// reduction; eGFR < 30 contraindicates metformin.
MATCH (source:Recommendation {id: 'rec:kdigo-ckd-monitoring'})
MATCH (target:Recommendation {id: 'rec:ada-metformin-first-line'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'dose_adjustment',
  r.note = 'KDIGO 2024 CKD monitoring (eGFR and urine ACR tracking) directly informs ADA metformin dosing. eGFR < 45 mL/min/1.73m2 requires metformin dose reduction; eGFR < 30 contraindicates metformin entirely. This is a cross-domain dependency: one guidelines monitoring output feeds another guidelines dosing decision.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-23',
  r.provenance_source = 'cross-edges-ada',
  r.provenance_date = '2026-04-23';
