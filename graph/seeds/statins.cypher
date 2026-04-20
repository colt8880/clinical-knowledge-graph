// v0 statin knowledge-graph seed — guideline-scoped nodes only.
//
// Loads the USPSTF 2022 statin primary prevention model exactly as specified in
// docs/reference/guidelines/statins.md. Structure:
//
//   Guideline:USPSTF  ── FROM_GUIDELINE ──  Recommendation:USPSTF{R1,R2,R3}
//                                           │
//                                           │ OFFERS_STRATEGY
//                                           ▼
//                                           Strategy:USPSTF{moderate-intensity, SDM}
//                                           │
//                                           │ INCLUDES_ACTION
//                                           ▼
//                                           Medication × 7 / Procedure × 1
//                                           (shared entities from clinical-entities.cypher)
//
// This seed contains only guideline-scoped nodes (Guideline, Recommendation,
// Strategy) with the :USPSTF domain label. Clinical entity nodes (Medication,
// Condition, Observation, Procedure) are defined in clinical-entities.cypher
// and referenced here via MATCH. Per ADR 0017, shared entities are global
// reference data with no domain label.
//
// Invariants:
// - Fully idempotent. Every node and edge is MERGEd; properties are set via
//   ON CREATE so second and later runs are no-ops.
// - Every node and edge carries provenance_* properties tying it back to the
//   source guideline, version, section, and publication date.
// - Class-level statin strategy: seven Medication members; any one active
//   prescription satisfies the strategy (v0 does not model intensity by dose;
//   see guidelines/statins.md § Strategies).
// - structured_eligibility is stored as a JSON string. The predicate tree is
//   authoritative; edges (EXCLUDED_BY / TRIGGERED_BY) are materialized views
//   and deliberately not emitted in v0 (no predicate evaluator yet).
//
// Implementation note: cypher-shell runs each `;`-terminated statement as its
// own transaction. We cannot share variable bindings across statements, so
// every edge-creation statement begins with MATCH clauses that reload the
// endpoints by id. The uniqueness constraints from constraints.cypher keep
// MATCH resolution unambiguous.
//
// Apply order: constraints.cypher → clinical-entities.cypher → this file.
//
// Source: USPSTF. Statin Use for the Primary Prevention of CVD in Adults.
//         Final recommendation, 2022-08-23.
//         https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication

// ---------------------------------------------------------------------------
// Guideline
// ---------------------------------------------------------------------------

MERGE (g:Guideline:USPSTF {id: 'guideline:uspstf-statin-2022'})
ON CREATE SET
  g.title = 'Statin Use for the Primary Prevention of Cardiovascular Disease in Adults: Preventive Medication',
  g.publisher = 'US Preventive Services Task Force',
  g.version = '2022-08-23',
  g.effective_date = date('2022-08-23'),
  g.url = 'https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication',
  g.status = 'active',
  g.provenance_guideline = 'guideline:uspstf-statin-2022',
  g.provenance_version = '2022-08-23',
  g.provenance_source_section = 'Guideline root',
  g.provenance_publication_date = date('2022-08-23')
SET
  g.coverage = '{"modeled":[{"label":"Grade B","rec_id":"rec:statin-initiate-grade-b"},{"label":"Grade C","rec_id":"rec:statin-selective-grade-c"},{"label":"Grade I","rec_id":"rec:statin-insufficient-evidence-grade-i"}],"deferred":["pregnancy","secondary prevention"],"exit_only":["age < 40","age > 75"]}';

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

// R1 — Grade B: initiate statin
MERGE (r1:Recommendation:USPSTF {id: 'rec:statin-initiate-grade-b'})
ON CREATE SET
  r1.title = 'Initiate statin for primary prevention of CVD (Grade B)',
  r1.evidence_grade = 'B',
  r1.intent = 'primary_prevention',
  r1.trigger = 'patient_state',
  r1.source_section = 'Recommendation Summary, Grade B',
  r1.clinical_nuance = 'Shared decision making about the potential benefits, harms, patient preferences, and costs of statin therapy is recommended. Risk may be under- or over-estimated by the Pooled Cohort Equations in populations they were not derived from.',
  r1.structured_eligibility = '{"all_of":[{"age_between":{"min":40,"max":75}},{"none_of":[{"has_condition_history":{"codes":["cond:ascvd-established"]}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":190,"unit":"mg/dL"}},{"has_condition_history":{"codes":["cond:familial-hypercholesterolemia"]}}]},{"any_of":[{"has_active_condition":{"codes":["cond:dyslipidemia"]}},{"has_active_condition":{"codes":["cond:diabetes"]}},{"has_active_condition":{"codes":["cond:hypertension"]}},{"smoking_status_is":{"values":["current","current_some_day","current_every_day"]}}]},{"risk_score_compares":{"name":"ascvd_10yr","comparator":"gte","threshold":10}}]}',
  r1.provenance_guideline = 'guideline:uspstf-statin-2022',
  r1.provenance_version = '2022-08-23',
  r1.provenance_source_section = 'Recommendation Summary, Grade B',
  r1.provenance_publication_date = date('2022-08-23');

