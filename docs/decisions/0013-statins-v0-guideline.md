# 0013. Statins (USPSTF 2022 primary prevention) replaces CRC as v0 guideline

Status: Accepted
Date: 2026-04-15
Supersedes: 0006

## Context

ADR 0006 picked CRC screening as the single v0 domain. After the schema, predicate DSL, patient-context spec, and 8 CRC eval fixtures were built, we reassessed. Three things pulled toward a different domain:

1. **Nothing in v0 exercised medications.** The `Medication` node type and RxNorm code list exist in the schema but are entirely dormant. A v0 that doesn't touch meds leaves a meaningful schema surface unvalidated.
2. **Nothing in v0 exercised computed risk scores.** Guidelines that predicate eligibility on a calculated score (ASCVD, CHA2DS2-VASc, FRAX) are a large share of real-world preventive care. CRC has no analog.
3. **The demo product is the eval trace UI.** CRC traces are mostly "age gate → strategy satisfaction check." A guideline whose trace decomposes a risk calculation step-by-step produces a more compelling visual and a better stress test of the trace contract.

## Decision

v0 models **USPSTF Statin Use for Primary Prevention of Cardiovascular Disease (2022)** as the sole active guideline. Grade B for adults 40–75 with ≥1 CVD risk factor and 10-year ASCVD risk ≥10%. Grade C for the same group at 7.5–10% risk. Grade I for adults ≥76. Out-of-scope exits for pre-existing ASCVD, LDL ≥190 (familial hypercholesterolemia pathway), and age <40.

The CRC work (ADR 0006 contents, `docs/reference/crc-model.archived.md`, 8 eval fixtures at `evals/archive/crc/`) is preserved as reference, not deleted. It re-enters scope when v0 ships.

## Why statins specifically

- **Single-body, single-document source.** USPSTF 2022 is one recommendation statement with three outcome bands. No cross-guideline merge in v0.
- **Cleanly exercises `Medication` nodes.** Moderate-intensity statin therapy is a class-level action with ~7 specific agents. One `Strategy` aggregates interchangeable `INCLUDES_ACTION` edges to individual `Medication` nodes. Tests the "class as a strategy, members as actions" pattern.
- **Forces a real computed-score predicate.** Pooled Cohort Equations for 10-year ASCVD risk require age, sex, race (Black vs. non-Black per the published equations), total cholesterol, HDL, SBP, on-treatment flag, smoking status, diabetes status. The evaluator has to call a named calculator, get a numeric, and compare to a threshold. That capability generalizes to every future risk score.
- **Crisp age gates produce a readable trace.** Three age branches (<40, 40–75, ≥76) with distinct outcomes make the stepper UI demo well.
- **Five patients cover the spread.** Grade B, Grade C, under-age exit, Grade I (≥76), and existing-CVD exclusion. Each patient traverses a distinct path.

## What statins does *not* exercise (and why that's acceptable)

- **Combined strategies (conjunction of actions).** Statin recs are single-action. CRC's flex-sig q5y + FIT q1y exercised conjunction; statins does not. The schema still supports conjunction via `INCLUDES_ACTION` semantics — it's just not stressed. Acceptable because CRC proved the pattern; we're not removing it from the schema.
- **Cascade (`TRIGGERS_FOLLOWUP`).** Statin primary prevention has no positive-test-triggers-followup analog. Deferred.
- **Cross-guideline preemption (`PREEMPTED_BY`).** With a single guideline, there's nothing to preempt to. Exclusions (pre-existing ASCVD, LDL ≥190) are modeled as out-of-scope exits in the trace, not preemptions to another guideline. The `PREEMPTED_BY` edge type stays in the schema for later; it's unused in v0.

## Alternatives considered

- **ADA T2DM pharmacotherapy.** Richer meds logic, comorbidity-driven branching, strong exercise of conjunctive strategies. Rejected for v0: scoping an annually-revised, sprawling guideline adds work not on the critical path. Revisit for v0.5 once the trace contract and UI are proven.
- **AFib anticoagulation (CHA2DS2-VASc).** Scoring-system decomposition would make the trace UI visually excellent. Rejected for v0: smaller patient-context surface than statins, thinner test of `PatientContext` breadth. Strong candidate for v0.5.
- **Continue CRC with added aspirin chemoprevention.** Rejected: USPSTF 2022 aspirin update narrowed and complicated the rec; grafting it onto CRC muddles scope without adding a clean meds exercise.

## Consequences

- `RxNorm` code system re-enters active use (dormant under CRC-only).
- New predicate `risk_score_compares` (already in catalog) becomes the first implemented risk-score predicate. Evaluator gains an `ascvd_10yr` calculator.
- Patient-context fields `observations.cholesterol`, `observations.blood_pressure`, `social_history.tobacco`, `demographics.ancestry` (for ASCVD race input), `medications` (for on-treatment-BP flag) all get real use.
- Pregnancy top-level record (ADR 0008) stays dormant in v0. No change.
- `evals/archive/crc/` is read-only reference. CRC re-activation is a post-v0 decision.

## Related

- `docs/reference/statin-model.md` — concrete model of nodes, edges, predicates.
- `docs/decisions/0014-v0-scope-and-structure.md` — companion ADR covering the repo restructure and language choice.
- USPSTF. *Statin Use for the Primary Prevention of Cardiovascular Disease in Adults: Preventive Medication.* 2022. https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/statin-use-in-adults-preventive-medication
