# ADA 2024 Diabetes model (v2)

Concrete instantiation of the ADA Standards of Medical Care in Diabetes—2024, pharmacologic glycemic management for type 2 diabetes, in the v2 knowledge graph. Pairs with the abstract spec in `docs/specs/schema.md` and is the source content for `/graph/seeds/ada-diabetes.cypher`.

**Source:** American Diabetes Association Professional Practice Committee. Standards of Medical Care in Diabetes—2024. *Diabetes Care.* 2024;47(Suppl 1). https://doi.org/10.2337/dc24-SINT

## Guideline node

| Attr | Value |
|---|---|
| id | `guideline:ada-diabetes-2024` |
| publisher | American Diabetes Association |
| version | 2024-01-01 |
| effective_date | 2024-01-01 |
| url | https://doi.org/10.2337/dc24-SINT |
| status | active |

## Evidence grade mapping {#evidence-grades}

ADA uses a letter-based evidence grading system.

| Grade | Meaning |
|---|---|
| A | Clear evidence from well-conducted, generalizable randomized controlled trials |
| B | Supportive evidence from well-conducted cohort studies |
| C | Supportive evidence from poorly controlled or uncontrolled studies |
| E | Expert consensus or clinical experience |

In this model, `evidence_grade` is stored as a string like `"ADA-A"`.

## Recommendations

Five Recommendation nodes corresponding to five pharmacologic management decision points.

### R1 — Metformin first-line therapy {#metformin-first-line}

| Attr | Value |
|---|---|
| id | `rec:ada-metformin-first-line` |
| title | Metformin as first-line pharmacotherapy for type 2 diabetes |
| evidence_grade | ADA-A |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 9 — Pharmacologic Approaches to Glycemic Treatment |
| clinical_nuance | Metformin should be initiated at diagnosis of T2DM unless contraindicated. Reduce dose when eGFR 30-45; contraindicated when eGFR < 30. GI intolerance mitigated by extended-release. No hypoglycemia risk as monotherapy. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:diabetes] }
  - age_between: { min: 18, max: 120 }
none_of:
  - has_medication_active: { codes: [med:metformin] }
  - most_recent_observation_value:
      code: obs:egfr
      window: P2Y
      comparator: lt
      threshold: 30
      unit: mL/min/1.73m2
```

Offered strategy: `strategy:ada-metformin`.

### R2 — SGLT2 inhibitor for cardiorenal benefit {#sglt2-cardiorenal}

| Attr | Value |
|---|---|
| id | `rec:ada-sglt2-cardiorenal` |
| title | SGLT2 inhibitor for cardiorenal benefit in T2DM |
| evidence_grade | ADA-A |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 9 / Chapter 10 |
| clinical_nuance | Independent of A1C. For patients with established ASCVD, HF, or CKD (eGFR 20-60 or albuminuria ACR ≥30). eGFR < 20 contraindicated for initiation. EMPA-REG, CANVAS, DECLARE-TIMI 58, CREDENCE, DAPA-CKD, EMPA-KIDNEY evidence. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:diabetes] }
  - age_between: { min: 18, max: 120 }
  - most_recent_observation_value:
      code: obs:egfr
      window: P2Y
      comparator: gte
      threshold: 20
      unit: mL/min/1.73m2
  - any_of:
      - has_active_condition: { codes: [cond:ascvd-established] }
      - has_active_condition: { codes: [cond:heart-failure] }
      - most_recent_observation_value:
          code: obs:egfr
          window: P2Y
          comparator: lte
          threshold: 60
          unit: mL/min/1.73m2
      - most_recent_observation_value:
          code: obs:urine-acr
          window: P2Y
          comparator: gte
          threshold: 30
          unit: mg/g
none_of:
  - has_medication_active: { codes: [med:empagliflozin, med:dapagliflozin, med:canagliflozin] }
```

Offered strategy: `strategy:ada-sglt2-cardiorenal`.

#### SGLT2i dual indication {#sglt2-dual}

ADA recommends SGLT2i for cardiorenal benefit *independent of A1C*. This is a separate Rec from glycemic intensification (R4). The same medication class appears in both R2 and R4 with different triggers — R2 is clinical (ASCVD/HF/CKD), R4 is metabolic (A1C above target). Both can fire for the same patient. This parallels KDIGO's SGLT2i recommendation and is the primary cross-guideline interaction target for F53.

