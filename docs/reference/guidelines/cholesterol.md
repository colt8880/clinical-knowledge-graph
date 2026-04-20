# ACC/AHA 2018 Cholesterol model (v1)

Concrete instantiation of the ACC/AHA 2018 Cholesterol guideline's four statin benefit groups in the v1 knowledge graph. Pairs with the abstract spec in `docs/specs/schema.md` and is the source content for `/graph/seeds/cholesterol.cypher`.

**Source:** Grundy SM, Stone NJ, Bailey AL, et al. *2018 AHA/ACC/AACVPR/AAPA/ABC/ACPM/ADA/AGS/APhA/ASPC/NLA/PCNA Guideline on the Management of Blood Cholesterol.* Circulation. 2019;139(25):e1082-e1143. https://doi.org/10.1161/CIR.0000000000000625

## Guideline node

| Attr | Value |
|---|---|
| id | `guideline:acc-aha-cholesterol-2018` |
| publisher | American Heart Association / American College of Cardiology |
| version | 2018-11-10 |
| effective_date | 2018-11-10 |
| url | https://doi.org/10.1161/CIR.0000000000000625 |
| status | active |

## Evidence grade mapping

ACC/AHA uses a two-axis system: Class of Recommendation (COR) and Level of Evidence (LOE).

| COR | Meaning |
|---|---|
| I | Benefit >>> Risk; treatment should be performed |
| IIa | Benefit >> Risk; reasonable to perform |
| IIb | Benefit ≥ Risk; may be considered |
| III | No benefit or harm; should not be performed |

| LOE | Meaning |
|---|---|
| A | Multiple populations evaluated; data from multiple RCTs or meta-analyses |
| B-R | Moderate; data from 1+ RCTs |
| B-NR | Moderate; data from 1+ well-designed nonrandomized studies |
| C-LD | Limited data |
| C-EO | Expert opinion |

In this model, `evidence_grade` is stored as a string like `"COR I, LOE A"`.

## Recommendations

Four Recommendation nodes, one per statin benefit group.

### R1 — Secondary prevention (clinical ASCVD, age ≤75) {#secondary-prevention}

| Attr | Value |
|---|---|
| id | `rec:accaha-statin-secondary-prevention` |
| title | High-intensity statin for secondary prevention in clinical ASCVD (age ≤75) |
| evidence_grade | COR I, LOE A |
| intent | treatment |
| trigger | patient_state |
| source_section | Section 4.1 — Secondary Prevention |
| clinical_nuance | For patients with clinical ASCVD aged ≤75, high-intensity statin therapy should be initiated or continued with the aim of achieving a ≥50% reduction in LDL-C. If LDL-C remains ≥70 mg/dL on maximally tolerated statin, adding ezetimibe is reasonable (not modeled in v1). Adults >75 are out of scope for this feature. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:ascvd-established] }
  - age_between: { min: 18, max: 75 }
```

Offered strategy: `strategy:accaha-statin-high-intensity`.

#### Clinical ASCVD definition {#ascvd-definition}

"Clinical ASCVD" includes:
- Acute coronary syndromes (SNOMED 394659003)
- History of myocardial infarction (SNOMED 22298006, ICD-10 I21-I25)
- Stable or unstable angina (SNOMED 429559004)
- Coronary or other arterial revascularization
- Stroke / TIA (SNOMED 230690007, ICD-10 I63)
- Peripheral arterial disease (SNOMED 52404001, ICD-10 I73.9, I70.2)

These are captured in the shared `cond:ascvd-established` entity node.

### R2 — Severe hypercholesterolemia (LDL ≥190, age 20-75) {#severe-hypercholesterolemia}

| Attr | Value |
|---|---|
| id | `rec:accaha-statin-severe-hypercholesterolemia` |
| title | High-intensity statin for severe hypercholesterolemia (LDL ≥190, age 20-75) |
| evidence_grade | COR I, LOE B-NR |
| intent | treatment |
| trigger | patient_state |
| source_section | Section 4.2 — Severe Hypercholesterolemia |
| clinical_nuance | Adults aged 20-75 with LDL-C ≥190 mg/dL should be treated with maximally tolerated high-intensity statin without requiring ASCVD risk calculation. This population often has genetic (familial) hypercholesterolemia. If LDL-C remains ≥100 mg/dL on maximally tolerated statin, adding ezetimibe is reasonable (not modeled in v1). |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 20, max: 75 }
  - most_recent_observation_value:
      code: obs:ldl-cholesterol
      window: P2Y
      comparator: gte
      threshold: 190
      unit: mg/dL
  - none_of:
      - has_active_condition: { codes: [cond:ascvd-established] }
```

