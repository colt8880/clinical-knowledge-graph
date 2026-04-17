# Statin model (v0)

Concrete instantiation of the USPSTF 2022 statin primary-prevention recommendation in the v0 knowledge graph. Pairs with the abstract spec in `docs/specs/schema.md` and is the source content for `/graph/seeds/statins.cypher`.

**Source:** USPSTF. *Statin Use for the Primary Prevention of Cardiovascular Disease in Adults: Preventive Medication.* Final recommendation, 2022-08-23. https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication

## Guideline node

| Attr | Value |
|---|---|
| id | `guideline:uspstf-statin-2022` |
| publisher | US Preventive Services Task Force |
| version | 2022-08-23 |
| effective_date | 2022-08-23 |
| url | https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication |
| status | active |

## Recommendations

Three Recommendation nodes plus three out-of-scope exits. The three recs correspond to the three outcome bands in the USPSTF statement:

### R1 — Initiate statin (Grade B, age 40–75, ≥1 risk factor, ASCVD ≥10%)

| Attr | Value |
|---|---|
| id | `rec:statin-initiate-grade-b` |
| title | Initiate statin for primary prevention of CVD (Grade B) |
| evidence_grade | B |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Recommendation Summary, Grade B |
| clinical_nuance | "Shared decision making about the potential benefits, harms, patient preferences, and costs of statin therapy is recommended. Risk may be under- or over-estimated by the Pooled Cohort Equations in populations they were not derived from." |

Structured eligibility:

```yaml
all_of:
  - age_between: { min: 40, max: 75 }
    # Top age cap 75 inclusive. ≥76 falls to R3.
  - none_of:
      # Exclusions — patients with these conditions exit to different pathways.
      - has_condition_history: { codes: [cond:ascvd-established] }
      - most_recent_observation_value:
          code: obs:ldl-cholesterol
          window: P2Y
          comparator: gte
          threshold: 190
          unit: mg/dL
      - has_condition_history: { codes: [cond:familial-hypercholesterolemia] }
  - any_of:
      # ≥1 CVD risk factor
      - has_active_condition: { codes: [cond:dyslipidemia] }
      - has_active_condition: { codes: [cond:diabetes] }
      - has_active_condition: { codes: [cond:hypertension] }
      - smoking_status_is:
          values: [current, current_some_day, current_every_day]
  - risk_score_compares:
      name: ascvd_10yr
      comparator: gte
      threshold: 10
```

Offered strategy: `strategy:statin-moderate-intensity`.

### R2 — Selectively offer statin (Grade C, age 40–75, ≥1 risk factor, ASCVD 7.5–<10%)

| Attr | Value |
|---|---|
| id | `rec:statin-selective-grade-c` |
| title | Selectively offer statin based on shared decision-making (Grade C) |
| evidence_grade | C |
| intent | shared_decision |
| trigger | patient_state |
| source_section | Recommendation Summary, Grade C |
| clinical_nuance | "Smaller net benefit in this group. The decision to initiate should be based on individual circumstances including patient preference, values, comorbid conditions, life expectancy, and risk factor profile." |

Structured eligibility: same as R1 except `risk_score_compares` is `value_between 7.5 and 10` (inclusive lower, exclusive upper).

Offered strategy: `strategy:statin-shared-decision-discussion` (Procedure-backed counseling), with `strategy:statin-moderate-intensity` as an alternative if the shared decision resolves to initiate.

### R3 — Insufficient evidence (Grade I, age ≥76)

| Attr | Value |
|---|---|
| id | `rec:statin-insufficient-evidence-grade-i` |
| title | Insufficient evidence to recommend for or against initiating statins (Grade I, ≥76) |
| evidence_grade | I |
| intent | primary_prevention |
| trigger | patient_state |
| source_section | Recommendation Summary, Grade I |
| clinical_nuance | "Current evidence is insufficient to assess the balance of benefits and harms of initiating a statin for the primary prevention of CVD events and mortality in adults ≥76." |

Structured eligibility:

```yaml
all_of:
  - age_greater_than_or_equal: { value: 76 }
  - none_of:
      - has_condition_history: { codes: [cond:ascvd-established] }
```

No offered strategies (Grade I emits `status: insufficient_evidence`).

### Out-of-scope exits (not Recommendation nodes)

Patients hitting the following conditions should produce an `exit_condition_triggered` trace event rather than being emitted as a recommendation:

