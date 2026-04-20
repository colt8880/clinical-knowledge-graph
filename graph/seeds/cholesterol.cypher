// ACC/AHA 2018 Cholesterol guideline — four statin benefit groups.
//
// Loads the ACC/AHA 2018 "Guideline on the Management of Blood Cholesterol"
// as a standalone subgraph. Models the four statin benefit groups from
// the 2018 update per docs/reference/guidelines/cholesterol.md.
//
// Structure:
//
//   Guideline:ACC_AHA ── FROM_GUIDELINE ── Recommendation:ACC_AHA{R1-R4}
//                                          │
//                                          │ OFFERS_STRATEGY
//                                          ▼
//                                          Strategy:ACC_AHA{high-intensity, moderate-intensity}
//                                          │
//                                          │ INCLUDES_ACTION {intensity}
//                                          ▼
//                                          Medication × 2 or 7
//                                          (shared entities from clinical-entities.cypher)
//
// This seed contains only guideline-scoped nodes (Guideline, Recommendation,
// Strategy) with the :ACC_AHA domain label. Clinical entity nodes (Medication,
// Condition, Observation) are defined in clinical-entities.cypher and
// referenced here via MATCH. Per ADR 0017, shared entities are global
// reference data with no domain label.
//
// No cross-guideline edges in this feature (F23). PREEMPTED_BY edges to
// USPSTF land in F25.
//
// Invariants:
// - Fully idempotent. Every node and edge is MERGEd; properties are set
//   via ON CREATE so second and later runs are no-ops.
// - Every node and edge carries provenance_* properties.
// - High-intensity strategy: atorvastatin + rosuvastatin (the two agents
//   with high-intensity formulations at class level).
// - Moderate-intensity strategy: all 7 statins (same set as USPSTF v0).
// - intensity property on INCLUDES_ACTION edges per F23 design notes.
//
// Apply order: constraints.cypher → clinical-entities.cypher → statins.cypher → this file.
//
// Source: Grundy SM, Stone NJ, Bailey AL, et al. 2018 AHA/ACC/AACVPR/AAPA/
//         ABC/ACPM/ADA/AGS/APhA/ASPC/NLA/PCNA Guideline on the Management
//         of Blood Cholesterol. Circulation. 2019;139(25):e1082-e1143.
//         https://doi.org/10.1161/CIR.0000000000000625

// ---------------------------------------------------------------------------
// Guideline
// ---------------------------------------------------------------------------

MERGE (g:Guideline:ACC_AHA {id: 'guideline:acc-aha-cholesterol-2018'})
ON CREATE SET
  g.title = '2018 AHA/ACC Guideline on the Management of Blood Cholesterol',
  g.publisher = 'American Heart Association / American College of Cardiology',
  g.version = '2018-11-10',
  g.effective_date = date('2018-11-10'),
  g.url = 'https://doi.org/10.1161/CIR.0000000000000625',
  g.status = 'active',
  g.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  g.provenance_version = '2018-11-10',
  g.provenance_source_section = 'Guideline root',
  g.provenance_publication_date = date('2018-11-10')
SET
  g.coverage = '{"modeled":[{"label":"Secondary prevention (COR I, LOE A)","rec_id":"rec:accaha-statin-secondary-prevention"},{"label":"Severe hypercholesterolemia (COR I, LOE B-NR)","rec_id":"rec:accaha-statin-severe-hypercholesterolemia"},{"label":"Diabetes mellitus (COR I, LOE A)","rec_id":"rec:accaha-statin-diabetes"},{"label":"Primary prevention (COR I, LOE A)","rec_id":"rec:accaha-statin-primary-prevention"}],"deferred":["adults over 75","ezetimibe add-on","PCSK9 inhibitor intensification","non-statin lipid therapies"],"exit_only":[]}';

// ---------------------------------------------------------------------------
// Recommendations — four statin benefit groups
// ---------------------------------------------------------------------------