### R3 — GLP-1 RA for cardiovascular benefit {#glp1ra-cvd}

| Attr | Value |
|---|---|
| id | `rec:ada-glp1ra-cvd-benefit` |
| title | GLP-1 receptor agonist for cardiovascular benefit in T2DM |
| evidence_grade | ADA-A |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 9 — GLP-1 Receptor Agonists |
| clinical_nuance | For patients with established ASCVD or high CVD risk (age ≥55 with hypertension, dyslipidemia, or smoking). SUSTAIN-6, PIONEER 6 (semaglutide), LEADER (liraglutide), REWIND (dulaglutide) trial evidence. Can be used with SGLT2i for additive benefit. Weight loss is additional benefit. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:diabetes] }
  - age_between: { min: 18, max: 120 }
  - any_of:
      - has_active_condition: { codes: [cond:ascvd-established] }
      - all_of:
          - age_between: { min: 55, max: 120 }
          - any_of:
              - has_active_condition: { codes: [cond:hypertension] }
              - has_active_condition: { codes: [cond:dyslipidemia] }
              - smoking_status_is: { values: [current_some_day, current_every_day] }
none_of:
  - has_medication_active: { codes: [med:semaglutide, med:liraglutide, med:dulaglutide] }
```

Offered strategy: `strategy:ada-glp1ra-cvd`.

### R4 — Intensification for glycemic control {#intensification}

| Attr | Value |
|---|---|
| id | `rec:ada-intensification` |
| title | Intensification of glycemic therapy when A1C remains above target |
| evidence_grade | ADA-A |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 9 — Pharmacologic Approaches to Glycemic Treatment |
| clinical_nuance | When A1C ≥7% on metformin, add a second agent. SGLT2i if CKD/HF predominates; GLP-1 RA if ASCVD/weight is priority; insulin if A1C very high (≥10%) or symptomatic. A1C <7% target for most adults; individualize for frail/elderly. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:diabetes] }
  - age_between: { min: 18, max: 120 }
  - has_medication_active: { codes: [med:metformin] }
  - most_recent_observation_value:
      code: obs:hba1c
      window: P1Y
      comparator: gte
      threshold: 7
      unit: "%"
```

Offered strategies (three alternatives):
1. `strategy:ada-sglt2-intensification` — add SGLT2i
2. `strategy:ada-glp1ra-intensification` — add GLP-1 RA
3. `strategy:ada-insulin-intensification` — add insulin

#### A1C target {#a1c-target}

ADA recommends A1C < 7% for most nonpregnant adults. This model uses 7% as a simple threshold. Individualized targets (< 6.5% for young, healthy patients; < 8% for frail/elderly with comorbidities) are documented in `clinical_nuance`, not modeled as separate Recs.

### R5 — Statin for diabetic patients {#statin-for-diabetes}

| Attr | Value |
|---|---|
| id | `rec:ada-statin-for-diabetes` |
| title | Statin therapy for adults with diabetes aged 40-75 |
| evidence_grade | ADA-A |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Chapter 10 — Cardiovascular Disease and Risk Management |
| clinical_nuance | Moderate-intensity statin for all diabetic adults 40-75 regardless of risk score. High-intensity if multiple ASCVD risk factors (LDL ≥100, HTN, smoking, obesity, family history). ADA defers to ACC/AHA for dosing details. |

Structured eligibility:

```yaml
all_of:
  - has_active_condition: { codes: [cond:diabetes] }
  - age_between: { min: 40, max: 75 }
none_of:
  - has_medication_active: { codes: [med:atorvastatin, med:rosuvastatin, med:simvastatin, med:pravastatin, med:lovastatin, med:fluvastatin, med:pitavastatin] }
```

Offered strategies:
1. `strategy:ada-statin-moderate` (primary)
2. `strategy:ada-statin-high` (alternative if ASCVD risk factors)

#### Statin overlap with ACC/AHA {#statin-overlap}