| Exit token | Trigger | Rationale (surfaced in trace) |
|---|---|---|
| `out_of_scope_age_below_range` | age < 40 and no ASCVD | USPSTF statin primary prevention does not address adults under 40. |
| `out_of_scope_secondary_prevention` | `cond:ascvd-established` active | Established ASCVD is secondary prevention — addressed by ACC/AHA cholesterol guideline, not this USPSTF statement. |
| `out_of_scope_familial_hypercholesterolemia` | LDL ≥190 mg/dL or `cond:familial-hypercholesterolemia` | Severe primary hypercholesterolemia falls outside the Pooled Cohort Equation calibration range and has its own management pathway. |

These exits are produced by short-circuiting eligibility evaluation at R1 before running the full predicate tree. The evaluator detects any hit among these three conditions during the initial patient-state scan and emits the exit event in place of attempting R1/R2/R3.

## Strategies

### `strategy:statin-moderate-intensity`

Class-level action strategy. Satisfied when the patient has any active medication in the moderate-intensity statin set.

`INCLUDES_ACTION` edges (one per acceptable member, `intent: primary_prevention`, `cadence: null`, `lookback: null`, `priority: routine`):
- `med:atorvastatin` (RxNorm 83367)
- `med:rosuvastatin` (RxNorm 301542)
- `med:simvastatin` (RxNorm 36567)
- `med:pravastatin` (RxNorm 42463)
- `med:lovastatin` (RxNorm 6472)
- `med:fluvastatin` (RxNorm 41127)
- `med:pitavastatin` (RxNorm 861634)

v0 does **not** model intensity by dose. Any active statin satisfies the strategy. The `clinical_nuance` on R1 reminds the reviewer that moderate intensity is the recommended starting point; dose-level modeling is deferred.

### `strategy:statin-shared-decision-discussion`

Satisfied when a shared decision-making encounter is documented. One `INCLUDES_ACTION` edge (`intent: shared_decision`, `cadence: P1Y`, `lookback: P1Y`, `priority: routine`) pointing at:
- `proc:sdm-statin-discussion` — a Procedure node coded with SNOMED `710925007` ("Shared decision making") with context specific to statin therapy.

In practice, a patient in the Grade C band who has had the SDM encounter and is not currently on a statin is reported as "up to date on shared decision" with the decision captured. A patient who elected to initiate is then also evaluated against `strategy:statin-moderate-intensity` — which is offered as an alternative satisfier of R2. Modeling decision: v0 emits R2 as `due` when neither strategy is satisfied; the Grade B Rec does not override R2 for the 7.5–<10% band.

## Clinical entity nodes

### Conditions

| Node id | snomed_codes | icd10_codes | Notes |
|---|---|---|---|
| `cond:ascvd-established` | 394659003 (Acute ischaemic heart disease), 429559004 (Typical angina), 230690007 (Cerebrovascular accident), 22298006 (Myocardial infarction), 52404001 (PAD) | I20–I25, I63, I73.9, I70.2 | Single semantic concept covering established atherosclerotic CVD. |
| `cond:diabetes` | 73211009 | E10, E11 | Type 1 or Type 2. |
| `cond:hypertension` | 38341003 | I10 | Essential hypertension. |
| `cond:dyslipidemia` | 370992007 | E78.5, E78.2, E78.0 | Dyslipidemia / mixed hyperlipidemia. Distinct from familial. |
| `cond:familial-hypercholesterolemia` | 398036000 | E78.01 | Monogenic severe hypercholesterolemia. |

### Observations

| Node id | loinc_codes | Notes |
|---|---|---|
| `obs:total-cholesterol` | 2093-3 | mg/dL. |
| `obs:hdl-cholesterol` | 2085-9 | mg/dL. |
| `obs:ldl-cholesterol` | 2089-1, 13457-7 | Direct and calculated. mg/dL. |
| `obs:blood-pressure` | 85354-9 | Panel with component codes 8480-6 (SBP) and 8462-4 (DBP), mm[Hg]. |

### Medications

| Node id | rxnorm_codes | Notes |
|---|---|---|
| `med:atorvastatin` | 83367 (ingredient) | Include SCD/SBD children as needed for EHR matching. |
| `med:rosuvastatin` | 301542 | |
| `med:simvastatin` | 36567 | |
| `med:pravastatin` | 42463 | |
| `med:lovastatin` | 6472 | |
| `med:fluvastatin` | 41127 | |
| `med:pitavastatin` | 861634 | |
| `med:antihypertensive-class` | 41127 (placeholder), and class-level RxNorm TTY=IN for ACE-I, ARB, BB, CCB, thiazide, etc. | **Used only for the ASCVD on-treatment BP input, not as a statin strategy action.** See seeds/statins.cypher for the full code list. |

