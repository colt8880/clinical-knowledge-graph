# KDIGO 2024 CKD model (v1)

Concrete instantiation of the KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease in the v1 knowledge graph. Pairs with the abstract spec in `docs/specs/schema.md` and is the source content for `/graph/seeds/kdigo-ckd.cypher`.

**Source:** KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease. *Kidney International.* 2024;105(4S):S117-S314. https://doi.org/10.1016/j.kint.2023.10.018

## Guideline node

| Attr | Value |
|---|---|
| id | `guideline:kdigo-ckd-2024` |
| publisher | Kidney Disease: Improving Global Outcomes (KDIGO) |
| version | 2024-03-14 |
| effective_date | 2024-03-14 |
| url | https://doi.org/10.1016/j.kint.2023.10.018 |
| status | active |

## Evidence grade mapping

KDIGO uses the GRADE system (Grading of Recommendations Assessment, Development and Evaluation).

| Grade | Strength of recommendation |
|---|---|
| 1 | Strong ("we recommend") |
| 2 | Weak / discretionary ("we suggest") |

| Evidence quality | Meaning |
|---|---|
| A | High — further research unlikely to change confidence |
| B | Moderate — further research likely to have an important impact |
| C | Low — further research very likely to have an important impact |
| D | Very low — any estimate of effect is very uncertain |

In this model, `evidence_grade` is stored as a string like `"1A"` (strong recommendation, high evidence) or `"1B"` (strong, moderate evidence).

## CKD staging as predicate {#staging-as-predicate}

**Design decision:** CKD stage is modeled as a derived predicate over eGFR and ACR observations, NOT as a synthesized Condition node. Rationale:

1. **Matches KDIGO's framing.** KDIGO describes staging as the output of applying eGFR and ACR cutoffs to lab values, not as an independent diagnosis.
2. **Avoids virtual-node drift.** A `CKD_Stage_3a` Condition node would be a synthesized concept not directly present in FHIR patient data. The evaluator would need to create it at runtime, adding a hidden state transformation.
3. **Predicate composition is cleaner.** `most_recent_observation_value(obs:egfr, lt, 60)` is directly auditable in the trace. A Stage node would require explaining how it was derived.

### CKD staging reference (KDIGO heatmap)

| Stage | eGFR (mL/min/1.73m2) | Description |
|---|---|---|
| G1 | ≥90 | Normal or high |
| G2 | 60-89 | Mildly decreased |
| G3a | 45-59 | Mildly to moderately decreased |
| G3b | 30-44 | Moderately to severely decreased |
| G4 | 15-29 | Severely decreased |
| G5 | <15 | Kidney failure |

| Category | ACR (mg/g) | Description |
|---|---|---|
| A1 | <30 | Normal to mildly increased |
| A2 | 30-300 | Moderately increased |
| A3 | >300 | Severely increased |

### Simplifications in v1

- **Single eGFR measurement.** KDIGO formally requires two eGFR measurements ≥3 months apart to confirm CKD. v1 fixtures use a single eGFR. The temporal confirmation requirement can be added in v2 when observation history enters the patient-context schema.
- **eGFR ≥15 as proxy for "not on dialysis."** KDIGO distinguishes G5 (eGFR <15) from G5D (on dialysis). v1 does not model dialysis status; eGFR ≥15 is used as the proxy.
- **Heatmap risk categories skipped.** KDIGO's Low/Moderate/High/Very High risk grid (G × A) is a reporting tool, not a decision-point modifier for the 4 Recs modeled here.

## Recommendations

Four Recommendation nodes corresponding to four KDIGO CKD management decision points.

### R1 — CKD monitoring (eGFR + albuminuria) {#ckd-monitoring}