ADA R5 (statin for diabetic adults 40-75) is nearly identical to ACC/AHA R3 (diabetes statin benefit group). In F53, this will become a convergence relationship. Both recommend moderate-intensity; both suggest high-intensity escalation for higher-risk patients. The shared entity layer handles deduplication at the medication level.

## Strategies

### `strategy:ada-metformin` {#strategy-metformin}

First-line metformin monotherapy. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:metformin` (RxNorm 6809)

Strategy satisfied when patient has an active metformin prescription.

### `strategy:ada-sglt2-cardiorenal` {#strategy-sglt2-cardiorenal}

SGLT2 inhibitor for cardiorenal benefit. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:empagliflozin` (RxNorm 1545653)
- `med:dapagliflozin` (RxNorm 1488564)
- `med:canagliflozin` (RxNorm 1373458)

Strategy satisfied when patient has any SGLT2i active.

### `strategy:ada-glp1ra-cvd` {#strategy-glp1ra-cvd}

GLP-1 RA for cardiovascular benefit. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:semaglutide` (RxNorm 1991302)
- `med:liraglutide` (RxNorm 475968)
- `med:dulaglutide` (RxNorm 1551291)

Strategy satisfied when patient has any GLP-1 RA active.

### `strategy:ada-sglt2-intensification` {#strategy-sglt2-intens}

Add SGLT2 inhibitor for glycemic intensification. Same three medications as the cardiorenal strategy but offered under a different Rec (R4 vs. R2).

### `strategy:ada-glp1ra-intensification` {#strategy-glp1ra-intens}

Add GLP-1 RA for glycemic intensification. Same three medications as the CVD strategy but offered under R4.

### `strategy:ada-insulin-intensification` {#strategy-insulin-intens}

Add basal insulin for glycemic intensification. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:insulin-glargine` (RxNorm 274783) — basal insulin
- `med:insulin-lispro` (RxNorm 86009) — rapid-acting insulin

Strategy satisfied when patient has any insulin active.

### `strategy:ada-statin-moderate` {#strategy-statin-moderate}

Moderate-intensity statin for diabetes. Same seven class-level statins as USPSTF v0 and ACC/AHA moderate-intensity. `INCLUDES_ACTION` edges with `intensity: moderate`.

### `strategy:ada-statin-high` {#strategy-statin-high}

High-intensity statin for diabetes with ASCVD risk factors. Two agents (atorvastatin, rosuvastatin) with `intensity: high`.

## Clinical entity nodes

### Conditions (new in F52)

| Node id | codings | Notes |
|---|---|---|
| `cond:heart-failure` | SNOMED:84114007, ICD10:I50, I50.9, I50.2, I50.4 | All HF types. HFrEF/HFpEF distinction deferred. |

### Conditions (shared, existing)

| Node id | Used by Rec | Notes |
|---|---|---|
| `cond:diabetes` | R1-R5 (eligibility) | Type 1 or Type 2 |
| `cond:ascvd-established` | R2, R3 (cardiorenal/CVD trigger) | Same entity as USPSTF/ACC-AHA |
| `cond:hypertension` | R3 (high CVD risk criterion) | |
| `cond:dyslipidemia` | R3 (high CVD risk criterion) | |

### Observations (new in F52)

| Node id | loinc_codes | Unit | Notes |
|---|---|---|---|
| `obs:hba1c` | 4548-4, 17856-6 | % | Hemoglobin A1c |
| `obs:fasting-plasma-glucose` | 1558-6 | mg/dL | Diagnostic, not used in eligibility predicates |

### Observations (shared, existing)

| Node id | Used by Rec | Notes |
|---|---|---|
| `obs:egfr` | R1 (contraindication), R2 (eGFR gate) | CKD-EPI 2021 preferred |
| `obs:urine-acr` | R2 (albuminuria trigger) | |

### Medications (new in F52)

| Node id | rxnorm_codes | Class | Notes |
|---|---|---|---|
| `med:metformin` | 6809 | Biguanide | First-line therapy |
| `med:canagliflozin` | 1373458 | SGLT2 inhibitor | CANVAS trial evidence |
| `med:semaglutide` | 1991302 | GLP-1 RA | SUSTAIN-6 / PIONEER 6 |
| `med:liraglutide` | 475968 | GLP-1 RA | LEADER trial |
| `med:dulaglutide` | 1551291 | GLP-1 RA | REWIND trial |
| `med:insulin-glargine` | 274783 | Basal insulin | Long-acting |
| `med:insulin-lispro` | 86009 | Rapid-acting insulin | Prandial |

