// Canonical shared clinical entity registry.
//
// Contains all Condition, Observation, Medication, and Procedure nodes
// used across guidelines. These are global reference data — they carry
// no domain label (no :USPSTF, :ACC_AHA, etc.). Domain labels belong
// on guideline-scoped nodes (Guideline, Recommendation, Strategy).
//
// Load order: constraints.cypher → this file → guideline seeds.
//
// Primary-key conventions (per ADR 0017):
//   Medication:  code_system = 'RxNorm',  code = RxCUI (class-level)
//   Observation: code_system = 'LOINC',   code = primary LOINC code
//   Procedure:   code_system = 'CPT',     code = most representative CPT
//   Condition:   codings = ['SYSTEM:CODE', ...] (SNOMED + ICD-10-CM)
//
// Existing code-array properties (snomed_codes, icd10_codes, rxnorm_codes,
// loinc_codes, cpt_codes) are retained for evaluator backward compatibility.
// The evaluator's _extract_codes() reads these arrays; primary-key properties
// are for seed-time MERGE deduplication.
//
// Class-level statin RxCUIs: v0 uses class-level codes (ingredient, not
// per-strength). Each RxCUI below is the RxNorm ingredient-level concept.
// Per-strength RxCUIs exist but are out of scope for v0/v1.
//
// MERGE semantics: every node MERGEs on `id`. ON CREATE SET populates all
// properties; ON MATCH SET is a no-op (properties set on first creation).
// Running this file twice is idempotent.
//
// Seed-time uniqueness check for Condition codings runs at the end of
// this file. If two Condition nodes share any (system, code) pair, the
// check returns a non-zero count and the seed script must exit non-zero.

// ---------------------------------------------------------------------------
// Conditions
// ---------------------------------------------------------------------------

MERGE (c:Condition {id: 'cond:ascvd-established'})
ON CREATE SET
  c.display_name = 'Established atherosclerotic cardiovascular disease',
  c.codings = ['SNOMED:394659003', 'SNOMED:429559004', 'SNOMED:230690007', 'SNOMED:22298006', 'SNOMED:52404001', 'ICD10:I20', 'ICD10:I21', 'ICD10:I22', 'ICD10:I23', 'ICD10:I24', 'ICD10:I25', 'ICD10:I63', 'ICD10:I73.9', 'ICD10:I70.2'],
  c.snomed_codes = ['394659003', '429559004', '230690007', '22298006', '52404001'],
  c.icd10_codes = ['I20', 'I21', 'I22', 'I23', 'I24', 'I25', 'I63', 'I73.9', 'I70.2'],
  c.provenance_guideline = 'guideline:uspstf-statin-2022',
  c.provenance_version = '2022-08-23',
  c.provenance_source_section = 'Clinical entity layer',
  c.provenance_publication_date = date('2022-08-23');

MERGE (c:Condition {id: 'cond:diabetes'})
ON CREATE SET
  c.display_name = 'Diabetes mellitus (Type 1 or Type 2)',
  c.codings = ['SNOMED:73211009', 'ICD10:E10', 'ICD10:E11'],
  c.snomed_codes = ['73211009'],
  c.icd10_codes = ['E10', 'E11'],
  c.provenance_guideline = 'guideline:uspstf-statin-2022',
  c.provenance_version = '2022-08-23',
  c.provenance_source_section = 'Clinical entity layer',
  c.provenance_publication_date = date('2022-08-23');

MERGE (c:Condition {id: 'cond:hypertension'})
ON CREATE SET
  c.display_name = 'Essential hypertension',
  c.codings = ['SNOMED:38341003', 'ICD10:I10'],
  c.snomed_codes = ['38341003'],
  c.icd10_codes = ['I10'],
  c.provenance_guideline = 'guideline:uspstf-statin-2022',
  c.provenance_version = '2022-08-23',
  c.provenance_source_section = 'Clinical entity layer',
  c.provenance_publication_date = date('2022-08-23');

MERGE (c:Condition {id: 'cond:dyslipidemia'})
ON CREATE SET
  c.display_name = 'Dyslipidemia / mixed hyperlipidemia',
  c.codings = ['SNOMED:370992007', 'ICD10:E78.5', 'ICD10:E78.2', 'ICD10:E78.0'],
  c.snomed_codes = ['370992007'],
  c.icd10_codes = ['E78.5', 'E78.2', 'E78.0'],
  c.provenance_guideline = 'guideline:uspstf-statin-2022',
  c.provenance_version = '2022-08-23',
  c.provenance_source_section = 'Clinical entity layer',
  c.provenance_publication_date = date('2022-08-23');

MERGE (c:Condition {id: 'cond:familial-hypercholesterolemia'})
ON CREATE SET
  c.display_name = 'Familial hypercholesterolemia',
  c.codings = ['SNOMED:398036000', 'ICD10:E78.01'],
  c.snomed_codes = ['398036000'],
  c.icd10_codes = ['E78.01'],
  c.provenance_guideline = 'guideline:uspstf-statin-2022',
  c.provenance_version = '2022-08-23',
  c.provenance_source_section = 'Clinical entity layer',
  c.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// Observations
