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

### Archived

- `uspstf-crc-2021`, `acp-crc-2019` — see `docs/archive/` for notes. Superseded by ADR 0013.

### Planned (post-v0)

- [ ] ACC/AHA 2018/2019 cholesterol guideline — more granular than USPSTF; would test preemption semantics and introduce statin intensity categories.
- [ ] ADA Standards of Care (diabetes) — next candidate to exercise medication management + risk factor overlap with statins.
- [ ] USPSTF aspirin primary prevention (2022) — overlaps the same ASCVD risk machinery; good test for predicate reuse.

## Out of scope for v0

Anything outside USPSTF 2022 statin primary prevention. Do not add until the statin slice has end-to-end evals passing.
