// Cross-guideline MODIFIES edges: KDIGO 2024 CKD → ACC/AHA 2018 Cholesterol.
//
// Clinician-reviewed 2026-04-21. Only edges with explicit sign-off are included.
// Review document: docs/review/cross-edges.md
// Reviewer: Colton Ortolf
//
// Pattern: KDIGO recommends moderate-intensity statins for CKD G3–G5 due to
// altered pharmacokinetics and increased myopathy risk. When an ACC/AHA rec
// calls for high-intensity, the KDIGO rec modifies it to moderate intensity
// for the CKD overlap population.
//
// 2 edges total (M1–M2 from the review document).

// --- M1: KDIGO CKD statin modifies ACC/AHA secondary prevention intensity ---
// Overlap: adults 50–75 with established ASCVD, eGFR 15–<60
MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 (1A) recommends moderate-intensity statin in CKD G3-G5 not on dialysis due to altered pharmacokinetics and increased myopathy risk. Overrides ACC/AHA high-intensity default for the CKD overlap population. Consider renal dosing adjustments.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-21';

// --- M2: KDIGO CKD statin modifies ACC/AHA severe hypercholesterolemia intensity ---
// Overlap: adults 50–75 with LDL ≥ 190, eGFR 15–<60, no established ASCVD
MATCH (source:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MATCH (target:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (source)-[r:MODIFIES]->(target)
ON CREATE SET
  r.nature = 'intensity_reduction',
  r.note = 'KDIGO 2024 (1A) recommends moderate-intensity statin in CKD G3-G5 not on dialysis due to altered pharmacokinetics and increased myopathy risk. Overrides ACC/AHA high-intensity default for the CKD overlap population. Consider renal dosing adjustments.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-kdigo',
  r.provenance_date = '2026-04-21';