// ---------------------------------------------------------------------------

MERGE (o:Observation {id: 'obs:total-cholesterol'})
ON CREATE SET
  o.display_name = 'Total cholesterol',
  o.code = '2093-3',
  o.code_system = 'LOINC',
  o.loinc_codes = ['2093-3'],
  o.unit = 'mg/dL',
  o.provenance_guideline = 'guideline:uspstf-statin-2022',
  o.provenance_version = '2022-08-23',
  o.provenance_source_section = 'Clinical entity layer',
  o.provenance_publication_date = date('2022-08-23');

MERGE (o:Observation {id: 'obs:hdl-cholesterol'})
ON CREATE SET
  o.display_name = 'HDL cholesterol',
  o.code = '2085-9',
  o.code_system = 'LOINC',
  o.loinc_codes = ['2085-9'],
  o.unit = 'mg/dL',
  o.provenance_guideline = 'guideline:uspstf-statin-2022',
  o.provenance_version = '2022-08-23',
  o.provenance_source_section = 'Clinical entity layer',
  o.provenance_publication_date = date('2022-08-23');

MERGE (o:Observation {id: 'obs:ldl-cholesterol'})
ON CREATE SET
  o.display_name = 'LDL cholesterol (direct or calculated)',
  o.code = '2089-1',
  o.code_system = 'LOINC',
  o.loinc_codes = ['2089-1', '13457-7'],
  o.unit = 'mg/dL',
  o.provenance_guideline = 'guideline:uspstf-statin-2022',
  o.provenance_version = '2022-08-23',
  o.provenance_source_section = 'Clinical entity layer',
  o.provenance_publication_date = date('2022-08-23');

MERGE (o:Observation {id: 'obs:blood-pressure'})
ON CREATE SET
  o.display_name = 'Blood pressure panel',
  o.code = '85354-9',
  o.code_system = 'LOINC',
  o.loinc_codes = ['85354-9', '8480-6', '8462-4'],
  o.unit = 'mm[Hg]',
  o.provenance_guideline = 'guideline:uspstf-statin-2022',
  o.provenance_version = '2022-08-23',
  o.provenance_source_section = 'Clinical entity layer',
  o.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// Medications (moderate-intensity statin class members)
// ---------------------------------------------------------------------------

MERGE (m:Medication {id: 'med:atorvastatin'})
ON CREATE SET
  m.display_name = 'Atorvastatin',
  m.code = '83367',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['83367'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:rosuvastatin'})
ON CREATE SET
  m.display_name = 'Rosuvastatin',
  m.code = '301542',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['301542'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:simvastatin'})
ON CREATE SET
  m.display_name = 'Simvastatin',
  m.code = '36567',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['36567'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:pravastatin'})
ON CREATE SET
  m.display_name = 'Pravastatin',
  m.code = '42463',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['42463'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:lovastatin'})
ON CREATE SET
  m.display_name = 'Lovastatin',
  m.code = '6472',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['6472'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:fluvastatin'})
ON CREATE SET
  m.display_name = 'Fluvastatin',
  m.code = '41127',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['41127'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

MERGE (m:Medication {id: 'med:pitavastatin'})
ON CREATE SET
  m.display_name = 'Pitavastatin',
  m.code = '861634',
  m.code_system = 'RxNorm',
  m.rxnorm_codes = ['861634'],
  m.provenance_guideline = 'guideline:uspstf-statin-2022',
  m.provenance_version = '2022-08-23',
  m.provenance_source_section = 'Strategies — moderate-intensity',
  m.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// Procedures
// ---------------------------------------------------------------------------

MERGE (p:Procedure {id: 'proc:sdm-statin-discussion'})
ON CREATE SET
  p.display_name = 'Shared decision-making discussion about statin therapy',
  p.code = '99401',
  p.code_system = 'CPT',
  p.snomed_codes = ['710925007'],
  p.cpt_codes = ['99401', '99402', '99403', '99404'],
  p.provenance_guideline = 'guideline:uspstf-statin-2022',
  p.provenance_version = '2022-08-23',
  p.provenance_source_section = 'Strategies — shared decision',
  p.provenance_publication_date = date('2022-08-23');

// ---------------------------------------------------------------------------
// Seed-time uniqueness check: Condition codings
//
// Neo4j cannot enforce native uniqueness on list-element contents.
// This query detects two Condition nodes sharing any (system, code) pair.
// The seed script checks that this returns 0; if not, it exits non-zero.
// ---------------------------------------------------------------------------

MATCH (a:Condition), (b:Condition)
WHERE a <> b AND ANY(c IN a.codings WHERE c IN b.codings)
RETURN count(*) AS duplicate_coding_pairs;
