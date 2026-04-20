// KDIGO 2024 CKD guideline — four recommendation groups.
//
// Loads the KDIGO 2024 Clinical Practice Guideline for the Evaluation and
// Management of Chronic Kidney Disease as a standalone subgraph. Models
// four decision points per docs/reference/guidelines/kdigo-ckd.md.
//
// Structure:
//
//   Guideline:KDIGO ── FROM_GUIDELINE ── Recommendation:KDIGO{R1-R4}
//                                         │
//                                         │ OFFERS_STRATEGY
//                                         ▼
//                                         Strategy:KDIGO
//                                         │
//                                         │ INCLUDES_ACTION
//                                         ▼
//                                         Medication / Observation / Procedure
//                                         (shared entities from clinical-entities.cypher)
//
// This seed contains only guideline-scoped nodes (Guideline, Recommendation,
// Strategy) with the :KDIGO domain label. Clinical entity nodes are defined
// in clinical-entities.cypher and referenced here via MATCH. Per ADR 0017,
// shared entities are global reference data with no domain label.
//
// CKD staging approach: derived predicates over eGFR and ACR observations,
// NOT synthesized Condition nodes. This matches KDIGO's framing of staging
// as the output of applying eGFR/ACR cutoffs. See docs/reference/guidelines/
// kdigo-ckd.md § "CKD staging as predicate."
//
// No cross-guideline edges in this feature (F24). MODIFIES edges to
// USPSTF/ACC-AHA Recs land in F26.
//
// Invariants:
// - Fully idempotent. Every node and edge is MERGEd; properties are set
//   via ON CREATE so second and later runs are no-ops.
// - Every node and edge carries provenance_* properties.
// - eGFR < 20 contraindication encoded as eligibility predicate on SGLT2 Rec.
// - Statin-for-CKD Rec is the primary modifier anchor for F26.
//
// Apply order: constraints.cypher → clinical-entities.cypher → statins.cypher
//              → cholesterol.cypher → this file.
//
// Source: KDIGO 2024 Clinical Practice Guideline for the Evaluation and
//         Management of Chronic Kidney Disease. Kidney International.
//         2024;105(4S):S117-S314.
//         https://doi.org/10.1016/j.kint.2023.10.018

// ---------------------------------------------------------------------------
// Guideline
// ---------------------------------------------------------------------------

MERGE (g:Guideline:KDIGO {id: 'guideline:kdigo-ckd-2024'})
ON CREATE SET
  g.title = 'KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease',
  g.publisher = 'Kidney Disease: Improving Global Outcomes (KDIGO)',
  g.version = '2024-03-14',
  g.effective_date = date('2024-03-14'),
  g.url = 'https://doi.org/10.1016/j.kint.2023.10.018',
  g.status = 'active',
  g.provenance_guideline = 'guideline:kdigo-ckd-2024',
  g.provenance_version = '2024-03-14',
  g.provenance_source_section = 'Guideline root',
  g.provenance_publication_date = date('2024-03-14')
SET
  g.coverage = '{"modeled":[{"label":"CKD monitoring (1B)","rec_id":"rec:kdigo-ckd-monitoring"},{"label":"SGLT2 inhibitor for CKD (1A)","rec_id":"rec:kdigo-sglt2-for-ckd"},{"label":"Statin for CKD (1A)","rec_id":"rec:kdigo-statin-for-ckd"},{"label":"ACEi/ARB for albuminuric CKD (1B)","rec_id":"rec:kdigo-acei-arb-for-ckd"}],"deferred":["dialysis-specific recommendations","kidney transplant recipients","pediatric CKD","acute kidney injury","CKD-MBD"],"exit_only":[]}';

// ---------------------------------------------------------------------------
// Recommendations — four CKD management decision points
// ---------------------------------------------------------------------------