### Medications (shared, existing)

| Node id | Used by Rec | Notes |
|---|---|---|
| `med:empagliflozin` | R2 (SGLT2i) | Shared with KDIGO |
| `med:dapagliflozin` | R2 (SGLT2i) | Shared with KDIGO |
| All 7 statins | R5 (statin) | Shared with USPSTF/ACC-AHA/KDIGO |

## Patient-path summary (for the 4 v2 fixtures) {#patient-paths}

| Case | Expected Recs | Path through the model |
|---|---|---|
| 01 | R1 (metformin), R5 (statin) | 52M, newly diagnosed T2DM, A1C 7.8%, no CVD, no CKD, eGFR 85. No metformin → R1 fires. Age 40-75 + diabetes → R5 fires. A1C < 7% threshold not met for R4 (not on metformin yet). No ASCVD/HF/CKD → R2 ineligible. No ASCVD/high risk → R3 ineligible. |
| 02 | R2 (SGLT2i), R3 (GLP-1 RA), R5 (statin high-intensity) | 60F, on metformin, A1C 8.2%, established ASCVD (prior MI), eGFR 62. ASCVD → R2 + R3 fire. On metformin + A1C ≥7% → R4 fires. Age 40-75 + diabetes → R5 fires. |
| 03 | R2 (SGLT2i), R4 (intensification), R5 (statin) | 58M, on metformin, A1C 9.1%, CKD 3a (eGFR 50), albuminuria A2 (ACR 120), HF. CKD + HF → R2 fires. On metformin + A1C ≥7% → R4 fires. Age 40-75 + diabetes → R5 fires. No established ASCVD → R3 requires high-risk alternative path. |
| 04 | R5 (statin moderate) | 45F, on metformin + empagliflozin, A1C 6.8%, no CVD, eGFR 92. A1C < 7% → R4 ineligible. Already on SGLT2i → R2 ineligible. No ASCVD → R3 ineligible. On metformin → R1 ineligible. Age 40-75 + diabetes → R5 fires. |

## Cross-guideline overlap (documented, not connected until F53) {#cross-guideline}

### SGLT2i overlap with KDIGO

ADA R2 recommends SGLT2i for cardiorenal benefit in T2DM with CKD. KDIGO R2 recommends SGLT2i for CKD with T2DM. Both use the same shared medication entities (empagliflozin, dapagliflozin). ADA additionally includes canagliflozin. The overlap is substantial — same medications, overlapping patient populations, shared evidence base (CREDENCE, DAPA-CKD, EMPA-KIDNEY). F53 will determine whether this is a convergence or a modification relationship.

### Statin overlap with ACC/AHA

ADA R5 and ACC/AHA R3 both recommend statin therapy for diabetic adults 40-75. Both recommend moderate-intensity as default, with high-intensity for higher-risk patients. The shared entity layer handles deduplication. F53 may not require explicit edges — the convergence is implicit through shared medication entities.

### Metformin eGFR interaction with KDIGO

ADA R1 contraindicates metformin at eGFR < 30 and recommends dose reduction at eGFR 30-45. KDIGO does not directly address metformin but the eGFR thresholds align with KDIGO's CKD staging. This is documented but not connected until F53.

## Guideline prose (for eval harness Arm B chunking) {#prose}

### Overview {#prose-overview}

The American Diabetes Association Standards of Medical Care in Diabetes—2024 provides comprehensive, evidence-based recommendations for the diagnosis and management of diabetes. This model covers Chapter 9 (Pharmacologic Approaches to Glycemic Treatment) and Chapter 10 (Cardiovascular Disease and Risk Management) for type 2 diabetes in adults. Five decision points are modeled: metformin first-line therapy, SGLT2 inhibitors for cardiorenal benefit, GLP-1 receptor agonists for cardiovascular benefit, glycemic intensification beyond metformin, and statin therapy.

