// Cross-guideline MODIFIES edges: KDIGO 2024 CKD → USPSTF 2022 Statins and ACC/AHA 2018 Cholesterol.
//
// Per ADR 0019 (MODIFIES edge semantics): MODIFIES is additive, not gating.
// The target Rec still fires; the modifier annotates. Direction is FROM the
// modifying Rec TO the modified Rec or Strategy.
//
// MODIFIES only activates when both the source and target Recs match the
// patient. A source Rec that does not match does not modify.
//
// Preemption takes precedence: if the target Rec is preempted, its modifiers
// are not emitted (ADR 0019).
//
// Seven edges covering three clinical scenarios:
//
//   1. CKD + ACC/AHA secondary prevention: KDIGO statin-for-CKD modifies
//      ACC/AHA high-intensity statin to moderate-intensity. Patient has
//      ASCVD + CKD G3-G5; KDIGO says moderate-intensity in advanced CKD.
//
//   2. CKD + ACC/AHA severe hypercholesterolemia: same pattern for LDL ≥190.
//      ACC/AHA recommends high-intensity; KDIGO modifies to moderate in CKD.
//
//   3. CKD + ACC/AHA primary prevention: ACC/AHA R4 may recommend
//      moderate-to-high-intensity. KDIGO surfaces CKD context and modifies
//      intensity to moderate.
//
//   4. CKD + ACC/AHA diabetes: ACC/AHA R3 recommends moderate-intensity with
//      high-intensity option for risk ≥7.5%. KDIGO modifies high-intensity
//      option to moderate.
//
//   5. CKD + USPSTF Grade B: USPSTF recommends moderate-intensity statin.
//      KDIGO reinforces moderate-intensity and surfaces CKD-specific context
//      (renal dosing considerations, drug interactions).
//
//   6. CKD + USPSTF Grade C: same CKD context surfaced for shared
//      decision-making patients.
//
// Apply order: constraints → clinical-entities → statins → cholesterol
//              → kdigo-ckd → cross-edges-uspstf-accaha → this file.
//
// See docs/reference/guidelines/cross-guideline-map.md for the full table.

// ---------------------------------------------------------------------------
// Scenario 1: CKD + ACC/AHA secondary prevention (high-intensity → moderate)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5 not on dialysis. ACC/AHA secondary prevention recommends high-intensity statin. In patients with both ASCVD and CKD G3-G5, reduce intensity to moderate per KDIGO. Consider renal dosing adjustments and drug interactions.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 2: CKD + ACC/AHA severe hypercholesterolemia (high-intensity → moderate)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5. ACC/AHA recommends high-intensity for LDL ≥190. In patients with severe hypercholesterolemia and CKD G3-G5, KDIGO modifies to moderate intensity. Balance LDL reduction against CKD-related drug metabolism changes.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 3: CKD + ACC/AHA primary prevention (moderate-to-high → moderate)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5. ACC/AHA primary prevention may recommend moderate-to-high intensity based on ASCVD risk. In patients with CKD G3-G5, cap intensity at moderate per KDIGO guidance.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 4: CKD + ACC/AHA diabetes (high-intensity option → moderate)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5. ACC/AHA recommends moderate-intensity for diabetic adults 40-75 with high-intensity option when ASCVD risk ≥7.5%. In CKD G3-G5 patients with diabetes, restrict to moderate intensity per KDIGO.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 5: CKD + USPSTF Grade B (surface CKD context)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:statin-initiate-grade-b'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5. USPSTF Grade B recommends moderate-intensity statin for primary prevention. While both align on moderate intensity, KDIGO provides additional CKD-specific context: renal dosing considerations, avoidance of certain statin-drug interactions in CKD, and monitoring of eGFR during therapy.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 6: CKD + USPSTF Grade C (surface CKD context for shared decision)
// ---------------------------------------------------------------------------

MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:statin-selective-grade-c'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 recommends moderate-intensity statin in CKD G3-G5. USPSTF Grade C requires shared decision-making for patients with ASCVD risk 7.5-<10%. CKD context should inform the shared decision: moderate intensity is appropriate, and CKD itself is a cardiovascular risk enhancer that may favor statin initiation.',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-17';