### Procedures

| Node id | snomed_codes | cpt_codes | Notes |
|---|---|---|---|
| `proc:sdm-statin-discussion` | 710925007 | 99401–99404 (preventive counseling) | Used by `strategy:statin-shared-decision-discussion`. |

## ASCVD Pooled Cohort Equations

The evaluator implements the 2013 ACC/AHA Pooled Cohort Equations (Goff et al.) to compute 10-year ASCVD risk when not supplied. Inputs (all from `PatientContext`):

| Input | Source | Missing-data behavior |
|---|---|---|
| age | derived from `date_of_birth` + `evaluation_time` | required |
| sex | `patient.administrative_sex` | required |
| race (Black vs. non-Black) | `patient.ancestry`; presence of `"black"` token | absent → non-Black default, trace notes imputation |
| total cholesterol (mg/dL) | `most_recent_observation_value(obs:total-cholesterol, P2Y)` | absent → score_unavailable |
| HDL cholesterol (mg/dL) | `most_recent_observation_value(obs:hdl-cholesterol, P2Y)` | absent → score_unavailable |
| systolic BP (mm Hg) | `most_recent_observation_value(obs:blood-pressure component 8480-6, P2Y)` | absent → score_unavailable |
| on BP treatment | `has_medication_active([med:antihypertensive-class])` | absent → false |
| diabetes | `has_active_condition([cond:diabetes])` | absent → false |
| current smoker | `smoking_status_is([current, current_some_day, current_every_day])` | absent → false |

Equations: Goff DC Jr, Lloyd-Jones DM, Bennett G, et al. *2013 ACC/AHA Guideline on the Assessment of Cardiovascular Risk.* Circulation. 2014;129(25 Suppl 2):S49–S73. The evaluator's implementation is a direct port of the published coefficients; it does not modify the equations. `method_version` in trace events is `pooled_cohort_equations_2013_goff`.

## Patient-path summary (for the 5 v0 fixtures)

| Case | Expected terminal event | Path through the model |
|---|---|---|
| 01-high-risk-55m | `recommendation_emitted(rec:statin-initiate-grade-b, due)` | R1 eligibility true; ASCVD ≥ 10%; no active statin → Grade B, initiate. |
| 02-borderline-55f-sdm | `recommendation_emitted(rec:statin-selective-grade-c, due)` | R1 fails at risk threshold; R2 eligibility true; ASCVD 7.5–<10% → Grade C, SDM. |
| 03-too-young-35m | `exit_condition_triggered(out_of_scope_age_below_range)` | Age gate exits before predicate tree fully evaluates. |
| 04-grade-i-78f | `recommendation_emitted(rec:statin-insufficient-evidence-grade-i, insufficient_evidence)` | Age ≥76; no established ASCVD; R3 eligible. |
| 05-prior-mi-62m | `exit_condition_triggered(out_of_scope_secondary_prevention)` | `cond:ascvd-established` active → secondary prevention exit. |

## Deferred for post-v0

- Intensity-aware statin modeling (high-intensity vs. moderate-intensity by agent + dose).
- Statin intolerance / bile acid sequestrant / ezetimibe alternatives (ACC/AHA cholesterol guideline territory).
- Primary prevention in diabetes per ADA Standards of Care (preempts USPSTF when both apply).
- Serum creatinine / eGFR as an ASCVD refinement (not in the 2013 PCE).

## Guideline prose (for eval harness Arm B chunking) {#prose}

The following sections render the USPSTF 2022 statin recommendation as continuous prose suitable for text chunking and retrieval. Each section has a stable anchor for chunk boundary alignment.

### Overview {#prose-overview}

The US Preventive Services Task Force (USPSTF) recommends that clinicians prescribe a statin for the primary prevention of cardiovascular disease (CVD) for adults aged 40 to 75 years who have one or more cardiovascular risk factors (dyslipidemia, diabetes, hypertension, or smoking) and an estimated 10-year risk of a cardiovascular event of 10% or greater. This is a Grade B recommendation, meaning there is high certainty of moderate net benefit or moderate certainty of moderate to substantial net benefit.

### Grade B recommendation: Statin initiation for high-risk adults {#prose-grade-b}

Adults aged 40 to 75 years who have at least one cardiovascular risk factor and a calculated 10-year ASCVD risk of 10% or greater should be started on moderate-intensity statin therapy for primary prevention of cardiovascular disease. Cardiovascular risk factors include dyslipidemia (elevated LDL cholesterol, low HDL cholesterol, elevated triglycerides), diabetes mellitus (type 1 or type 2), hypertension (including treated hypertension), and current tobacco smoking.