| Attr | Value |
|---|---|
| id | `rec:kdigo-ckd-monitoring` |
| title | Monitor eGFR and urine ACR in patients with CKD |
| evidence_grade | 1B |
| intent | surveillance |
| trigger | patient_state |
| source_section | Chapter 1 — Evaluation of CKD |
| clinical_nuance | At least annual monitoring; frequency increases with severity. Two eGFR measurements ≥3 months apart formally required to confirm CKD; v1 uses single eGFR. |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 18, max: 120 }
  - any_of:
      - most_recent_observation_value:
          code: obs:egfr
          window: P2Y
          comparator: lt
          threshold: 60
          unit: mL/min/1.73m2
      - most_recent_observation_value:
          code: obs:urine-acr
          window: P2Y
          comparator: gte
          threshold: 30
          unit: mg/g
```

Semantics: adults with either reduced eGFR (<60) or elevated albuminuria (ACR ≥30) should have regular monitoring.

Offered strategy: `strategy:kdigo-ckd-monitoring`.

### R2 — SGLT2 inhibitor for CKD {#sglt2-for-ckd}

| Attr | Value |
|---|---|
| id | `rec:kdigo-sglt2-for-ckd` |
| title | SGLT2 inhibitor for CKD with T2DM or significant albuminuria |
| evidence_grade | 1A |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 3, Recommendation 3.8.1 |
| clinical_nuance | Empagliflozin or dapagliflozin recommended. eGFR ≥20 required for initiation; may continue below once started. Initial eGFR dip of 10-30% is expected and reversible. |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 18, max: 120 }
  - most_recent_observation_value:
      code: obs:egfr
      window: P2Y
      comparator: gte
      threshold: 20
      unit: mL/min/1.73m2
  - any_of:
      # Path 1: CKD + diabetes
      - all_of:
          - has_active_condition: { codes: [cond:diabetes] }
          - most_recent_observation_value:
              code: obs:egfr
              window: P2Y
              comparator: lt
              threshold: 60
              unit: mL/min/1.73m2
      # Path 2: significant albuminuria regardless of diabetes
      - most_recent_observation_value:
          code: obs:urine-acr
          window: P2Y
          comparator: gte
          threshold: 200
          unit: mg/g
none_of:
  - has_medication_active: { codes: [med:empagliflozin, med:dapagliflozin] }
```

Semantics: two pathways — CKD with diabetes (eGFR 20-59), or significant albuminuria (ACR ≥200) regardless of diabetes. eGFR <20 is a contraindication for new starts.

Offered strategy: `strategy:kdigo-sglt2-inhibitor`.

### R3 — Statin for CKD patients ≥50 {#statin-for-ckd}

| Attr | Value |
|---|---|
| id | `rec:kdigo-statin-for-ckd` |
| title | Moderate-intensity statin for CKD patients aged ≥50, not on dialysis |
| evidence_grade | 1A |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Chapter 3, Recommendation 3.5.1 |
| clinical_nuance | Moderate-intensity specifically recommended in CKD G3-G5 (not high-intensity) due to altered pharmacokinetics and myopathy risk. This is the key modifier anchor for F26. |

Structured eligibility:

```yaml
all_of:
  - age_greater_than_or_equal: { value: 50 }
  - most_recent_observation_value:
      code: obs:egfr
      window: P2Y
      comparator: lt
      threshold: 60
      unit: mL/min/1.73m2
  - most_recent_observation_value:
      code: obs:egfr
      window: P2Y
      comparator: gte
      threshold: 15
      unit: mL/min/1.73m2
none_of:
  - has_medication_active: { codes: [med:atorvastatin, med:rosuvastatin, med:simvastatin, med:pravastatin, med:lovastatin, med:fluvastatin, med:pitavastatin] }
```

Semantics: adults ≥50 with CKD (eGFR 15-59) not already on a statin. KDIGO recommends moderate-intensity over high-intensity in this population.

Offered strategy: `strategy:kdigo-statin-moderate-ckd`.

### R4 — ACEi/ARB for albuminuric CKD {#acei-arb-for-ckd}