Exclusion rationale: patients with established ASCVD are routed to R1 (secondary prevention) instead, which also prescribes high-intensity statin but has different LDL targets and follow-up pathways.

Offered strategy: `strategy:accaha-statin-high-intensity`.

### R3 — Diabetes mellitus, age 40-75 {#diabetes}

| Attr | Value |
|---|---|
| id | `rec:accaha-statin-diabetes` |
| title | Moderate-intensity statin for diabetes mellitus, age 40-75 |
| evidence_grade | COR I, LOE A |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Section 4.3 — Diabetes Mellitus |
| clinical_nuance | Adults aged 40-75 with diabetes mellitus should be started on moderate-intensity statin regardless of ASCVD risk score. For those with multiple risk factors or 10-year ASCVD risk ≥7.5%, it is reasonable to use high-intensity statin to reduce LDL-C by ≥50%. Risk enhancers (long duration of diabetes ≥10 years for T2DM, albuminuria ≥30 mcg/mg, eGFR <60, retinopathy, neuropathy, ABI <0.9) support the case for high-intensity. |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 40, max: 75 }
  - has_active_condition: { codes: [cond:diabetes] }
  - none_of:
      - has_active_condition: { codes: [cond:ascvd-established] }
      - most_recent_observation_value:
          code: obs:ldl-cholesterol
          window: P2Y
          comparator: gte
          threshold: 190
          unit: mg/dL
```

Offered strategies:
1. `strategy:accaha-statin-moderate-intensity` (primary)
2. `strategy:accaha-statin-high-intensity` (alternative if ASCVD risk ≥7.5%)

### R4 — Primary prevention, age 40-75, LDL 70-189, no diabetes {#primary-prevention}

| Attr | Value |
|---|---|
| id | `rec:accaha-statin-primary-prevention` |
| title | Moderate-to-high-intensity statin for primary prevention (age 40-75, LDL 70-189, ASCVD risk ≥7.5%) |
| evidence_grade | COR I, LOE A |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Section 4.4 — Primary Prevention |
| clinical_nuance | For adults aged 40-75 without diabetes and with LDL-C 70-189 mg/dL, a 10-year ASCVD risk ≥7.5% warrants moderate-to-high-intensity statin initiation. At borderline risk (5% to <7.5%, COR IIb, LOE B-R), risk enhancers favor statin initiation. A CAC score of 0 supports deferral. |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 40, max: 75 }
  - none_of:
      - has_active_condition: { codes: [cond:ascvd-established] }
      - most_recent_observation_value:
          code: obs:ldl-cholesterol
          window: P2Y
          comparator: gte
          threshold: 190
          unit: mg/dL
      - has_active_condition: { codes: [cond:diabetes] }
  - most_recent_observation_value:
      code: obs:ldl-cholesterol
      window: P2Y
      comparator: gte
      threshold: 70
      unit: mg/dL
  - most_recent_observation_value:
      code: obs:ldl-cholesterol
      window: P2Y
      comparator: lte
      threshold: 189
      unit: mg/dL
  - risk_score_compares:
      name: ascvd_10yr
      comparator: gte
      threshold: 7.5
```

Offered strategies:
1. `strategy:accaha-statin-moderate-intensity` (primary)
2. `strategy:accaha-statin-high-intensity` (alternative)