The 10-year ASCVD risk is calculated using the Pooled Cohort Equations (Goff et al., 2013), which incorporate age, sex, race (Black vs. non-Black), total cholesterol, HDL cholesterol, systolic blood pressure, blood pressure treatment status, diabetes status, and current smoking status. A 10-year risk of 10% or greater places the patient in the Grade B recommendation band.

Moderate-intensity statin therapy includes atorvastatin 10-20 mg, rosuvastatin 5-10 mg, simvastatin 20-40 mg, pravastatin 40 mg, lovastatin 40 mg, fluvastatin 80 mg, or pitavastatin 2-4 mg daily. The USPSTF does not recommend a specific agent within the moderate-intensity class; any of these agents is acceptable.

### Grade C recommendation: Selective statin offer for borderline-risk adults {#prose-grade-c}

For adults aged 40 to 75 years who have at least one cardiovascular risk factor and a calculated 10-year ASCVD risk of 7.5% to less than 10%, the USPSTF recommends that clinicians selectively offer a statin. This is a Grade C recommendation, meaning there is at least moderate certainty of a small net benefit.

The decision to initiate statin therapy in this group should be an individual one, based on shared decision-making between the patient and clinician. The discussion should consider the potential benefits (modest reduction in cardiovascular events), potential harms (muscle symptoms, slightly increased diabetes risk), patient preferences and values, comorbid conditions, life expectancy, and the overall cardiovascular risk factor profile.

If the shared decision-making discussion results in a decision to initiate therapy, moderate-intensity statin therapy is recommended. A documented shared decision-making encounter satisfies the recommendation's counseling strategy.

### Grade I statement: Insufficient evidence for adults 76 and older {#prose-grade-i}

For adults aged 76 years and older, the USPSTF concludes that the current evidence is insufficient to assess the balance of benefits and harms of initiating a statin for the primary prevention of CVD events and mortality. This is a Grade I statement.

This does not mean that statins are contraindicated in older adults. Rather, the evidence base for initiating statin therapy specifically for primary prevention in this age group is limited. Clinicians should use clinical judgment and consider individual patient circumstances, including existing cardiovascular risk, life expectancy, and patient preferences, when discussing statin therapy with adults 76 and older.

Adults already taking a statin before age 76 should not automatically discontinue therapy upon reaching that age. The Grade I statement applies specifically to new initiation, not continuation of existing therapy.

### Exclusions from this recommendation {#prose-exclusions}

The USPSTF statin primary prevention recommendation does not apply to the following populations, who are managed under separate clinical pathways:

**Established atherosclerotic cardiovascular disease (secondary prevention):** Patients with a history of myocardial infarction, stroke, peripheral arterial disease, or other established ASCVD are managed under secondary prevention guidelines (ACC/AHA 2018 Cholesterol). These patients typically require high-intensity statin therapy and have different LDL targets.

**Familial hypercholesterolemia:** Patients with LDL cholesterol >= 190 mg/dL or a diagnosis of familial hypercholesterolemia fall outside the Pooled Cohort Equation calibration range. They require specialized lipid management and are not addressed by this USPSTF recommendation.

**Adults under age 40:** The USPSTF does not make a recommendation about statin use for primary prevention in adults younger than 40. Risk assessment tools like the Pooled Cohort Equations are not validated below age 40.

### ASCVD risk calculation {#prose-ascvd}

The 10-year atherosclerotic cardiovascular disease risk is estimated using the 2013 Pooled Cohort Equations (Goff et al.). Required inputs are: age, sex, race (Black vs. non-Black), total cholesterol (mg/dL), HDL cholesterol (mg/dL), systolic blood pressure (mmHg), blood pressure treatment status, diabetes status, and current smoking status.

The equations may overestimate risk in some populations and underestimate it in others, particularly in populations not well-represented in the derivation cohorts. The USPSTF acknowledges this limitation and recommends that clinicians discuss the potential for mis-estimation with patients.

If a pre-computed ASCVD score is available from the electronic health record, it may be used directly. If not, the score should be calculated from the most recent available clinical data.

## Related

- `docs/specs/schema.md`
- `docs/specs/predicate-dsl.md`
- `docs/contracts/predicate-catalog.yaml`
- `docs/specs/eval-trace.md`
- `evals/fixtures/statins/` — 5 patient fixtures and golden traces.