// R1 — Secondary prevention: clinical ASCVD, age ≤75
// COR I, LOE A: high-intensity statin to reduce LDL-C ≥50%.
MERGE (r1:Recommendation:ACC_AHA {id: 'rec:accaha-statin-secondary-prevention'})
ON CREATE SET
  r1.title = 'High-intensity statin for secondary prevention in clinical ASCVD (age ≤75)',
  r1.evidence_grade = 'COR I, LOE A',
  r1.intent = 'treatment',
  r1.trigger = 'patient_state',
  r1.source_section = 'Section 4.1 — Secondary Prevention',
  r1.clinical_nuance = 'For patients with clinical ASCVD aged ≤75, high-intensity statin therapy should be initiated or continued with the aim of achieving a ≥50% reduction in LDL-C. If LDL-C remains ≥70 mg/dL on maximally tolerated statin, adding ezetimibe is reasonable (not modeled in v1). Adults >75 are out of scope for this feature.',
  r1.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}},{"age_between":{"min":18,"max":75}}]}',
  r1.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  r1.provenance_version = '2018-11-10',
  r1.provenance_source_section = 'Section 4.1 — Secondary Prevention',
  r1.provenance_publication_date = date('2018-11-10');

// R2 — Severe hypercholesterolemia: LDL ≥190 mg/dL, age 20-75
// COR I, LOE B-NR: maximally tolerated high-intensity statin.
MERGE (r2:Recommendation:ACC_AHA {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
ON CREATE SET
  r2.title = 'High-intensity statin for severe hypercholesterolemia (LDL ≥190, age 20-75)',
  r2.evidence_grade = 'COR I, LOE B-NR',
  r2.intent = 'treatment',
  r2.trigger = 'patient_state',
  r2.source_section = 'Section 4.2 — Severe Hypercholesterolemia',
  r2.clinical_nuance = 'Adults aged 20-75 with LDL-C ≥190 mg/dL should be treated with maximally tolerated high-intensity statin without requiring ASCVD risk calculation. This population often has genetic (familial) hypercholesterolemia. If LDL-C remains ≥100 mg/dL on maximally tolerated statin, adding ezetimibe is reasonable (not modeled in v1).',
  r2.structured_eligibility = '{"all_of":[{"age_between":{"min":20,"max":75}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":190,"unit":"mg/dL"}},{"none_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}}]}]}',
  r2.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  r2.provenance_version = '2018-11-10',
  r2.provenance_source_section = 'Section 4.2 — Severe Hypercholesterolemia',
  r2.provenance_publication_date = date('2018-11-10');

// R3 — Diabetes, age 40-75: moderate-intensity statin
// COR I, LOE A: moderate-intensity statin; high-intensity reasonable if
// 10-year ASCVD risk ≥7.5%.
MERGE (r3:Recommendation:ACC_AHA {id: 'rec:accaha-statin-diabetes'})
ON CREATE SET
  r3.title = 'Moderate-intensity statin for diabetes mellitus, age 40-75',
  r3.evidence_grade = 'COR I, LOE A',
  r3.intent = 'primary_prevention',
  r3.trigger = 'patient_state',
  r3.source_section = 'Section 4.3 — Diabetes Mellitus',
  r3.clinical_nuance = 'Adults aged 40-75 with diabetes mellitus should be started on moderate-intensity statin regardless of ASCVD risk score. For those with multiple risk factors or 10-year ASCVD risk ≥7.5%, it is reasonable to use high-intensity statin to reduce LDL-C by ≥50%. Risk enhancers (long duration of diabetes ≥10 years for T2DM, albuminuria ≥30 mcg/mg, eGFR <60, retinopathy, neuropathy, ABI <0.9) support the case for high-intensity.',
  r3.structured_eligibility = '{"all_of":[{"age_between":{"min":40,"max":75}},{"has_active_condition":{"codes":["cond:diabetes"]}},{"none_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":190,"unit":"mg/dL"}}]}]}',
  r3.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  r3.provenance_version = '2018-11-10',
  r3.provenance_source_section = 'Section 4.3 — Diabetes Mellitus',
  r3.provenance_publication_date = date('2018-11-10');

// R4 — Primary prevention, age 40-75, LDL 70-189, no diabetes
// COR I, LOE A at ≥7.5% 10-year ASCVD risk: moderate-to-high intensity.
// Borderline (5-7.5%) is COR IIb — captured in clinical_nuance.
MERGE (r4:Recommendation:ACC_AHA {id: 'rec:accaha-statin-primary-prevention'})
ON CREATE SET
  r4.title = 'Moderate-to-high-intensity statin for primary prevention (age 40-75, LDL 70-189, ASCVD risk ≥7.5%)',
  r4.evidence_grade = 'COR I, LOE A',
  r4.intent = 'primary_prevention',
  r4.trigger = 'patient_state',
  r4.source_section = 'Section 4.4 — Primary Prevention',
  r4.clinical_nuance = 'For adults aged 40-75 without diabetes and with LDL-C 70-189 mg/dL, a 10-year ASCVD risk ≥7.5% warrants moderate-to-high-intensity statin initiation. At borderline risk (5% to <7.5%, COR IIb, LOE B-R), risk enhancers (family history of premature ASCVD, metabolic syndrome, CKD, chronic inflammatory conditions, ethnicity, LDL-C ≥160, Lp(a) ≥50 mg/dL) favor statin initiation. A coronary artery calcium (CAC) score of 0 supports deferral of statin in borderline cases.',
  r4.structured_eligibility = '{"all_of":[{"age_between":{"min":40,"max":75}},{"none_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":190,"unit":"mg/dL"}},{"has_active_condition":{"codes":["cond:diabetes"]}}]},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":70,"unit":"mg/dL"}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"lte","threshold":189,"unit":"mg/dL"}},{"risk_score_compares":{"name":"ascvd_10yr","comparator":"gte","threshold":7.5}}]}',
  r4.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  r4.provenance_version = '2018-11-10',
  r4.provenance_source_section = 'Section 4.4 — Primary Prevention',
  r4.provenance_publication_date = date('2018-11-10');

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

// High-intensity statin strategy: atorvastatin + rosuvastatin at high intensity.
// ACC/AHA defines high-intensity as therapy that lowers LDL-C by ≥50%.
// At class level, only atorvastatin (40-80 mg) and rosuvastatin (20-40 mg)
// are standard high-intensity agents.
MERGE (sHigh:Strategy:ACC_AHA {id: 'strategy:accaha-statin-high-intensity'})
ON CREATE SET
  sHigh.name = 'High-intensity statin therapy',
  sHigh.evidence_note = 'High-intensity statin therapy lowers LDL-C by ≥50%. Standard agents: atorvastatin 40-80 mg/day, rosuvastatin 20-40 mg/day. v1 models at class level; dose verification deferred.',
  sHigh.source_section = 'Table 3 — High-, Moderate-, and Low-Intensity Statin Therapy',
  sHigh.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  sHigh.provenance_version = '2018-11-10',
  sHigh.provenance_source_section = 'Table 3',
  sHigh.provenance_publication_date = date('2018-11-10');

// Moderate-intensity statin strategy: all 7 class-level statins.
// ACC/AHA defines moderate-intensity as therapy that lowers LDL-C by 30-49%.
MERGE (sMod:Strategy:ACC_AHA {id: 'strategy:accaha-statin-moderate-intensity'})
ON CREATE SET
  sMod.name = 'Moderate-intensity statin therapy',
  sMod.evidence_note = 'Moderate-intensity statin therapy lowers LDL-C by 30-49%. All seven class-level statins can be used at moderate intensity. v1 models at class level; dose verification deferred.',
  sMod.source_section = 'Table 3 — High-, Moderate-, and Low-Intensity Statin Therapy',
  sMod.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  sMod.provenance_version = '2018-11-10',
  sMod.provenance_source_section = 'Table 3',
  sMod.provenance_publication_date = date('2018-11-10');

// ---------------------------------------------------------------------------
// FROM_GUIDELINE edges (Recommendation -> Guideline)
// ---------------------------------------------------------------------------

MATCH (g:Guideline {id: 'guideline:acc-aha-cholesterol-2018'}),
      (r1:Recommendation {id: 'rec:accaha-statin-secondary-prevention'})
MERGE (r1)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.1 — Secondary Prevention',
  e.provenance_publication_date = date('2018-11-10');

MATCH (g:Guideline {id: 'guideline:acc-aha-cholesterol-2018'}),
      (r2:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'})
MERGE (r2)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.2 — Severe Hypercholesterolemia',
  e.provenance_publication_date = date('2018-11-10');

MATCH (g:Guideline {id: 'guideline:acc-aha-cholesterol-2018'}),
      (r3:Recommendation {id: 'rec:accaha-statin-diabetes'})
MERGE (r3)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.3 — Diabetes Mellitus',
  e.provenance_publication_date = date('2018-11-10');

MATCH (g:Guideline {id: 'guideline:acc-aha-cholesterol-2018'}),
      (r4:Recommendation {id: 'rec:accaha-statin-primary-prevention'})
MERGE (r4)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.4 — Primary Prevention',
  e.provenance_publication_date = date('2018-11-10');

// ---------------------------------------------------------------------------
// OFFERS_STRATEGY edges
//   R1 (secondary prevention) -> high-intensity
//   R2 (severe hypercholesterolemia) -> high-intensity
//   R3 (diabetes) -> moderate-intensity (primary), high-intensity (alternative)
//   R4 (primary prevention) -> moderate-intensity (primary), high-intensity (alternative)
// ---------------------------------------------------------------------------

MATCH (r1:Recommendation {id: 'rec:accaha-statin-secondary-prevention'}),
      (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'})
MERGE (r1)-[e:OFFERS_STRATEGY]->(sHigh)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.1 — Secondary Prevention',
  e.provenance_publication_date = date('2018-11-10');

MATCH (r2:Recommendation {id: 'rec:accaha-statin-severe-hypercholesterolemia'}),
      (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'})
MERGE (r2)-[e:OFFERS_STRATEGY]->(sHigh)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.2 — Severe Hypercholesterolemia',
  e.provenance_publication_date = date('2018-11-10');

MATCH (r3:Recommendation {id: 'rec:accaha-statin-diabetes'}),
      (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'})
MERGE (r3)-[e:OFFERS_STRATEGY]->(sMod)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.3 — Diabetes Mellitus',
  e.provenance_publication_date = date('2018-11-10');

MATCH (r3:Recommendation {id: 'rec:accaha-statin-diabetes'}),
      (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'})
MERGE (r3)-[e:OFFERS_STRATEGY]->(sHigh)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.3 — Diabetes Mellitus',
  e.provenance_publication_date = date('2018-11-10');

MATCH (r4:Recommendation {id: 'rec:accaha-statin-primary-prevention'}),
      (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sMod)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.4 — Primary Prevention',
  e.provenance_publication_date = date('2018-11-10');

MATCH (r4:Recommendation {id: 'rec:accaha-statin-primary-prevention'}),
      (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sHigh)
ON CREATE SET
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Section 4.4 — Primary Prevention',
  e.provenance_publication_date = date('2018-11-10');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — high-intensity strategy -> 2 statins
// Only atorvastatin and rosuvastatin have standard high-intensity dosing.
// intensity: "high" per F23 design notes.
// ---------------------------------------------------------------------------

MATCH (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sHigh)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'high',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — High-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sHigh:Strategy {id: 'strategy:accaha-statin-high-intensity'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sHigh)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'high',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — High-Intensity',
  e.provenance_publication_date = date('2018-11-10');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — moderate-intensity strategy -> 7 statins
// All 7 class-level statins can be used at moderate intensity.
// intensity: "moderate" per F23 design notes.
// ---------------------------------------------------------------------------

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:simvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:pravastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:lovastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:fluvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');

MATCH (sMod:Strategy {id: 'strategy:accaha-statin-moderate-intensity'}),
      (m:Medication {id: 'med:pitavastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:acc-aha-cholesterol-2018',
  e.provenance_version = '2018-11-10',
  e.provenance_source_section = 'Table 3 — Moderate-Intensity',
  e.provenance_publication_date = date('2018-11-10');