// R1 — CKD monitoring: eGFR and albuminuria assessment
// KDIGO Practice Point 1.1.1 / 1.2.1: All patients with CKD should have
// eGFR and albuminuria monitored at least annually; frequency increases
// with severity.
MERGE (r1:Recommendation:KDIGO {id: 'rec:kdigo-ckd-monitoring'})
ON CREATE SET
  r1.title = 'Monitor eGFR and urine ACR in patients with CKD',
  r1.evidence_grade = '1B',
  r1.intent = 'surveillance',
  r1.trigger = 'patient_state',
  r1.source_section = 'Chapter 1 — Evaluation of CKD',
  r1.clinical_nuance = 'KDIGO recommends at least annual monitoring of eGFR and urine ACR in patients with CKD. Monitoring frequency should increase with disease severity: every 6 months for G3a-A2, every 3-4 months for G3b-A3 or worse. Two eGFR measurements ≥3 months apart are formally required to confirm CKD; v1 fixtures use a single eGFR for simplicity.',
  r1.structured_eligibility = '{"all_of":[{"age_between":{"min":18,"max":120}},{"any_of":[{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"lt","threshold":60,"unit":"mL/min/1.73m2"}},{"most_recent_observation_value":{"code":"obs:urine-acr","window":"P2Y","comparator":"gte","threshold":30,"unit":"mg/g"}}]}]}',
  r1.provenance_guideline = 'guideline:kdigo-ckd-2024',
  r1.provenance_version = '2024-03-14',
  r1.provenance_source_section = 'Chapter 1 — Evaluation of CKD',
  r1.provenance_publication_date = date('2024-03-14');

// R2 — SGLT2 inhibitor for CKD
// KDIGO Recommendation 3.8.1 (1A): SGLT2i recommended for patients with
// CKD and T2DM, or CKD with significantly increased albuminuria regardless
// of diabetes status. eGFR ≥20 required for initiation.
MERGE (r2:Recommendation:KDIGO {id: 'rec:kdigo-sglt2-for-ckd'})
ON CREATE SET
  r2.title = 'SGLT2 inhibitor for CKD with T2DM or significant albuminuria',
  r2.evidence_grade = '1A',
  r2.intent = 'treatment',
  r2.trigger = 'patient_state',
  r2.source_section = 'Chapter 3, Recommendation 3.8.1',
  r2.clinical_nuance = 'SGLT2 inhibitors (empagliflozin, dapagliflozin) are recommended for patients with CKD who have type 2 diabetes and eGFR ≥20, OR who have significantly increased albuminuria (ACR ≥200 mg/g) regardless of diabetes status. Once initiated, SGLT2i may be continued below eGFR 20 unless not tolerated or renal replacement therapy starts. eGFR < 20 is a contraindication for new starts. Initial eGFR dip of 10-30% is expected and reversible; do not discontinue solely for this.',
  r2.structured_eligibility = '{"all_of":[{"age_between":{"min":18,"max":120}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"gte","threshold":20,"unit":"mL/min/1.73m2"}},{"any_of":[{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"lt","threshold":60,"unit":"mL/min/1.73m2"}}]},{"most_recent_observation_value":{"code":"obs:urine-acr","window":"P2Y","comparator":"gte","threshold":200,"unit":"mg/g"}}]}],"none_of":[{"has_medication_active":{"codes":["med:empagliflozin","med:dapagliflozin"]}}]}',
  r2.provenance_guideline = 'guideline:kdigo-ckd-2024',
  r2.provenance_version = '2024-03-14',
  r2.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  r2.provenance_publication_date = date('2024-03-14');