// R2 — Grade C: selectively offer statin / SDM
// Eligibility matches R1 except the risk-score gate is 7.5 ≤ ascvd_10yr < 10.
// Expressed via two risk_score_compares (gte 7.5, lt 10) per predicate catalog.
MERGE (r2:Recommendation:USPSTF {id: 'rec:statin-selective-grade-c'})
ON CREATE SET
  r2.title = 'Selectively offer statin based on shared decision-making (Grade C)',
  r2.evidence_grade = 'C',
  r2.intent = 'shared_decision',
  r2.trigger = 'patient_state',
  r2.source_section = 'Recommendation Summary, Grade C',
  r2.clinical_nuance = 'Smaller net benefit in this group. The decision to initiate should be based on individual circumstances including patient preference, values, comorbid conditions, life expectancy, and risk factor profile.',
  r2.structured_eligibility = '{"all_of":[{"age_between":{"min":40,"max":75}},{"none_of":[{"has_condition_history":{"codes":["cond:ascvd-established"]}},{"most_recent_observation_value":{"code":"obs:ldl-cholesterol","window":"P2Y","comparator":"gte","threshold":190,"unit":"mg/dL"}},{"has_condition_history":{"codes":["cond:familial-hypercholesterolemia"]}}]},{"any_of":[{"has_active_condition":{"codes":["cond:dyslipidemia"]}},{"has_active_condition":{"codes":["cond:diabetes"]}},{"has_active_condition":{"codes":["cond:hypertension"]}},{"smoking_status_is":{"values":["current","current_some_day","current_every_day"]}}]},{"risk_score_compares":{"name":"ascvd_10yr","comparator":"gte","threshold":7.5}},{"risk_score_compares":{"name":"ascvd_10yr","comparator":"lt","threshold":10}}]}',
  r2.provenance_guideline = 'guideline:uspstf-statin-2022',
  r2.provenance_version = '2022-08-23',
  r2.provenance_source_section = 'Recommendation Summary, Grade C',
  r2.provenance_publication_date = date('2022-08-23');

// R3 — Grade I: insufficient evidence at age ≥76
MERGE (r3:Recommendation:USPSTF {id: 'rec:statin-insufficient-evidence-grade-i'})
ON CREATE SET
  r3.title = 'Insufficient evidence to recommend for or against initiating statins (Grade I, >=76)',
  r3.evidence_grade = 'I',
  r3.intent = 'primary_prevention',
  r3.trigger = 'patient_state',
  r3.source_section = 'Recommendation Summary, Grade I',
  r3.clinical_nuance = 'Current evidence is insufficient to assess the balance of benefits and harms of initiating a statin for the primary prevention of CVD events and mortality in adults >=76.',
  r3.structured_eligibility = '{"all_of":[{"age_greater_than_or_equal":{"value":76}},{"none_of":[{"has_condition_history":{"codes":["cond:ascvd-established"]}}]}]}',
  r3.provenance_guideline = 'guideline:uspstf-statin-2022',
  r3.provenance_version = '2022-08-23',
  r3.provenance_source_section = 'Recommendation Summary, Grade I',
  r3.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

MERGE (sMod:Strategy:USPSTF {id: 'strategy:statin-moderate-intensity'})
ON CREATE SET
  sMod.name = 'Moderate-intensity statin therapy',
  sMod.evidence_note = 'Any active moderate-intensity statin satisfies. v0 does not model intensity by dose; agent-level substitution is acceptable. See guidelines/statins.md.',
  sMod.source_section = 'Recommendation Summary, Grade B',
  sMod.provenance_guideline = 'guideline:uspstf-statin-2022',
  sMod.provenance_version = '2022-08-23',
  sMod.provenance_source_section = 'Recommendation Summary, Grade B',
  sMod.provenance_publication_date = date('2022-08-23');

