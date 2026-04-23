// ADA 2024 Standards of Medical Care in Diabetes — pharmacologic glycemic
// management for type 2 diabetes.
//
// Loads five decision points from ADA Standards 2024, Chapter 9
// (Pharmacologic Approaches to Glycemic Treatment) and Chapter 10
// (Cardiovascular Disease and Risk Management, statin subsection).
//
// Structure:
//
//   Guideline:ADA ── FROM_GUIDELINE ── Recommendation:ADA{R1-R5}
//                                       │
//                                       │ OFFERS_STRATEGY
//                                       ▼
//                                       Strategy:ADA
//                                       │
//                                       │ INCLUDES_ACTION
//                                       ▼
//                                       Medication / Observation
//                                       (shared entities from clinical-entities.cypher)
//
// This seed contains only guideline-scoped nodes (Guideline, Recommendation,
// Strategy) with the :ADA domain label. Clinical entity nodes are defined
// in clinical-entities.cypher and referenced here via MATCH.
//
// No cross-guideline edges in this feature (F52). Overlap with KDIGO
// (SGLT2i), ACC/AHA (statin), and USPSTF (statin) documented in
// docs/reference/guidelines/ada-diabetes.md but not expressed as edges
// until F53.
//
// Evidence grades: ADA uses letter grades where A = clear evidence from
// well-conducted RCTs, B = supportive evidence from well-conducted cohort
// studies, C = supportive evidence from poorly controlled studies, E =
// expert consensus. Stored as "ADA-A", "ADA-B", etc.
//
// Invariants:
// - Fully idempotent. Every node and edge is MERGEd; properties are set
//   via ON CREATE so second and later runs are no-ops.
// - Every node and edge carries provenance_* properties.
// - eGFR contraindications encoded in structured_eligibility predicates.
// - SGLT2i appears in both R2 (cardiorenal) and R4 (intensification).
//
// Apply order: constraints.cypher → clinical-entities.cypher → statins.cypher
//              → cholesterol.cypher → kdigo-ckd.cypher → this file.
//
// Source: ADA Standards of Medical Care in Diabetes—2024. Diabetes Care.
//         2024;47(Suppl 1). https://doi.org/10.2337/dc24-SINT

// ---------------------------------------------------------------------------
// Guideline
// ---------------------------------------------------------------------------

MERGE (g:Guideline:ADA {id: 'guideline:ada-diabetes-2024'})
ON CREATE SET
  g.title = 'ADA Standards of Medical Care in Diabetes—2024',
  g.publisher = 'American Diabetes Association',
  g.version = '2024-01-01',
  g.effective_date = date('2024-01-01'),
  g.url = 'https://doi.org/10.2337/dc24-SINT',
  g.status = 'active',
  g.provenance_guideline = 'guideline:ada-diabetes-2024',
  g.provenance_version = '2024-01-01',
  g.provenance_source_section = 'Guideline root',
  g.provenance_publication_date = date('2024-01-01')
SET
  g.coverage = '{"modeled":[{"label":"Metformin first-line (ADA-A)","rec_id":"rec:ada-metformin-first-line"},{"label":"SGLT2i for cardiorenal benefit (ADA-A)","rec_id":"rec:ada-sglt2-cardiorenal"},{"label":"GLP-1 RA for CVD benefit (ADA-A)","rec_id":"rec:ada-glp1ra-cvd-benefit"},{"label":"Intensification for glycemic control (ADA-A)","rec_id":"rec:ada-intensification"},{"label":"Statin for diabetic patients (ADA-A)","rec_id":"rec:ada-statin-for-diabetes"}],"deferred":["type 1 diabetes","non-pharmacologic management","insulin titration algorithms","DPP-4 inhibitors","thiazolidinediones","sulfonylureas","gestational diabetes","CGM recommendations","microvascular complications beyond CKD"],"exit_only":[]}';

// ---------------------------------------------------------------------------
// Recommendations — five ADA decision points
// ---------------------------------------------------------------------------

