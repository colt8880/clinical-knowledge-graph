// Cross-guideline PREEMPTED_BY edges: USPSTF 2022 Statins ↔ ACC/AHA 2018 Cholesterol.
//
// Per ADR 0018 (preemption precedence): ACC/AHA (priority 200) preempts USPSTF
// (priority 100) within the cardiovascular statin domain. Direction is FROM the
// preempted Rec TO the winning Rec: (loser)-[:PREEMPTED_BY]->(winner).
//
// Preemption only activates when both the preempted and winning Recs match the
// patient. An unmatched winner does not preempt.
//
// Nine edges covering four clinical scenarios:
//
//   1. Secondary prevention (clinical ASCVD): USPSTF exits before matching, so
//      these edges are safety nets. ACC/AHA R1 prescribes high-intensity statin
//      for secondary prevention; USPSTF is primary prevention only.
//
//   2. Severe hypercholesterolemia (LDL ≥190): USPSTF exits (out_of_scope_
//      familial_hypercholesterolemia). ACC/AHA R2 prescribes high-intensity
//      statin. Safety-net edges.
//
//   3. Diabetes age 40-75: both USPSTF Grade B/C and ACC/AHA R3 can match.
//      ACC/AHA provides more specific guidance (moderate-intensity regardless
//      of ASCVD risk, with high-intensity option if risk ≥7.5%).
//
//   4. Primary prevention no diabetes age 40-75: both USPSTF Grade B/C and
//      ACC/AHA R4 can match when ASCVD risk ≥7.5%. ACC/AHA provides intensity
//      tiers and risk-enhancer guidance that USPSTF does not.
//
// Apply order: constraints.cypher → clinical-entities.cypher → statins.cypher
//              → cholesterol.cypher → this file.
//
// See docs/reference/guidelines/preemption-map.md for the full human-readable table.

// ---------------------------------------------------------------------------
// Scenario 1: Secondary prevention (safety net)
// USPSTF Grade B → ACC/AHA secondary prevention
// ---------------------------------------------------------------------------

MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA secondary prevention (COR I, LOE A) prescribes high-intensity statin for clinical ASCVD. USPSTF primary prevention Grade B is not applicable to secondary prevention patients. Safety-net edge: USPSTF exits before matching.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// USPSTF Grade C → ACC/AHA secondary prevention

MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA secondary prevention preempts USPSTF Grade C for patients with clinical ASCVD. Safety-net edge: USPSTF exits before matching.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// USPSTF Grade I → ACC/AHA secondary prevention

MATCH (loser:Recommendation {id: 'rec:statin-insufficient-evidence-grade-i'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA secondary prevention preempts USPSTF Grade I for patients ≥76 with clinical ASCVD. Safety-net edge: USPSTF exits before matching for patients with ASCVD.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 2: Severe hypercholesterolemia (safety net)
// USPSTF Grade B → ACC/AHA severe hypercholesterolemia
// ---------------------------------------------------------------------------

MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA recommends high-intensity statin for LDL ≥190 mg/dL (COR I, LOE B-NR) regardless of ASCVD risk. USPSTF primary prevention reasoning is non-applicable at this LDL level. Safety-net edge: USPSTF exits (out_of_scope_familial_hypercholesterolemia) before matching.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// USPSTF Grade C → ACC/AHA severe hypercholesterolemia

MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA severe hypercholesterolemia preempts USPSTF Grade C for LDL ≥190. Safety-net edge: USPSTF exits before matching.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 3: Diabetes age 40-75 (real overlap)
// Both USPSTF Grade B/C and ACC/AHA R3 can match simultaneously.
// ---------------------------------------------------------------------------

MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA recommends moderate-intensity statin for all adults 40-75 with diabetes (COR I, LOE A), regardless of ASCVD risk score. Provides more specific guidance than USPSTF Grade B, which requires ASCVD risk ≥10%. ACC/AHA also offers high-intensity statin for diabetic patients with risk ≥7.5%, a distinction USPSTF does not make.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA diabetes statin recommendation (COR I, LOE A) preempts USPSTF Grade C for diabetic patients with ASCVD risk 7.5-<10%. ACC/AHA covers all diabetic adults 40-75 with moderate-intensity statin, removing the need for shared decision-making that Grade C requires.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

// ---------------------------------------------------------------------------
// Scenario 4: Primary prevention, no diabetes, age 40-75 (real overlap)
// Both USPSTF Grade B/C and ACC/AHA R4 can match when ASCVD risk ≥7.5%.
// ---------------------------------------------------------------------------

MATCH (loser:Recommendation {id: 'rec:statin-initiate-grade-b'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA primary prevention (COR I, LOE A) provides intensity tiers and risk-enhancer guidance that USPSTF Grade B does not. Both apply to patients 40-75 with ASCVD risk ≥10%, but ACC/AHA also covers 7.5-<10% and gives quantitative LDL thresholds.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';

MATCH (loser:Recommendation {id: 'rec:statin-selective-grade-c'})
MATCH (winner:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (loser)-[r:PREEMPTED_BY]->(winner)
ON CREATE SET
  r.priority = 200,
  r.rationale = 'ACC/AHA primary prevention preempts USPSTF Grade C for non-diabetic patients with ASCVD risk ≥7.5% and LDL 70-189. ACC/AHA provides a definitive recommendation (COR I) where USPSTF Grade C requires shared decision-making.',
  r.provenance_source = 'cross-edges-uspstf-accaha',
  r.provenance_date = '2026-04-17';