MERGE (sSdm:Strategy:USPSTF {id: 'strategy:statin-shared-decision-discussion'})
ON CREATE SET
  sSdm.name = 'Shared decision-making discussion about statin therapy',
  sSdm.evidence_note = 'Satisfied by a documented SDM encounter within the last year, regardless of decision outcome. Patients who elect to initiate are also evaluated against strategy:statin-moderate-intensity.',
  sSdm.source_section = 'Recommendation Summary, Grade C',
  sSdm.provenance_guideline = 'guideline:uspstf-statin-2022',
  sSdm.provenance_version = '2022-08-23',
  sSdm.provenance_source_section = 'Recommendation Summary, Grade C',
  sSdm.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// FROM_GUIDELINE edges (Recommendation -> Guideline)
// ---------------------------------------------------------------------------

MATCH (g:Guideline {id: 'guideline:uspstf-statin-2022'}),
      (r1:Recommendation {id: 'rec:statin-initiate-grade-b'})
MERGE (r1)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade B',
  e.provenance_publication_date = date('2022-08-23');

MATCH (g:Guideline {id: 'guideline:uspstf-statin-2022'}),
      (r2:Recommendation {id: 'rec:statin-selective-grade-c'})
MERGE (r2)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade C',
  e.provenance_publication_date = date('2022-08-23');

MATCH (g:Guideline {id: 'guideline:uspstf-statin-2022'}),
      (r3:Recommendation {id: 'rec:statin-insufficient-evidence-grade-i'})
MERGE (r3)-[e:FROM_GUIDELINE]->(g)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade I',
  e.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// OFFERS_STRATEGY edges
//   R1 -> moderate-intensity         (Grade B: initiate)
//   R2 -> SDM                        (Grade C primary satisfier)
//   R2 -> moderate-intensity         (Grade C alternative if patient elects to initiate)
// R3 (Grade I) offers no strategies — evaluator emits status:insufficient_evidence.
// ---------------------------------------------------------------------------

MATCH (r1:Recommendation {id: 'rec:statin-initiate-grade-b'}),
      (sMod:Strategy {id: 'strategy:statin-moderate-intensity'})
MERGE (r1)-[e:OFFERS_STRATEGY]->(sMod)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade B',
  e.provenance_publication_date = date('2022-08-23');

MATCH (r2:Recommendation {id: 'rec:statin-selective-grade-c'}),
      (sSdm:Strategy {id: 'strategy:statin-shared-decision-discussion'})
MERGE (r2)-[e:OFFERS_STRATEGY]->(sSdm)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade C',
  e.provenance_publication_date = date('2022-08-23');

MATCH (r2:Recommendation {id: 'rec:statin-selective-grade-c'}),
      (sMod:Strategy {id: 'strategy:statin-moderate-intensity'})
MERGE (r2)-[e:OFFERS_STRATEGY]->(sMod)
ON CREATE SET
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Recommendation Summary, Grade C',
  e.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// INCLUDES_ACTION edges — moderate-intensity strategy -> 7 statins.
// Clinical entity nodes are created in clinical-entities.cypher; referenced
// here via MATCH. Per guidelines/statins.md: intent=primary_prevention,
// cadence=null, lookback=null, priority=routine for every member.
// ---------------------------------------------------------------------------

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:atorvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:rosuvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:simvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:pravastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:lovastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:fluvastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

MATCH (sMod:Strategy {id: 'strategy:statin-moderate-intensity'}),
      (m:Medication {id: 'med:pitavastatin'})
MERGE (sMod)-[e:INCLUDES_ACTION]->(m)
ON CREATE SET
  e.cadence = null, e.lookback = null, e.priority = 'routine', e.intent = 'primary_prevention',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — moderate-intensity',
  e.provenance_publication_date = date('2022-08-23');

// INCLUDES_ACTION — SDM strategy -> shared-decision procedure.
// intent=shared_decision, cadence=P1Y, lookback=P1Y, priority=routine.

MATCH (sSdm:Strategy {id: 'strategy:statin-shared-decision-discussion'}),
      (p:Procedure {id: 'proc:sdm-statin-discussion'})
MERGE (sSdm)-[e:INCLUDES_ACTION]->(p)
ON CREATE SET
  e.cadence = 'P1Y', e.lookback = 'P1Y', e.priority = 'routine', e.intent = 'shared_decision',
  e.provenance_guideline = 'guideline:uspstf-statin-2022',
  e.provenance_version = '2022-08-23',
  e.provenance_source_section = 'Strategies — shared decision',
  e.provenance_publication_date = date('2022-08-23');