// R1 — Metformin first-line therapy
// ADA-A: Metformin is the preferred initial pharmacologic agent for T2DM.
// Contraindicated at eGFR < 30; dose reduction at 30-45 (clinical_nuance).
MERGE (r1:Recommendation:ADA {id: 'rec:ada-metformin-first-line'})
ON CREATE SET
  r1.title = 'Metformin as first-line pharmacotherapy for type 2 diabetes',
  r1.evidence_grade = 'ADA-A',
  r1.intent = 'treatment',
  r1.trigger = 'patient_state',
  r1.source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r1.clinical_nuance = 'Metformin should be initiated at diagnosis of T2DM unless contraindicated. Reduce dose when eGFR 30-45 mL/min/1.73m2; contraindicated when eGFR < 30. Common side effects include GI intolerance (mitigated by extended-release formulation) and vitamin B12 deficiency with long-term use. Metformin does not cause hypoglycemia as monotherapy.',
  r1.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"age_between":{"min":18,"max":120}}],"none_of":[{"has_medication_active":{"codes":["med:metformin"]}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"lt","threshold":30,"unit":"mL/min/1.73m2"}}]}',
  r1.provenance_guideline = 'guideline:ada-diabetes-2024',
  r1.provenance_version = '2024-01-01',
  r1.provenance_source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r1.provenance_publication_date = date('2024-01-01');

// R2 — SGLT2 inhibitor for cardiorenal benefit
// ADA-A: Independent of A1C, for patients with established ASCVD, HF, or CKD.
// eGFR ≥ 20 required for initiation.
MERGE (r2:Recommendation:ADA {id: 'rec:ada-sglt2-cardiorenal'})
ON CREATE SET
  r2.title = 'SGLT2 inhibitor for cardiorenal benefit in T2DM',
  r2.evidence_grade = 'ADA-A',
  r2.intent = 'treatment',
  r2.trigger = 'patient_state',
  r2.source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment; Chapter 10 — Cardiovascular Disease',
  r2.clinical_nuance = 'SGLT2 inhibitors with proven cardiorenal benefit (empagliflozin, dapagliflozin, canagliflozin) should be used in T2DM patients with established ASCVD, heart failure, or CKD (eGFR 20-60 or albuminuria), independent of A1C level. This recommendation is independent of and additive to metformin. Benefits include reduction in HF hospitalization, CKD progression, and major adverse cardiovascular events. eGFR < 20 is a contraindication for initiation. Once initiated, may continue below eGFR 20.',
  r2.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"age_between":{"min":18,"max":120}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"gte","threshold":20,"unit":"mL/min/1.73m2"}},{"any_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}},{"has_active_condition":{"codes":["cond:heart-failure"]}},{"most_recent_observation_value":{"code":"obs:egfr","window":"P2Y","comparator":"lte","threshold":60,"unit":"mL/min/1.73m2"}},{"most_recent_observation_value":{"code":"obs:urine-acr","window":"P2Y","comparator":"gte","threshold":30,"unit":"mg/g"}}]}],"none_of":[{"has_medication_active":{"codes":["med:empagliflozin","med:dapagliflozin","med:canagliflozin"]}}]}',
  r2.provenance_guideline = 'guideline:ada-diabetes-2024',
  r2.provenance_version = '2024-01-01',
  r2.provenance_source_section = 'Chapter 9 / Chapter 10',
  r2.provenance_publication_date = date('2024-01-01');

// R3 — GLP-1 RA for cardiovascular benefit
// ADA-A: For patients with established ASCVD or high CVD risk, independent
// of A1C. Complements or substitutes SGLT2i.
MERGE (r3:Recommendation:ADA {id: 'rec:ada-glp1ra-cvd-benefit'})
ON CREATE SET
  r3.title = 'GLP-1 receptor agonist for cardiovascular benefit in T2DM',
  r3.evidence_grade = 'ADA-A',
  r3.intent = 'treatment',
  r3.trigger = 'patient_state',
  r3.source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r3.clinical_nuance = 'GLP-1 receptor agonists with proven cardiovascular benefit (semaglutide, liraglutide, dulaglutide) should be considered for T2DM patients with established ASCVD or indicators of high cardiovascular risk. Benefits include reduction in major adverse cardiovascular events, stroke, and cardiovascular death. Can be used in combination with SGLT2 inhibitors for additive benefit. Weight loss is an additional benefit for patients with obesity.',
  r3.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"age_between":{"min":18,"max":120}},{"any_of":[{"has_active_condition":{"codes":["cond:ascvd-established"]}},{"all_of":[{"age_between":{"min":55,"max":120}},{"any_of":[{"has_active_condition":{"codes":["cond:hypertension"]}},{"has_active_condition":{"codes":["cond:dyslipidemia"]}},{"smoking_status_is":{"values":["current_some_day","current_every_day"]}}]}]}]}],"none_of":[{"has_medication_active":{"codes":["med:semaglutide","med:liraglutide","med:dulaglutide"]}}]}',
  r3.provenance_guideline = 'guideline:ada-diabetes-2024',
  r3.provenance_version = '2024-01-01',
  r3.provenance_source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r3.provenance_publication_date = date('2024-01-01');