// R3 — Statin for CKD age ≥50 not on dialysis
// KDIGO Recommendation 3.5.1 (1A): Statin or statin/ezetimibe for adults
// with CKD aged ≥50 who are not treated with dialysis or kidney transplant.
// KDIGO specifically recommends moderate-intensity in CKD G3-G5 (not
// high-intensity). This Rec is the primary modifier anchor for F26.
MERGE (r3:Recommendation:KDIGO {id: 'rec:kdigo-statin-for-ckd'})
ON CREATE SET
  r3.title = 'Moderate-intensity statin for CKD patients aged ≥50, not on dialysis',
  r3.evidence_grade = '1A',
  r3.intent = 'primary_prevention',
  r3.trigger = 'patient_state',
  r3.source_section = 'Chapter 3, Recommendation 3.5.1',
  r3.clinical_nuance = 'KDIGO recommends statin therapy (moderate-intensity) for adults aged ≥50 with CKD G3a-G5 not on dialysis, regardless of LDL-C levels. In CKD G3-G5, KDIGO specifically recommends moderate-intensity over high-intensity statin due to altered pharmacokinetics and increased myopathy risk. This is the key modifier for F26: when USPSTF or ACC/AHA would recommend high-intensity, the KDIGO CKD rec modifies to moderate-intensity. eGFR ≥15 used as proxy for "not on dialysis" in v1.',
  r3.structured_eligibility = '{"all_of":[{"age_greater_than_or_equal":{"value":50}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"lt","threshold":60,"unit":"mL/min/1.73m2"}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"gte","threshold":15,"unit":"mL/min/1.73m2"}}],"none_of":[{"has_medication_active":{"codes":["med:atorvastatin","med:rosuvastatin","med:simvastatin","med:pravastatin","med:lovastatin","med:fluvastatin","med:pitavastatin"]}}]}',
  r3.provenance_guideline = 'guideline:kdigo-ckd-2024',
  r3.provenance_version = '2024-03-14',
  r3.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  r3.provenance_publication_date = date('2024-03-14');

// R4 — ACEi/ARB for albuminuric CKD
// KDIGO Recommendation 3.2.1 (1B): RAS blockade (ACEi or ARB) recommended
// for patients with CKD and moderately to severely increased albuminuria
// (A2-A3), particularly with diabetes or hypertension.
MERGE (r4:Recommendation:KDIGO {id: 'rec:kdigo-acei-arb-for-ckd'})
ON CREATE SET
  r4.title = 'ACE inhibitor or ARB for CKD with albuminuria (ACR ≥30)',
  r4.evidence_grade = '1B',
  r4.intent = 'treatment',
  r4.trigger = 'patient_state',
  r4.source_section = 'Chapter 3, Recommendation 3.2.1',
  r4.clinical_nuance = 'KDIGO recommends RAS blockade (ACEi or ARB, not both) for adults with CKD and moderately to severely increased albuminuria (ACR ≥30 mg/g, categories A2-A3). The recommendation is strongest for A3 (ACR ≥300) and for patients with diabetes or hypertension. Titrate to maximally tolerated dose. Monitor serum potassium and creatinine within 2-4 weeks of initiation. An acute GFR decline of up to 30% is acceptable; discontinue if >30% decline.',
  r4.structured_eligibility = '{"all_of":[{"age_between":{"min":18,"max":120}},{"most_recent_observation_value":{"code":"obs:urine-acr","window":"P2Y","comparator":"gte","threshold":30,"unit":"mg/g"}}],"none_of":[{"has_medication_active":{"codes":["med:lisinopril","med:enalapril","med:ramipril","med:losartan","med:valsartan","med:irbesartan"]}}]}',
  r4.provenance_guideline = 'guideline:kdigo-ckd-2024',
  r4.provenance_version = '2024-03-14',
  r4.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  r4.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

// CKD monitoring strategy: periodic eGFR + ACR
MERGE (sMon:Strategy:KDIGO {id: 'strategy:kdigo-ckd-monitoring'})
ON CREATE SET
  sMon.name = 'CKD monitoring (eGFR + urine ACR)',
  sMon.evidence_note = 'Monitoring frequency varies by CKD stage: annually for G1-G2 with A1, every 6 months for G3a-A2, every 3-4 months for G4-G5 or A3. v1 uses a 1-year cadence as the default check.',
  sMon.source_section = 'Chapter 1, Practice Point 1.1.1 / 1.2.1',
  sMon.provenance_guideline = 'guideline:kdigo-ckd-2024',
  sMon.provenance_version = '2024-03-14',
  sMon.provenance_source_section = 'Chapter 1',
  sMon.provenance_publication_date = date('2024-03-14');