| Attr | Value |
|---|---|
| id | `rec:kdigo-acei-arb-for-ckd` |
| title | ACE inhibitor or ARB for CKD with albuminuria (ACR ≥30) |
| evidence_grade | 1B |
| intent | treatment |
| trigger | patient_state |
| source_section | Chapter 3, Recommendation 3.2.1 |
| clinical_nuance | ACEi or ARB (not both). Strongest evidence for A3 (ACR ≥300) and with diabetes or hypertension. Titrate to maximally tolerated dose. Monitor potassium and creatinine 2-4 weeks after initiation. |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 18, max: 120 }
  - most_recent_observation_value:
      code: obs:urine-acr
      window: P2Y
      comparator: gte
      threshold: 30
      unit: mg/g
none_of:
  - has_medication_active: { codes: [med:lisinopril, med:enalapril, med:ramipril, med:losartan, med:valsartan, med:irbesartan] }
```

Semantics: adults with albuminuria (ACR ≥30, categories A2-A3) not already on an ACEi or ARB.

Offered strategy: `strategy:kdigo-acei-arb`.

## Strategies

### `strategy:kdigo-ckd-monitoring`

Periodic renal function monitoring. `INCLUDES_ACTION` edges:
- `obs:egfr` (LOINC 48642-3) — `cadence: P1Y`, `lookback: P1Y`, `intent: surveillance`
- `obs:urine-acr` (LOINC 9318-7) — `cadence: P1Y`, `lookback: P1Y`, `intent: surveillance`

Strategy is **conjunction**: both eGFR and ACR must have been checked within the lookback window. Strategy satisfied = monitoring is up to date.

### `strategy:kdigo-sglt2-inhibitor`

SGLT2 inhibitor therapy. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:empagliflozin` (RxNorm 1545653)
- `med:dapagliflozin` (RxNorm 1488564)

Strategy satisfied when the patient has an active prescription for either SGLT2 inhibitor.

### `strategy:kdigo-statin-moderate-ckd`