// R4 — Intensification for glycemic control
// ADA-A: When A1C remains ≥ 7% despite metformin, add SGLT2i, GLP-1 RA,
// or insulin based on patient factors.
MERGE (r4:Recommendation:ADA {id: 'rec:ada-intensification'})
ON CREATE SET
  r4.title = 'Intensification of glycemic therapy when A1C remains above target',
  r4.evidence_grade = 'ADA-A',
  r4.intent = 'treatment',
  r4.trigger = 'patient_state',
  r4.source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r4.clinical_nuance = 'When A1C remains ≥7% (individualize target for frail/elderly patients) despite metformin, intensify with a second agent. Choice depends on patient factors: SGLT2i if CKD/HF predominates; GLP-1 RA if ASCVD or weight management is priority; insulin (typically basal) if A1C is very high (≥10%) or symptomatic hyperglycemia. A1C target of <7% is appropriate for most nonpregnant adults; less stringent targets (< 8%) may be appropriate for patients with limited life expectancy, advanced complications, or extensive comorbidities.',
  r4.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"age_between":{"min":18,"max":120}},{"has_medication_active":{"codes":["med:metformin"]}},{"most_recent_observation_value":{"code":"obs:hba1c","window":"P1Y","comparator":"gte","threshold":7,"unit":"%"}}]}',
  r4.provenance_guideline = 'guideline:ada-diabetes-2024',
  r4.provenance_version = '2024-01-01',
  r4.provenance_source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  r4.provenance_publication_date = date('2024-01-01');

// R5 — Statin for diabetic patients
// ADA-A: Moderate-intensity statin for all diabetic adults 40-75; high-intensity
// if ASCVD risk factors present.
MERGE (r5:Recommendation:ADA {id: 'rec:ada-statin-for-diabetes'})
ON CREATE SET
  r5.title = 'Statin therapy for adults with diabetes aged 40-75',
  r5.evidence_grade = 'ADA-A',
  r5.intent = 'primary_prevention',
  r5.trigger = 'patient_state',
  r5.source_section = 'Chapter 10 — Cardiovascular Disease and Risk Management',
  r5.clinical_nuance = 'ADA recommends at least moderate-intensity statin therapy for all adults aged 40-75 with diabetes, regardless of ASCVD risk score. For those with multiple ASCVD risk factors (LDL-C ≥100, hypertension, smoking, overweight/obesity, family history of premature ASCVD), high-intensity statin therapy is recommended to achieve ≥50% LDL-C reduction. ADA defers to ACC/AHA for detailed statin dosing.',
  r5.structured_eligibility = '{"all_of":[{"has_active_condition":{"codes":["cond:diabetes"]}},{"age_between":{"min":40,"max":75}}],"none_of":[{"has_medication_active":{"codes":["med:atorvastatin","med:rosuvastatin","med:simvastatin","med:pravastatin","med:lovastatin","med:fluvastatin","med:pitavastatin"]}}]}',
  r5.provenance_guideline = 'guideline:ada-diabetes-2024',
  r5.provenance_version = '2024-01-01',
  r5.provenance_source_section = 'Chapter 10 — Cardiovascular Disease and Risk Management',
  r5.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