// SGLT2 inhibitor strategy: empagliflozin or dapagliflozin
MERGE (sSglt2:Strategy:KDIGO {id: 'strategy:kdigo-sglt2-inhibitor'})
ON CREATE SET
  sSglt2.name = 'SGLT2 inhibitor therapy (empagliflozin or dapagliflozin)',
  sSglt2.evidence_note = 'CREDENCE, DAPA-CKD, and EMPA-KIDNEY trials demonstrated kidney and cardiovascular benefits. Empagliflozin and dapagliflozin have the strongest CKD-specific evidence. Canagliflozin also has evidence but is not modeled in v1.',
  sSglt2.source_section = 'Chapter 3, Recommendation 3.8.1',
  sSglt2.provenance_guideline = 'guideline:kdigo-ckd-2024',
  sSglt2.provenance_version = '2024-03-14',
  sSglt2.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  sSglt2.provenance_publication_date = date('2024-03-14');

// Moderate-intensity statin strategy (CKD-specific)
// Reuses the same shared statin medications as USPSTF/ACC-AHA but
// KDIGO specifically recommends moderate-intensity in CKD G3-G5.
MERGE (sStat:Strategy:KDIGO {id: 'strategy:kdigo-statin-moderate-ckd'})
ON CREATE SET
  sStat.name = 'Moderate-intensity statin for CKD',
  sStat.evidence_note = 'SHARP trial demonstrated benefit of simvastatin/ezetimibe in CKD. KDIGO recommends moderate-intensity due to altered statin pharmacokinetics in advanced CKD and increased myopathy risk with high-intensity dosing. v1 models at class level.',
  sStat.source_section = 'Chapter 3, Recommendation 3.5.1',
  sStat.provenance_guideline = 'guideline:kdigo-ckd-2024',
  sStat.provenance_version = '2024-03-14',
  sStat.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  sStat.provenance_publication_date = date('2024-03-14');

// ACEi/ARB strategy
MERGE (sRas:Strategy:KDIGO {id: 'strategy:kdigo-acei-arb'})
ON CREATE SET
  sRas.name = 'ACE inhibitor or ARB therapy',
  sRas.evidence_note = 'Multiple RCTs (RENAAL, IDNT, AASK) demonstrate ACEi/ARB reduce proteinuria and slow CKD progression. Use one agent (ACEi or ARB), not dual RAS blockade. Titrate to maximally tolerated dose.',
  sRas.source_section = 'Chapter 3, Recommendation 3.2.1',
  sRas.provenance_guideline = 'guideline:kdigo-ckd-2024',
  sRas.provenance_version = '2024-03-14',
  sRas.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  sRas.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// FROM_GUIDELINE edges (Recommendation -> Guideline)
// ---------------------------------------------------------------------------

MATCH (g:Guideline {id: 'guideline:kdigo-ckd-2024'}),
      (r1:Recommendation {id: 'rec:kdigo-ckd-monitoring'})
MERGE (r1)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 1 — Evaluation of CKD',
  e.provenance_publication_date = date('2024-03-14');

MATCH (g:Guideline {id: 'guideline:kdigo-ckd-2024'}),
      (r2:Recommendation {id: 'rec:kdigo-sglt2-for-ckd'})
MERGE (r2)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (g:Guideline {id: 'guideline:kdigo-ckd-2024'}),
      (r3:Recommendation {id: 'rec:kdigo-statin-for-ckd'})
MERGE (r3)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (g:Guideline {id: 'guideline:kdigo-ckd-2024'}),
      (r4:Recommendation {id: 'rec:kdigo-acei-arb-for-ckd'})
MERGE (r4)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// OFFERS_STRATEGY edges
//   R1 (monitoring) -> CKD monitoring strategy
//   R2 (SGLT2) -> SGLT2 inhibitor strategy
//   R3 (statin) -> moderate-intensity statin strategy
//   R4 (ACEi/ARB) -> ACEi/ARB strategy
// ---------------------------------------------------------------------------

MATCH (r1:Recommendation {id: 'rec:kdigo-ckd-monitoring'}),
      (sMon:Strategy {id: 'strategy:kdigo-ckd-monitoring'})
