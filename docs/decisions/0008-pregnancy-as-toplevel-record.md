# 0008. Pregnancy as a top-level structured record

Status: Accepted, deferred in v0 (see 0014)
Date: 2026-04-14

**Deferred in v0.** Statin guideline (ADR 0013) does not touch the pregnancy record. Field stays in the schema but is not exercised in v0. Re-activates when a guideline that reads it (e.g., cervical screening, perinatal depression) enters scope.

## Context

v0 modeled pregnancy as a coded Observation (LOINC 82810-3 or similar) so "currently pregnant" would time-box like any other clinical finding. The USPSTF v1 coverage pass surfaced a problem: the perinatal block (HepB, HIV, syphilis screening in pregnancy; Rh(D) initial and 24–28 week repeat; GDM at ≥24 weeks; aspirin for preeclampsia at 12 weeks; bacteriuria; IPV; breastfeeding; perinatal depression; healthy weight; tobacco cessation in pregnancy) needs gestational age, EDD, parity, gravidity, lactation, and postpartum end-date together in a coherent record. Reconstructing those from scattered Observations is fragile, inconsistent across adapters, and hard to review.

## Decision

Pregnancy is a top-level structured record on `PatientContext` (`pregnancy: PregnancySummary`) representing the current pregnancy only. Historical pregnancies remain in `conditions` (e.g., prior gestational diabetes, prior preeclampsia) and `observations`. The summary is adapter-computed; the evaluator does not derive it.

## Alternatives considered

- **Keep pregnancy as an Observation only.** Rejected: the field shape works for "is the patient pregnant today" but fails for the GA + EDD + parity joint logic.
- **Pregnancy as a Condition with extensions.** Rejected: FHIR-valid but pushes the complexity into extension definitions that adapters implement inconsistently.
- **Observation for pregnancy status + a parallel Observation for gestational age.** Rejected: two-Observation AND logic across the contract is exactly the failure mode we saw with v0 tobacco before promoting that to a structured record too.

## Consequences

- This is a departure from strict FHIR shape. The adapter projects FHIR Condition + related Observations into the summary record; the departure is documented in the spec.
- Predicates `is_pregnant`, `gestational_age_between`, `postpartum_within`, `parity_greater_than_or_equal`, `gravidity_greater_than_or_equal`, and `lactation_status_is` read from this record.
- Reversal requires rewriting those predicates and the pregnancy sub-schema; it does not require changing other patient-context resources.

## Related

- `docs/specs/patient-context.md` (§ pregnancy)
- `docs/specs/predicate-dsl.md` (§ Pregnancy and perinatal)
- ADR 0002