// Metformin strategy
MERGE (sMet:Strategy:ADA {id: 'strategy:ada-metformin'})
ON CREATE SET
  sMet.name = 'Metformin monotherapy',
  sMet.evidence_note = 'Metformin is the preferred initial pharmacologic agent for T2DM. Effective, low cost, well-studied safety profile, possible cardiovascular benefit. Start 500 mg daily, titrate to 1000 mg twice daily.',
  sMet.source_section = 'Chapter 9 — Initial Pharmacologic Treatment',
  sMet.provenance_guideline = 'guideline:ada-diabetes-2024',
  sMet.provenance_version = '2024-01-01',
  sMet.provenance_source_section = 'Chapter 9',
  sMet.provenance_publication_date = date('2024-01-01');

// SGLT2 inhibitor strategy (cardiorenal benefit)
MERGE (sSglt2:Strategy:ADA {id: 'strategy:ada-sglt2-cardiorenal'})
ON CREATE SET
  sSglt2.name = 'SGLT2 inhibitor for cardiorenal benefit',
  sSglt2.evidence_note = 'EMPA-REG OUTCOME (empagliflozin), CANVAS (canagliflozin), DECLARE-TIMI 58 (dapagliflozin), CREDENCE, DAPA-CKD, and EMPA-KIDNEY trials demonstrated cardiovascular and renal benefits independent of glycemic control.',
  sSglt2.source_section = 'Chapter 9 — SGLT2 Inhibitors',
  sSglt2.provenance_guideline = 'guideline:ada-diabetes-2024',
  sSglt2.provenance_version = '2024-01-01',
  sSglt2.provenance_source_section = 'Chapter 9 — SGLT2 Inhibitors',
  sSglt2.provenance_publication_date = date('2024-01-01');

// GLP-1 RA strategy (CVD benefit)
MERGE (sGlp1:Strategy:ADA {id: 'strategy:ada-glp1ra-cvd'})
ON CREATE SET
  sGlp1.name = 'GLP-1 receptor agonist for cardiovascular benefit',
  sGlp1.evidence_note = 'SUSTAIN-6 and PIONEER 6 (semaglutide), LEADER (liraglutide), REWIND (dulaglutide) trials demonstrated reduction in MACE. Weight loss is an additional clinical benefit.',
  sGlp1.source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  sGlp1.provenance_guideline = 'guideline:ada-diabetes-2024',
  sGlp1.provenance_version = '2024-01-01',
  sGlp1.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  sGlp1.provenance_publication_date = date('2024-01-01');

// SGLT2 inhibitor strategy (intensification — same meds, different Rec)
MERGE (sSglt2Int:Strategy:ADA {id: 'strategy:ada-sglt2-intensification'})
ON CREATE SET
  sSglt2Int.name = 'Add SGLT2 inhibitor for glycemic intensification',
  sSglt2Int.evidence_note = 'SGLT2 inhibitors reduce A1C by ~0.5-0.8% and provide weight loss and blood pressure reduction in addition to glycemic benefit. Preferred add-on when CKD or HF predominates.',
  sSglt2Int.source_section = 'Chapter 9 — Intensification',
  sSglt2Int.provenance_guideline = 'guideline:ada-diabetes-2024',
  sSglt2Int.provenance_version = '2024-01-01',
  sSglt2Int.provenance_source_section = 'Chapter 9 — Intensification',
  sSglt2Int.provenance_publication_date = date('2024-01-01');