MERGE (r1)-[e:OFFERS_STRATEGY]->(sMon)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 1 — Evaluation of CKD',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r2:Recommendation {id: 'rec:kdigo-sglt2-for-ckd'}),
      (sSglt2:Strategy {id: 'strategy:kdigo-sglt2-inhibitor'})
MERGE (r2)-[e:OFFERS_STRATEGY]->(sSglt2)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r3:Recommendation {id: 'rec:kdigo-statin-for-ckd'}),
      (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'})
MERGE (r3)-[e:OFFERS_STRATEGY]->(sStat)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r4:Recommendation {id: 'rec:kdigo-acei-arb-for-ckd'}),
      (sRas:Strategy {id: 'strategy:kdigo-acei-arb'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sRas)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — monitoring strategy -> observations
// ---------------------------------------------------------------------------

MATCH (sMon:Strategy {id: 'strategy:kdigo-ckd-monitoring'}),
      (obs:Observation {id: 'obs:egfr'})
MERGE (sMon)-[e:INCLUDES_ACTION]->(obs)
ON CREATE SET
  e.cadence = 'P1Y', e.lookback = 'P1Y', e.priority = 'routine',
  e.intent = 'surveillance',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 1, Practice Point 1.1.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sMon:Strategy {id: 'strategy:kdigo-ckd-monitoring'}),
      (obs:Observation {id: 'obs:urine-acr'})
MERGE (sMon)-[e:INCLUDES_ACTION]->(obs)
ON CREATE SET
  e.cadence = 'P1Y', e.lookback = 'P1Y', e.priority = 'routine',
  e.intent = 'surveillance',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 1, Practice Point 1.2.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — SGLT2 strategy -> 2 SGLT2 inhibitors
// ---------------------------------------------------------------------------

MATCH (sSglt2:Strategy {id: 'strategy:kdigo-sglt2-inhibitor'}),
      (m:Medication {id: 'med:empagliflozin'})
MERGE (sSglt2)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sSglt2:Strategy {id: 'strategy:kdigo-sglt2-inhibitor'}),
      (m:Medication {id: 'med:dapagliflozin'})
MERGE (sSglt2)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — statin strategy -> 7 statins (moderate-intensity)
// Same shared statin entities as USPSTF/ACC-AHA.
// ---------------------------------------------------------------------------

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:simvastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:pravastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:lovastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:fluvastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sStat:Strategy {id: 'strategy:kdigo-statin-moderate-ckd'}),
      (m:Medication {id: 'med:pitavastatin'})
MERGE (sStat)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — ACEi/ARB strategy -> 3 ACEi + 3 ARB
// KDIGO recommends the class; any ACEi or ARB satisfies.
// ---------------------------------------------------------------------------

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:lisinopril'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:enalapril'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:ramipril'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:losartan'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:valsartan'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (sRas:Strategy {id: 'strategy:kdigo-acei-arb'}),
      (m:Medication {id: 'med:irbesartan'})
MERGE (sRas)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');

// ---------------------------------------------------------------------------
// FOR_CONDITION edges (Recommendation -> Condition)
// All four KDIGO Recs target CKD.
// ---------------------------------------------------------------------------

MATCH (r:Recommendation {id: 'rec:kdigo-ckd-monitoring'}),
      (c:Condition {id: 'cond:chronic-kidney-disease'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r:Recommendation {id: 'rec:kdigo-sglt2-for-ckd'}),
      (c:Condition {id: 'cond:chronic-kidney-disease'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.8.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r:Recommendation {id: 'rec:kdigo-statin-for-ckd'}),
      (c:Condition {id: 'cond:chronic-kidney-disease'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.5.1',
  e.provenance_publication_date = date('2024-03-14');

MATCH (r:Recommendation {id: 'rec:kdigo-acei-arb-for-ckd'}),
      (c:Condition {id: 'cond:chronic-kidney-disease'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:kdigo-ckd-2024',
  e.provenance_version = '2024-03-14',
  e.provenance_source_section = 'Chapter 3, Recommendation 3.2.1',
  e.provenance_publication_date = date('2024-03-14');