### Metformin first-line therapy {#prose-metformin}

Metformin is the preferred initial pharmacologic agent for the treatment of type 2 diabetes (ADA Evidence Grade A). It should be initiated at or soon after diagnosis unless there are contraindications. Metformin is effective at lowering hemoglobin A1C by approximately 1.0-1.5%, has a well-established safety profile, does not cause hypoglycemia when used as monotherapy, is weight-neutral or associated with modest weight loss, has low cost, and has possible cardiovascular benefit.

Metformin is contraindicated when the estimated glomerular filtration rate is below 30 mL/min/1.73m2. When eGFR is between 30 and 45 mL/min/1.73m2, metformin should be used at a reduced dose, typically no more than 1000 mg per day, with close monitoring of renal function. Common side effects include gastrointestinal intolerance, which can be mitigated by using the extended-release formulation and by gradual dose titration. Long-term use may cause vitamin B12 deficiency; periodic monitoring is advised.

### SGLT2 inhibitors for cardiorenal benefit {#prose-sglt2}

Among patients with type 2 diabetes who have established atherosclerotic cardiovascular disease, heart failure, or chronic kidney disease, an SGLT2 inhibitor with demonstrated cardiorenal benefit should be used as part of the glucose-lowering regimen, independent of the current hemoglobin A1C level (ADA Evidence Grade A). This recommendation is independent of and additive to metformin therapy.

The evidence base for this recommendation includes multiple landmark randomized controlled trials. EMPA-REG OUTCOME demonstrated that empagliflozin reduced the composite of cardiovascular death, nonfatal myocardial infarction, and nonfatal stroke by 14% in patients with T2DM and established ASCVD. CANVAS showed that canagliflozin reduced the composite MACE endpoint by 14%. DAPA-CKD demonstrated that dapagliflozin reduced the composite kidney outcome by 39% in patients with CKD, with consistent benefit regardless of diabetes status. EMPA-KIDNEY extended these findings to a broader CKD population.

SGLT2 inhibitors should not be initiated when eGFR is below 20 mL/min/1.73m2. Once initiated, they may be continued below eGFR 20 unless not tolerated or kidney replacement therapy begins. An initial decline in eGFR of 10-30% is expected and is hemodynamically mediated and reversible; clinicians should not discontinue the medication based on this initial dip alone.

The three SGLT2 inhibitors with proven cardiorenal benefit modeled here are empagliflozin, dapagliflozin, and canagliflozin.

### GLP-1 receptor agonists for cardiovascular benefit {#prose-glp1ra}

Among patients with type 2 diabetes who have established atherosclerotic cardiovascular disease or indicators of high cardiovascular risk, a GLP-1 receptor agonist with proven cardiovascular benefit is recommended to reduce the risk of major adverse cardiovascular events (ADA Evidence Grade A).

The SUSTAIN-6 trial demonstrated that subcutaneous semaglutide reduced the risk of major adverse cardiovascular events by 26% in patients with T2DM and high cardiovascular risk. LEADER showed that liraglutide reduced the composite of cardiovascular death, nonfatal myocardial infarction, and nonfatal stroke by 13%. REWIND demonstrated that dulaglutide reduced MACE by 12% in a broader T2DM population, including patients without established ASCVD but with cardiovascular risk factors.

High cardiovascular risk, in the absence of established ASCVD, is defined as age 55 years or older with coronary, carotid, or lower extremity artery stenosis greater than 50%, left ventricular hypertrophy, or the presence of at least two cardiovascular risk factors such as hypertension, dyslipidemia, or current smoking.

GLP-1 receptor agonists and SGLT2 inhibitors can be used together for additive cardiovascular and metabolic benefit. Weight loss is an additional clinical benefit of GLP-1 RAs.

### Glycemic intensification {#prose-intensification}

For patients with type 2 diabetes who are already on metformin and whose hemoglobin A1C remains at or above 7%, a second glucose-lowering agent should be added (ADA Evidence Grade A). The choice of the second agent depends on patient-specific factors including the presence of cardiovascular disease, heart failure, chronic kidney disease, need for weight management, cost, and risk of hypoglycemia.