// GLP-1 RA strategy (intensification)
MERGE (sGlp1Int:Strategy:ADA {id: 'strategy:ada-glp1ra-intensification'})
ON CREATE SET
  sGlp1Int.name = 'Add GLP-1 receptor agonist for glycemic intensification',
  sGlp1Int.evidence_note = 'GLP-1 RAs reduce A1C by ~1.0-1.8% and provide significant weight loss. Preferred add-on when ASCVD risk or weight management is priority.',
  sGlp1Int.source_section = 'Chapter 9 — Intensification',
  sGlp1Int.provenance_guideline = 'guideline:ada-diabetes-2024',
  sGlp1Int.provenance_version = '2024-01-01',
  sGlp1Int.provenance_source_section = 'Chapter 9 — Intensification',
  sGlp1Int.provenance_publication_date = date('2024-01-01');

// Insulin strategy (intensification)
MERGE (sIns:Strategy:ADA {id: 'strategy:ada-insulin-intensification'})
ON CREATE SET
  sIns.name = 'Add basal insulin for glycemic intensification',
  sIns.evidence_note = 'Basal insulin (glargine, detemir, degludec) is preferred when A1C is very high (≥10%) or symptomatic hyperglycemia is present. Typically added to metformin. Consider adding rapid-acting insulin (lispro, aspart) if postprandial control is needed.',
  sIns.source_section = 'Chapter 9 — Insulin Therapy',
  sIns.provenance_guideline = 'guideline:ada-diabetes-2024',
  sIns.provenance_version = '2024-01-01',
  sIns.provenance_source_section = 'Chapter 9 — Insulin Therapy',
  sIns.provenance_publication_date = date('2024-01-01');

// Moderate-intensity statin strategy (diabetes)
MERGE (sStatMod:Strategy:ADA {id: 'strategy:ada-statin-moderate'})
ON CREATE SET
  sStatMod.name = 'Moderate-intensity statin for diabetes',
  sStatMod.evidence_note = 'ADA recommends at least moderate-intensity statin for all diabetic adults 40-75. Seven class-level agents at moderate intensity. v1 models at class level; dose verification deferred.',
  sStatMod.source_section = 'Chapter 10 — Lipid Management',
  sStatMod.provenance_guideline = 'guideline:ada-diabetes-2024',
  sStatMod.provenance_version = '2024-01-01',
  sStatMod.provenance_source_section = 'Chapter 10 — Lipid Management',
  sStatMod.provenance_publication_date = date('2024-01-01');

// High-intensity statin strategy (diabetes with risk factors)
MERGE (sStatHigh:Strategy:ADA {id: 'strategy:ada-statin-high'})
ON CREATE SET
  sStatHigh.name = 'High-intensity statin for diabetes with ASCVD risk factors',
  sStatHigh.evidence_note = 'For diabetic patients with multiple ASCVD risk factors, high-intensity statin to achieve ≥50% LDL-C reduction is recommended. Standard high-intensity agents: atorvastatin 40-80 mg, rosuvastatin 20-40 mg.',
  sStatHigh.source_section = 'Chapter 10 — Lipid Management',
  sStatHigh.provenance_guideline = 'guideline:ada-diabetes-2024',
  sStatHigh.provenance_version = '2024-01-01',
  sStatHigh.provenance_source_section = 'Chapter 10 — Lipid Management',
  sStatHigh.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// FROM_GUIDELINE edges (Recommendation -> Guideline)
// ---------------------------------------------------------------------------

MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}),
      (r1:Recommendation {id: 'rec:ada-metformin-first-line'})
MERGE (r1)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Pharmacologic Approaches to Glycemic Treatment',
  e.provenance_publication_date = date('2024-01-01');

MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}),
      (r2:Recommendation {id: 'rec:ada-sglt2-cardiorenal'})
MERGE (r2)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 / Chapter 10',
  e.provenance_publication_date = date('2024-01-01');

MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}),
      (r3:Recommendation {id: 'rec:ada-glp1ra-cvd-benefit'})
MERGE (r3)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  e.provenance_publication_date = date('2024-01-01');

MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}),
      (r4:Recommendation {id: 'rec:ada-intensification'})