## Strategies

### `strategy:accaha-statin-high-intensity` {#strategy-high}

High-intensity statin therapy: lowers LDL-C by ≥50%. Two class-level agents.

`INCLUDES_ACTION` edges (`intent: treatment`, `intensity: high`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:atorvastatin` (RxNorm 83367) — atorvastatin 40-80 mg/day
- `med:rosuvastatin` (RxNorm 301542) — rosuvastatin 20-40 mg/day

Strategy is satisfied when the patient has any active medication matching either agent. v1 does not verify dose; class-level matching only.

### `strategy:accaha-statin-moderate-intensity` {#strategy-moderate}

Moderate-intensity statin therapy: lowers LDL-C by 30-49%. Seven class-level agents (same set as USPSTF v0).

`INCLUDES_ACTION` edges (`intent: treatment`, `intensity: moderate`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:atorvastatin` (RxNorm 83367) — atorvastatin 10-20 mg/day
- `med:rosuvastatin` (RxNorm 301542) — rosuvastatin 5-10 mg/day
- `med:simvastatin` (RxNorm 36567) — simvastatin 20-40 mg/day
- `med:pravastatin` (RxNorm 42463) — pravastatin 40-80 mg/day
- `med:lovastatin` (RxNorm 6472) — lovastatin 40 mg/day
- `med:fluvastatin` (RxNorm 41127) — fluvastatin 40 mg bid or 80 mg XL/day
- `med:pitavastatin` (RxNorm 861634) — pitavastatin 2-4 mg/day

Strategy is satisfied when the patient has any active medication matching any agent.

## Clinical entity nodes

All clinical entity nodes referenced by this seed are shared entities defined in `clinical-entities.cypher`. No new clinical entities are created by this seed.

### Conditions (shared)

| Node id | Used by Rec | Notes |
|---|---|---|
| `cond:ascvd-established` | R1 (eligibility), R2-R4 (exclusion) | Same entity as USPSTF statin model |
| `cond:diabetes` | R3 (eligibility), R4 (exclusion) | Type 1 or Type 2 |

### Observations (shared)

| Node id | Used by Rec | Notes |
|---|---|---|
| `obs:ldl-cholesterol` | R2 (threshold ≥190), R4 (range 70-189) | Direct or calculated |

### Medications (shared)

All 7 statin medications from the shared entity layer. Same nodes referenced by USPSTF `strategy:statin-moderate-intensity`.

## Patient-path summary (for the 4 v1 fixtures) {#patient-paths}

| Case | Expected terminal event | Path through the model |
|---|---|---|
| 01-severe-hyperchol-42f | `recommendation_emitted(rec:accaha-statin-severe-hypercholesterolemia, due)` | LDL 230 ≥190; no ASCVD; age 20-75 → R2 eligible; no active statin → due. |
| 02-secondary-prev-58m | `recommendation_emitted(rec:accaha-statin-secondary-prevention, due)` | Post-MI = clinical ASCVD; age ≤75 → R1 eligible; on simvastatin (moderate, not high) → due for high-intensity upgrade. |
| 03-diabetes-55m | `recommendation_emitted(rec:accaha-statin-diabetes, due)` | Diabetes + age 40-75; no ASCVD; LDL <190 → R3 eligible; no active statin → due. |
| 04-primary-prev-below-threshold-48m | No ACC/AHA rec emitted | No ASCVD, no diabetes, LDL 162 (70-189), ASCVD risk 6.1% (<7.5%) → R4 ineligible. |

## Guideline prose (for eval harness Arm B chunking) {#prose}

The following sections render the ACC/AHA 2018 Cholesterol recommendation as continuous prose suitable for text chunking and retrieval. Each section has a stable anchor for chunk boundary alignment.

### Overview {#prose-overview}

The 2018 AHA/ACC Guideline on the Management of Blood Cholesterol identifies four groups of patients who benefit most from statin therapy. These statin benefit groups are defined by the presence of clinical atherosclerotic cardiovascular disease (ASCVD), severe hypercholesterolemia (LDL-C ≥190 mg/dL), diabetes mellitus, or elevated 10-year ASCVD risk in the primary prevention setting. The guideline uses a Class of Recommendation (COR) and Level of Evidence (LOE) system to grade the strength of each recommendation.

### Secondary prevention: clinical ASCVD {#prose-secondary-prevention}

For patients aged 75 years or younger with clinical ASCVD (including acute coronary syndromes, myocardial infarction, stable or unstable angina, coronary or arterial revascularization, stroke, transient ischemic attack, or peripheral arterial disease), the ACC/AHA recommends high-intensity statin therapy (COR I, LOE A). The goal is to achieve a reduction of LDL-C by 50% or more from baseline.

High-intensity statin therapy is defined as a daily dose that lowers LDL-C by approximately 50% or more. The two agents at this intensity level are atorvastatin 40-80 mg/day and rosuvastatin 20-40 mg/day.

If a patient with clinical ASCVD has an LDL-C that remains at or above 70 mg/dL on maximally tolerated high-intensity statin therapy, it is reasonable to add ezetimibe (COR IIa, LOE B-R). For very high-risk ASCVD patients with LDL-C ≥70 mg/dL on maximally tolerated statin plus ezetimibe, a PCSK9 inhibitor may be considered (COR IIa, LOE A). Ezetimibe and PCSK9 inhibitors are not modeled in v1 of this graph.

For adults older than 75 with clinical ASCVD, it is reasonable to continue high-intensity statin therapy or initiate moderate-intensity statin therapy after a clinician-patient discussion of benefits and risks. Adults over 75 are deferred to v2.

### Severe hypercholesterolemia: LDL-C ≥190 mg/dL {#prose-severe-hypercholesterolemia}

Adults aged 20 to 75 years with an LDL-C level of 190 mg/dL or higher should be treated with maximally tolerated high-intensity statin therapy (COR I, LOE B-NR). This recommendation applies without a prior ASCVD risk calculation, as the absolute LDL-C level alone warrants treatment.

Many patients with LDL-C ≥190 mg/dL have a genetic basis for their hypercholesterolemia (familial hypercholesterolemia), though a genetic diagnosis is not required to initiate statin therapy at this threshold. The goal is maximal LDL-C lowering.

If the LDL-C level remains at 100 mg/dL or higher on maximally tolerated statin therapy, adding ezetimibe is reasonable (COR IIa, LOE B-R). If the LDL-C level remains at 100 mg/dL or higher on statin plus ezetimibe, adding a PCSK9 inhibitor may be considered (COR IIb, LOE B-R). These add-on therapies are not modeled in v1.

### Diabetes mellitus: age 40-75 {#prose-diabetes}

For adults aged 40 to 75 years with diabetes mellitus (type 1 or type 2), the ACC/AHA recommends moderate-intensity statin therapy regardless of the estimated 10-year ASCVD risk (COR I, LOE A). Diabetes is considered an independent risk enhancer for ASCVD.

For patients with diabetes who have additional ASCVD risk factors or a 10-year ASCVD risk of 7.5% or greater, it is reasonable to prescribe high-intensity statin therapy with the aim of reducing LDL-C by 50% or more (COR IIa, LOE B-NR). Diabetes-specific risk enhancers that favor high-intensity therapy include long duration of diabetes (≥10 years for type 2, ≥20 years for type 1), albuminuria (≥30 mcg/mg creatinine), estimated GFR less than 60 mL/min/1.73 m², retinopathy, neuropathy, and ankle-brachial index less than 0.9.

### Primary prevention without diabetes: age 40-75, LDL-C 70-189 mg/dL {#prose-primary-prevention}

For adults aged 40 to 75 years without clinical ASCVD or diabetes, with LDL-C levels between 70 and 189 mg/dL, the ACC/AHA recommends an initial assessment of 10-year ASCVD risk using the Pooled Cohort Equations (PCE).

If the estimated 10-year ASCVD risk is 7.5% or greater, the guideline recommends initiating a moderate-intensity statin (COR I, LOE A). If the risk is 7.5% to less than 20%, a clinician-patient risk discussion should consider risk enhancers, the potential for risk-reduction benefits, adverse effects, drug-drug interactions, and patient preferences.

At borderline risk (5% to less than 7.5%), statin therapy may be considered (COR IIb, LOE B-R), especially in the presence of risk-enhancing factors. Risk enhancers include family history of premature ASCVD (males <55 years, females <65 years in first-degree relatives), persistently elevated LDL-C ≥160 mg/dL, metabolic syndrome, chronic kidney disease, chronic inflammatory conditions (rheumatoid arthritis, psoriasis, HIV), history of premature menopause or pre-eclampsia, high-risk ethnicity (e.g., South Asian ancestry), elevated biomarkers (Lp(a) ≥50 mg/dL or nmol/L, apoB ≥130 mg/dL, hsCRP ≥2 mg/L, ABI <0.9), and triglycerides ≥175 mg/dL.

A coronary artery calcium (CAC) score of 0 Agatston units in a patient with borderline or intermediate risk supports deferring statin therapy and reassessing in 5-10 years, provided no high-risk conditions (diabetes, family history of premature ASCVD, or cigarette smoking) are present.

### ASCVD risk calculation {#prose-ascvd}

The 10-year atherosclerotic cardiovascular disease risk is estimated using the 2013 Pooled Cohort Equations (Goff et al.), the same tool referenced by the USPSTF. Required inputs are: age, sex, race (Black vs. non-Black), total cholesterol (mg/dL), HDL cholesterol (mg/dL), systolic blood pressure (mmHg), blood pressure treatment status, diabetes status, and current smoking status.

If a pre-computed ASCVD score is available from the electronic health record, it may be used directly. v1 fixtures supply `risk_scores.ascvd_10yr` directly; no live PCE calculation.

### Statin intensity classification {#prose-intensity}

The ACC/AHA classifies statin therapy into three intensity tiers based on the expected percentage reduction in LDL-C:

**High-intensity** (≥50% LDL-C reduction):
- Atorvastatin 40-80 mg/day
- Rosuvastatin 20-40 mg/day

**Moderate-intensity** (30-49% LDL-C reduction):
- Atorvastatin 10-20 mg/day
- Rosuvastatin 5-10 mg/day
- Simvastatin 20-40 mg/day
- Pravastatin 40-80 mg/day
- Lovastatin 40 mg/day
- Fluvastatin 40 mg bid or 80 mg XL/day
- Pitavastatin 2-4 mg/day

**Low-intensity** (<30% LDL-C reduction):
- Simvastatin 10 mg/day
- Pravastatin 10-20 mg/day
- Lovastatin 20 mg/day
- Fluvastatin 20-40 mg/day
- Pitavastatin 1 mg/day

Low-intensity is not modeled in v1. v1 models at the class level (agent identity), not the dose level. Intensity is tracked as a property on the `INCLUDES_ACTION` edge between Strategy and Medication.

## Deferred for post-v1

- Adults over age 75 (moderate-intensity considerations).
- Ezetimibe add-on therapy for patients not at LDL goal.
- PCSK9 inhibitor intensification pathways.
- Non-statin lipid therapies (fibrates, niacin, bile acid sequestrants).
- Dose-level intensity verification.
- Pediatric or familial hypercholesterolemia genetic testing pathways.
- Cross-guideline edges to USPSTF (F25).

## Related

- `docs/specs/schema.md`
- `docs/specs/predicate-dsl.md`
- `docs/contracts/predicate-catalog.yaml`
- `docs/reference/guidelines/statins.md` — USPSTF statin model (v0)
- `evals/fixtures/cholesterol/` — 4 patient fixtures
