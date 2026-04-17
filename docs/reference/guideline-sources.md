# Guideline Sources

Running log of guidelines modeled into the graph. Append-only; supersession is tracked via `SUPERSEDES` edges in the graph itself.

## Format

- `guideline_id` — stable internal id (e.g., `uspstf-statin-2022`)
- `publisher`
- `title`
- `version` / `effective_date`
- `url`
- `ingestion_date`
- `reviewer` — clinician who signed off
- `notes`

## Entries

### v0 corpus (statin primary prevention)

#### `uspstf-statin-2022`

- **Publisher:** US Preventive Services Task Force
- **Title:** Statin Use for the Primary Prevention of Cardiovascular Disease in Adults: US Preventive Services Task Force Recommendation Statement
- **Version / effective date:** 2022 / 2022-08-23
- **URL:** https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication
- **Ingestion date:** TBD (v0 modeling in progress; hand-authored, not LLM-drafted)
- **Reviewer:** TBD
- **Notes:**
  - Scope is primary prevention only. Established ASCVD is out of scope and triggers `out_of_scope_secondary_prevention`.
  - Grades: B (age 40-75, ≥1 risk factor, ASCVD ≥10%), C (age 40-75, ≥1 risk factor, ASCVD 7.5 to <10% — selectively, via shared decision-making), I (age ≥76, insufficient evidence).
  - Age < 40: entire guideline does not apply. Evaluator exits via `out_of_scope_age_below_range`.
  - Risk factors that count: dyslipidemia (LDL > 130 or TC > 200), diabetes, hypertension, or current smoking.
  - ASCVD 10-year risk is computed via the Pooled Cohort Equations (Goff et al. 2013). v0 evaluator reads `risk_scores.ascvd_10yr` from the supplied patient context; live PCE calculation is deferred.
  - Strategy: any moderate-intensity statin (modeled at the RxNorm class level: atorvastatin, rosuvastatin, simvastatin, pravastatin, lovastatin, fluvastatin, pitavastatin). Intensity dose ranges captured in clinical nuance; not enforced as a predicate in v0 (no dose predicates yet).
  - Grade C also offers an explicit shared-decision-making Procedure-backed strategy.
  - See `docs/reference/guidelines/statins.md` for the concrete nodes, edges, and code mappings.

### v1 corpus (multi-guideline)

#### `acc-aha-cholesterol-2018`

- **Publisher:** American Heart Association / American College of Cardiology
- **Title:** 2018 AHA/ACC/AACVPR/AAPA/ABC/ACPM/ADA/AGS/APhA/ASPC/NLA/PCNA Guideline on the Management of Blood Cholesterol
- **Version / effective date:** 2018 / 2018-11-10
- **URL:** https://doi.org/10.1161/CIR.0000000000000625
- **Ingestion date:** 2026-04-17 (hand-authored)
- **Reviewer:** TBD
- **Notes:**
  - Scope: four statin benefit groups only. Not the full guideline.
  - Benefit groups modeled: (1) secondary prevention (clinical ASCVD, ≤75), (2) severe hypercholesterolemia (LDL ≥190), (3) diabetes age 40-75, (4) primary prevention age 40-75 with LDL 70-189 and risk ≥7.5%.
  - Evidence grades use COR/LOE system (e.g., "COR I, LOE A").
  - Introduces high-intensity vs. moderate-intensity statin strategies with `intensity` property on `INCLUDES_ACTION` edges.
  - Reuses shared clinical entities from `clinical-entities.cypher` (same statin medications as USPSTF v0).
  - No cross-guideline edges to USPSTF in this feature; those land in F25.
  - Adults >75, ezetimibe, PCSK9 inhibitors, non-statin lipid therapies deferred to v2.
  - See `docs/reference/guidelines/cholesterol.md` for concrete nodes, edges, and code mappings.

#### `kdigo-ckd-2024`

- **Publisher:** Kidney Disease: Improving Global Outcomes (KDIGO)
- **Title:** KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease
- **Version / effective date:** 2024 / 2024-03-14
- **URL:** https://doi.org/10.1016/j.kint.2023.10.018
- **Ingestion date:** 2026-04-17 (hand-authored)
- **Reviewer:** TBD
- **Notes:**
  - Scope: four CKD management decision points. Not the full guideline.
  - Decision points modeled: (1) CKD monitoring (eGFR + ACR), (2) SGLT2 inhibitor for CKD with T2DM or significant albuminuria, (3) statin for CKD age ≥50 not on dialysis, (4) ACEi/ARB for albuminuric CKD.
  - Evidence grades use the GRADE system (e.g., "1A" = strong recommendation, high evidence).
  - CKD staging modeled as derived predicates over eGFR and ACR observations, not as synthesized Condition nodes.
  - eGFR < 20 contraindication for SGLT2 initiation encoded in eligibility predicate.
  - Statin-for-CKD Rec is the primary modifier anchor for F26 (KDIGO recommends moderate-intensity in CKD G3-G5).
  - New shared entities: eGFR observation, urine ACR observation, CKD condition, SGLT2 inhibitors (empagliflozin, dapagliflozin), ACEi (lisinopril, enalapril, ramipril), ARBs (losartan, valsartan, irbesartan).
  - No cross-guideline edges to USPSTF or ACC/AHA in this feature; those land in F26.
  - Dialysis-specific, transplant, pediatric, AKI, and CKD-MBD recommendations deferred to v2.
  - See `docs/reference/guidelines/kdigo-ckd.md` for concrete nodes, edges, and code mappings.

### Archived

- `uspstf-crc-2021`, `acp-crc-2019` — see `docs/archive/` for notes. Superseded by ADR 0013.

### Planned (post-v1)

- [ ] ADA Standards of Care (diabetes) — next candidate to exercise medication management + risk factor overlap with statins.
- [ ] USPSTF aspirin primary prevention (2022) — overlaps the same ASCVD risk machinery; good test for predicate reuse.

## Out of scope for v0

Anything outside USPSTF 2022 statin primary prevention. Do not add until the statin slice has end-to-end evals passing.