Moderate-intensity statin for CKD. `INCLUDES_ACTION` edges (`intent: primary_prevention`, `intensity: moderate`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:atorvastatin` (RxNorm 83367)
- `med:rosuvastatin` (RxNorm 301542)
- `med:simvastatin` (RxNorm 36567)
- `med:pravastatin` (RxNorm 42463)
- `med:lovastatin` (RxNorm 6472)
- `med:fluvastatin` (RxNorm 41127)
- `med:pitavastatin` (RxNorm 861634)

Same shared statin entities as USPSTF and ACC/AHA. The `intensity: moderate` attribute on the INCLUDES_ACTION edges distinguishes this from ACC/AHA's high-intensity strategy. This is the anchor point for F26's `MODIFIES` edges.

### `strategy:kdigo-acei-arb`

ACEi or ARB therapy. `INCLUDES_ACTION` edges (`intent: treatment`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:lisinopril` (RxNorm 29046)
- `med:enalapril` (RxNorm 3827)
- `med:ramipril` (RxNorm 35296)
- `med:losartan` (RxNorm 52175)
- `med:valsartan` (RxNorm 69749)
- `med:irbesartan` (RxNorm 83818)

Strategy satisfied when the patient has an active prescription for any ACEi or ARB.

## Clinical entity nodes

### Conditions (new in F24)

| Node id | codings | Notes |
|---|---|---|
| `cond:chronic-kidney-disease` | SNOMED:709044004, ICD10:N18, N18.1-N18.5, N18.9 | Covers all CKD stages. Staging is predicate-based, not per-stage nodes. |

### Observations (new in F24)

| Node id | loinc_codes | Unit | Notes |
|---|---|---|---|
| `obs:egfr` | 48642-3, 62238-1, 88293-6 | mL/min/1.73m2 | CKD-EPI 2021 preferred; older eGFR formulas also match. |
| `obs:urine-acr` | 9318-7, 14959-1 | mg/g | Albumin-to-creatinine ratio. Conversion from mg/mmol not in v1 scope. |

### Medications (new in F24)

| Node id | rxnorm_codes | Class | Notes |
|---|---|---|---|
| `med:empagliflozin` | 1545653 | SGLT2 inhibitor | EMPA-KIDNEY trial evidence. |
| `med:dapagliflozin` | 1488564 | SGLT2 inhibitor | DAPA-CKD trial evidence. |
| `med:lisinopril` | 29046 | ACE inhibitor | Most prescribed ACEi in the US. |
| `med:enalapril` | 3827 | ACE inhibitor | SOLVD trial heritage. |
| `med:ramipril` | 35296 | ACE inhibitor | HOPE trial evidence. |
| `med:losartan` | 52175 | ARB | RENAAL trial evidence. |
| `med:valsartan` | 69749 | ARB | Val-HeFT evidence. |
| `med:irbesartan` | 83818 | ARB | IDNT trial evidence for diabetic nephropathy. |

## Patient-path summary (for the 3 v1 fixtures)

| Case | eGFR | ACR | Key features | Expected Recs |
|---|---|---|---|---|
| 01 | 52 (G3a) | 22 (A1) | 63M, no diabetes | R1 (monitoring), R3 (statin) |
| 02 | 38 (G3b) | 520 (A3) | 68M, T2DM | R1 + R2 + R3 + R4 (all four) |
| 03 | 22 (G4) | 85 (A2) | 71M, T2DM + HTN | R1 + R2 + R3 + R4 (all four) |

## Deferred for post-v1

- Cross-guideline `MODIFIES` edges to USPSTF/ACC-AHA statin Recs (F26).
- Deep diabetes-specific KDIGO recommendations beyond generic SGLT2 for CKD + T2DM.
- Dialysis-specific recommendations (G5D).
- Kidney transplant recommendations.
- Pediatric CKD.
- Acute kidney injury.
- CKD-MBD (mineral and bone disorder).
- Dose-adjusted medication tables.
- Heatmap risk category reporting.
- Temporal eGFR confirmation (two measurements ≥3 months apart).

## Guideline prose (for eval harness Arm B chunking) {#prose}

### Overview {#prose-overview}

The Kidney Disease: Improving Global Outcomes (KDIGO) 2024 guideline provides a comprehensive framework for the evaluation and management of chronic kidney disease. CKD is defined as abnormalities of kidney structure or function, present for more than 3 months, with implications for health. CKD is classified based on Cause (C), GFR category (G1-G5), and Albuminuria category (A1-A3), known as the CGA classification.

### CKD evaluation and staging {#prose-staging}

CKD should be diagnosed based on eGFR and albuminuria assessment. eGFR should be calculated using the CKD-EPI 2021 creatinine equation, which does not include a race variable. CKD is confirmed when eGFR <60 mL/min/1.73m2 or markers of kidney damage (most commonly albuminuria, defined as ACR ≥30 mg/g) are present for ≥3 months.

eGFR categories: G1 (≥90, normal), G2 (60-89, mildly decreased), G3a (45-59, mildly to moderately decreased), G3b (30-44, moderately to severely decreased), G4 (15-29, severely decreased), G5 (<15, kidney failure).

Albuminuria categories: A1 (<30 mg/g, normal to mildly increased), A2 (30-300 mg/g, moderately increased), A3 (>300 mg/g, severely increased).

Patients with CKD should have eGFR and urine ACR monitored at least annually, with monitoring frequency increasing with disease severity.

### SGLT2 inhibitors for CKD {#prose-sglt2}

KDIGO recommends SGLT2 inhibitors (empagliflozin, dapagliflozin) for patients with CKD who have type 2 diabetes and eGFR ≥20 mL/min/1.73m2, OR who have significantly increased albuminuria (ACR ≥200 mg/g) regardless of diabetes status. This is a Grade 1A recommendation (strong, high-quality evidence).

The evidence base includes CREDENCE (canagliflozin), DAPA-CKD (dapagliflozin), and EMPA-KIDNEY (empagliflozin), which demonstrated significant reduction in kidney disease progression and cardiovascular events. Benefits extend beyond glycemic control and include direct kidney-protective effects through tubuloglomerular feedback modulation.

SGLT2 inhibitors should not be initiated when eGFR is <20 mL/min/1.73m2. However, once initiated, they may be continued below this threshold unless not tolerated or renal replacement therapy starts. An initial eGFR decline of 10-30% is expected and reversible upon discontinuation; clinicians should not stop the medication solely based on this initial dip.

### Statin therapy in CKD {#prose-statin}

KDIGO recommends statin therapy for adults aged ≥50 with CKD (eGFR <60) who are not treated with chronic dialysis or kidney transplantation. This is a Grade 1A recommendation. The SHARP trial (Study of Heart and Renal Protection) demonstrated that simvastatin plus ezetimibe reduced major atherosclerotic events in patients with CKD.

Importantly, KDIGO specifically recommends moderate-intensity statin therapy in patients with CKD G3a-G5, rather than high-intensity. This is because statin pharmacokinetics are altered in advanced CKD (reduced clearance, higher plasma levels at equivalent doses), leading to an increased risk of myopathy with high-intensity regimens. In patients with CKD who are already on a statin initiated before CKD diagnosis, the intensity should be adjusted to moderate.

This recommendation is the primary anchor for cross-guideline modification in F26: when USPSTF or ACC/AHA guidelines would recommend high-intensity statin therapy, the KDIGO CKD recommendation modifies it to moderate-intensity for patients with CKD.

### RAS blockade for albuminuric CKD {#prose-ras-blockade}

KDIGO recommends an ACE inhibitor (ACEi) or angiotensin receptor blocker (ARB) for adults with CKD and moderately to severely increased albuminuria (ACR ≥30 mg/g, categories A2-A3). This is a Grade 1B recommendation. The recommendation is strongest for patients with ACR ≥300 mg/g (A3) and for those with coexisting diabetes or hypertension.

Key principles: use either an ACEi or an ARB, not both (dual RAS blockade increases hyperkalemia and AKI risk without additional benefit per ONTARGET and VA NEPHRON-D trials). Titrate to the maximally tolerated dose of the chosen agent. Monitor serum potassium and creatinine within 2-4 weeks of initiation or dose increase. An acute GFR decline of up to 30% after starting RAS blockade is acceptable and does not warrant discontinuation; a decline >30% should prompt investigation.

Multiple landmark trials support this recommendation: RENAAL (losartan in diabetic nephropathy), IDNT (irbesartan in diabetic nephropathy), AASK (ramipril in African Americans with hypertensive nephrosclerosis).

### Exclusions from this model {#prose-exclusions}

The following KDIGO CKD recommendations are NOT modeled in v1:

**Dialysis-specific recommendations:** Patients on dialysis (G5D) have distinct pharmacological considerations, including altered statin benefit (AURORA, 4D trials showed no benefit of statins in hemodialysis) and different RAS blockade management.

**Kidney transplant recipients:** Managed under transplant-specific immunosuppression protocols that interact with statin and ACEi/ARB recommendations.

**Pediatric CKD:** Different eGFR formulas, growth considerations, and age-appropriate medication dosing.

**Acute kidney injury:** AKI management follows a separate pathway; CKD recommendations assume stable chronic disease.

**CKD-MBD:** Mineral and bone disorder management (phosphate binders, vitamin D, PTH targets) is a distinct KDIGO guideline.

## Related

- `docs/specs/schema.md`
- `docs/specs/predicate-dsl.md`
- `docs/contracts/predicate-catalog.yaml`
- `docs/specs/eval-trace.md`
- `evals/fixtures/kdigo/` — 3 patient fixtures and expected outcomes.
