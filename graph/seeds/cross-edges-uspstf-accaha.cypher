// Cross-guideline PREEMPTED_BY edges: USPSTF 2022 Statins ↔ ACC/AHA 2018 Cholesterol.
//
// Clinician-reviewed 2026-04-21. Only edges with explicit sign-off are included.
// Review document: docs/review/cross-edges.md
// Reviewer: Colton Ortolf
//
// Pattern: ACC/AHA (specialty society, priority 200) preempts USPSTF (federal
// task force, priority 100) for the overlapping statin-eligible population.
// Per ADR 0018 preemption precedence rules.
//
// 6 edges total (P1–P6 from the review document).

// --- P1: ACC/AHA diabetes statin preempts USPSTF Grade B ---
// Overlap: adults 40–75 with diabetes, CVD risk factor, ASCVD 10yr ≥ 10%
MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA diabetes-specific statin rec (COR I, LOE A) provides more targeted guidance than USPSTF Grade B population screen for the diabetes overlap population. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';

// --- P2: ACC/AHA diabetes statin preempts USPSTF Grade C ---
// Overlap: adults 40–75 with diabetes, CVD risk factor, ASCVD 10yr 7.5–<10%
MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA diabetes-specific statin rec (COR I, LOE A) provides more targeted guidance than USPSTF Grade C shared-decision screen for the diabetes overlap population. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';

// --- P3: ACC/AHA primary prevention statin preempts USPSTF Grade B ---
// Overlap: adults 40–75, LDL 70–189, ASCVD 10yr ≥ 10%, CVD risk factor, no diabetes
MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA primary prevention statin rec (COR I, LOE A) with LDL/risk stratification is more specific than USPSTF Grade B population screen. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';

// --- P4: ACC/AHA primary prevention statin preempts USPSTF Grade C ---
// Overlap: adults 40–75, LDL 70–189, ASCVD 10yr 7.5–<10%, CVD risk factor, no diabetes
MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA primary prevention statin rec (COR I, LOE A) with LDL/risk stratification is more specific than USPSTF Grade C shared-decision screen. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';

// --- P5: ACC/AHA severe hypercholesterolemia statin preempts USPSTF Grade B ---
// Overlap: adults 40–75, LDL ≥ 190, ASCVD 10yr ≥ 10%, CVD risk factor
MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA severe hypercholesterolemia rec (COR I, LOE B-NR) mandates high-intensity statin for LDL ≥ 190. More specific than USPSTF Grade B population screen. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';

// --- P6: ACC/AHA severe hypercholesterolemia statin preempts USPSTF Grade C ---
// Overlap: adults 40–75, LDL ≥ 190, ASCVD 10yr 7.5–<10%, CVD risk factor
MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA severe hypercholesterolemia rec (COR I, LOE B-NR) mandates high-intensity statin for LDL ≥ 190. More specific than USPSTF Grade C shared-decision screen. Per ADR 0018.',
  r.reviewer = 'Colton Ortolf',
  r.review_date = '2026-04-21',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-21';