If atherosclerotic cardiovascular disease or indicators of high cardiovascular risk predominate, a GLP-1 receptor agonist with proven cardiovascular benefit is preferred. If heart failure or chronic kidney disease predominates, an SGLT2 inhibitor with proven benefit in these conditions is preferred. If the hemoglobin A1C is very high (10% or greater) or the patient has symptomatic hyperglycemia (polyuria, polydipsia, weight loss), insulin therapy (typically starting with basal insulin such as insulin glargine) should be considered.

The A1C target of less than 7% is appropriate for most nonpregnant adults. Less stringent targets (for example, less than 8%) may be appropriate for patients with limited life expectancy, advanced micro- or macrovascular complications, extensive comorbid conditions, long-standing diabetes in whom the goal is difficult to achieve despite diabetes self-management education, appropriate glucose monitoring, and effective doses of multiple glucose-lowering agents including insulin.

### Statin therapy for diabetes {#prose-statin}

For adults aged 40 to 75 years with diabetes mellitus (type 1 or type 2), the ADA recommends at least moderate-intensity statin therapy regardless of the estimated 10-year ASCVD risk (ADA Evidence Grade A). Diabetes is considered an independent risk factor for atherosclerotic cardiovascular disease.

For patients with diabetes who have additional ASCVD risk factors — including LDL cholesterol at or above 100 mg/dL, hypertension, current smoking, overweight or obesity, or family history of premature ASCVD — high-intensity statin therapy is recommended to achieve a 50% or greater reduction in LDL cholesterol. ADA defers to the ACC/AHA 2018 Cholesterol guideline for detailed statin dosing recommendations.

Moderate-intensity statin therapy is defined as a daily dose expected to lower LDL cholesterol by 30-49%. Seven class-level statin agents are available at moderate intensity: atorvastatin, rosuvastatin, simvastatin, pravastatin, lovastatin, fluvastatin, and pitavastatin. High-intensity statin therapy lowers LDL cholesterol by 50% or more and is available with atorvastatin 40-80 mg per day or rosuvastatin 20-40 mg per day.

### Exclusions from this model {#prose-exclusions}

The following ADA recommendations are NOT modeled in v2:

**Type 1 diabetes:** T1DM has distinct pharmacologic management centered on insulin therapy from diagnosis; it does not follow the metformin-first-line pathway.

**Non-pharmacologic management:** Diet, exercise, weight management, and bariatric surgery recommendations are clinically important but are not pharmacologic decision points.

**Insulin titration algorithms:** Complex multi-step basal-bolus titration algorithms are deferred to v3.

**Second-line agents with weaker cardiorenal evidence:** DPP-4 inhibitors (sitagliptin, saxagliptin, linagliptin), thiazolidinediones (pioglitazone), and sulfonylureas (glipizide, glimepiride) are available add-on options but lack the cardiorenal benefit evidence of SGLT2i and GLP-1 RA.

**Gestational diabetes:** Managed under a separate ADA chapter with distinct screening, diagnosis, and treatment algorithms.

**Continuous glucose monitoring:** CGM recommendations affect monitoring strategy but not pharmacologic decision points.

**Microvascular complications beyond CKD:** Retinopathy screening, neuropathy management, and foot care are distinct decision domains.

## Deferred for post-v2

- Cross-guideline edges to KDIGO, ACC/AHA, and USPSTF (F53).
- Multi-morbidity fixtures exercising 3-4 guidelines (F54).
- Type 1 diabetes management.
- Insulin titration algorithms.
- DPP-4 inhibitors, thiazolidinediones, sulfonylureas.
- Non-pharmacologic management.
- Gestational diabetes.
- CGM recommendations.
- ADA's detailed statin dosing tables (ACC/AHA handles this).

## Related

- `docs/specs/schema.md`
- `docs/specs/predicate-dsl.md`
- `docs/contracts/predicate-catalog.yaml`
- `docs/reference/guidelines/statins.md` — USPSTF statin model (v0)
- `docs/reference/guidelines/cholesterol.md` — ACC/AHA cholesterol model (v1)
- `docs/reference/guidelines/kdigo-ckd.md` — KDIGO CKD model (v1)
- `evals/fixtures/diabetes/` — 4 patient fixtures