MERGE (r4)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}),
      (r5:Recommendation {id: 'rec:ada-statin-for-diabetes'})
MERGE (r5)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Cardiovascular Disease and Risk Management',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// FOR_CONDITION edges (Recommendation -> Condition)
// All five ADA Recs target diabetes.
// ---------------------------------------------------------------------------

MATCH (r:Recommendation {id: 'rec:ada-metformin-first-line'}),
      (c:Condition {id: 'cond:diabetes'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r:Recommendation {id: 'rec:ada-sglt2-cardiorenal'}),
      (c:Condition {id: 'cond:diabetes'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 / Chapter 10',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r:Recommendation {id: 'rec:ada-glp1ra-cvd-benefit'}),
      (c:Condition {id: 'cond:diabetes'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r:Recommendation {id: 'rec:ada-intensification'}),
      (c:Condition {id: 'cond:diabetes'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r:Recommendation {id: 'rec:ada-statin-for-diabetes'}),
      (c:Condition {id: 'cond:diabetes'})
MERGE (r)-[e:FOR_CONDITION]->(c)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// OFFERS_STRATEGY edges
//   R1 (metformin) -> metformin strategy
//   R2 (SGLT2i cardiorenal) -> SGLT2i cardiorenal strategy
//   R3 (GLP-1 RA CVD) -> GLP-1 RA CVD strategy
//   R4 (intensification) -> SGLT2i intens., GLP-1 RA intens., insulin intens.
//   R5 (statin) -> moderate-intensity (primary), high-intensity (alternative)
// ---------------------------------------------------------------------------

MATCH (r1:Recommendation {id: 'rec:ada-metformin-first-line'}),
      (sMet:Strategy {id: 'strategy:ada-metformin'})
MERGE (r1)-[e:OFFERS_STRATEGY]->(sMet)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Initial Pharmacologic Treatment',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r2:Recommendation {id: 'rec:ada-sglt2-cardiorenal'}),
      (sSglt2:Strategy {id: 'strategy:ada-sglt2-cardiorenal'})
MERGE (r2)-[e:OFFERS_STRATEGY]->(sSglt2)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 / Chapter 10',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r3:Recommendation {id: 'rec:ada-glp1ra-cvd-benefit'}),
      (sGlp1:Strategy {id: 'strategy:ada-glp1ra-cvd'})
MERGE (r3)-[e:OFFERS_STRATEGY]->(sGlp1)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r4:Recommendation {id: 'rec:ada-intensification'}),
      (sSglt2Int:Strategy {id: 'strategy:ada-sglt2-intensification'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sSglt2Int)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r4:Recommendation {id: 'rec:ada-intensification'}),
      (sGlp1Int:Strategy {id: 'strategy:ada-glp1ra-intensification'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sGlp1Int)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r4:Recommendation {id: 'rec:ada-intensification'}),
      (sIns:Strategy {id: 'strategy:ada-insulin-intensification'})
MERGE (r4)-[e:OFFERS_STRATEGY]->(sIns)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Insulin Therapy',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r5:Recommendation {id: 'rec:ada-statin-for-diabetes'}),
      (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'})
MERGE (r5)-[e:OFFERS_STRATEGY]->(sStatMod)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (r5:Recommendation {id: 'rec:ada-statin-for-diabetes'}),
      (sStatHigh:Strategy {id: 'strategy:ada-statin-high'})
MERGE (r5)-[e:OFFERS_STRATEGY]->(sStatHigh)
ON CREATE SET
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — metformin strategy -> 1 medication
// ---------------------------------------------------------------------------

MATCH (sMet:Strategy {id: 'strategy:ada-metformin'}),
      (m:Medication {id: 'med:metformin'})
MERGE (sMet)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Initial Pharmacologic Treatment',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — SGLT2i cardiorenal strategy -> 3 SGLT2 inhibitors
// ---------------------------------------------------------------------------

MATCH (sSglt2:Strategy {id: 'strategy:ada-sglt2-cardiorenal'}),
      (m:Medication {id: 'med:empagliflozin'})
MERGE (sSglt2)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — SGLT2 Inhibitors',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sSglt2:Strategy {id: 'strategy:ada-sglt2-cardiorenal'}),
      (m:Medication {id: 'med:dapagliflozin'})
MERGE (sSglt2)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — SGLT2 Inhibitors',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sSglt2:Strategy {id: 'strategy:ada-sglt2-cardiorenal'}),
      (m:Medication {id: 'med:canagliflozin'})
MERGE (sSglt2)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — SGLT2 Inhibitors',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — GLP-1 RA CVD strategy -> 3 GLP-1 RAs
// ---------------------------------------------------------------------------

MATCH (sGlp1:Strategy {id: 'strategy:ada-glp1ra-cvd'}),
      (m:Medication {id: 'med:semaglutide'})
MERGE (sGlp1)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sGlp1:Strategy {id: 'strategy:ada-glp1ra-cvd'}),
      (m:Medication {id: 'med:liraglutide'})
MERGE (sGlp1)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sGlp1:Strategy {id: 'strategy:ada-glp1ra-cvd'}),
      (m:Medication {id: 'med:dulaglutide'})
MERGE (sGlp1)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — GLP-1 Receptor Agonists',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — SGLT2i intensification strategy -> 3 SGLT2 inhibitors
// ---------------------------------------------------------------------------

MATCH (sSglt2Int:Strategy {id: 'strategy:ada-sglt2-intensification'}),
      (m:Medication {id: 'med:empagliflozin'})
MERGE (sSglt2Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sSglt2Int:Strategy {id: 'strategy:ada-sglt2-intensification'}),
      (m:Medication {id: 'med:dapagliflozin'})
MERGE (sSglt2Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sSglt2Int:Strategy {id: 'strategy:ada-sglt2-intensification'}),
      (m:Medication {id: 'med:canagliflozin'})
MERGE (sSglt2Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — GLP-1 RA intensification strategy -> 3 GLP-1 RAs
// ---------------------------------------------------------------------------

MATCH (sGlp1Int:Strategy {id: 'strategy:ada-glp1ra-intensification'}),
      (m:Medication {id: 'med:semaglutide'})
MERGE (sGlp1Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sGlp1Int:Strategy {id: 'strategy:ada-glp1ra-intensification'}),
      (m:Medication {id: 'med:liraglutide'})
MERGE (sGlp1Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sGlp1Int:Strategy {id: 'strategy:ada-glp1ra-intensification'}),
      (m:Medication {id: 'med:dulaglutide'})
MERGE (sGlp1Int)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Intensification',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — insulin intensification strategy -> 2 insulins
// ---------------------------------------------------------------------------

MATCH (sIns:Strategy {id: 'strategy:ada-insulin-intensification'}),
      (m:Medication {id: 'med:insulin-glargine'})
MERGE (sIns)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Insulin Therapy',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sIns:Strategy {id: 'strategy:ada-insulin-intensification'}),
      (m:Medication {id: 'med:insulin-lispro'})
MERGE (sIns)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'treatment',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 9 — Insulin Therapy',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — moderate-intensity statin strategy -> 7 statins
// ---------------------------------------------------------------------------

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:simvastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:pravastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:lovastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:fluvastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatMod:Strategy {id: 'strategy:ada-statin-moderate'}),
      (m:Medication {id: 'med:pitavastatin'})
MERGE (sStatMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'moderate',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — high-intensity statin strategy -> 2 statins
// ---------------------------------------------------------------------------

MATCH (sStatHigh:Strategy {id: 'strategy:ada-statin-high'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sStatHigh)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'high',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');

MATCH (sStatHigh:Strategy {id: 'strategy:ada-statin-high'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sStatHigh)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine',
  e.intent = 'primary_prevention', e.intensity = 'high',
  e.provenance_guideline = 'guideline:ada-diabetes-2024',
  e.provenance_version = '2024-01-01',
  e.provenance_source_section = 'Chapter 10 — Lipid Management',
  e.provenance_publication_date = date('2024-01-01');
