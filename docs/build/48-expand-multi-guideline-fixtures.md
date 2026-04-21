# 48: Expand multi-guideline fixture set

**Status**: pending
**Depends on**: 42
**Components touched**: evals / docs
**Branch**: `feat/expand-multi-gl-fixtures`

## Context

The v2-edges thesis run (F42) exposed a statistical power problem: 4 multi-guideline fixtures, 1 trial, and one bad fixture swings the composite by ~0.3 points against a 0.5 threshold. Two of the four fixtures (case-02, case-04) showed identical C-B gaps across v1 and v2; the other two drove all the variance. Future thesis runs (F44, F46, F47) need a larger, more targeted sample to produce trustworthy margins.

Additionally, the existing fixtures only exercise 2 of the 8 approved edges: P4 (ACC/AHA primary prevention preempts USPSTF Grade C) and M1 (KDIGO modifies ACC/AHA secondary prevention intensity). Four edges (P1, P2, P5, P6) and M2 have no coverage at all.

This feature adds 6 new cross-domain fixtures — one per gap in edge coverage, plus one "bias probe" fixture where the correct clinical answer requires the LLM to *diverge* from a naive reading of the trace.

## Required reading

- `evals/SPEC.md` — fixture format, expected-actions schema
- `evals/fixtures/cross-domain/` — existing 4 fixtures (understand the pattern)
- `evals/results/v2-edges/README.md` — what went wrong with the current sample
- `docs/review/cross-edges.md` — all 8 approved edges and their clinical semantics
- `docs/reference/guidelines/statins.md` — USPSTF statin model
- `evals/rubric.md` — scoring rubric (Integration dimension definition)

## Scope

New fixture directories (each with `patient-context.json` and `expected-actions.json`):

- `evals/fixtures/cross-domain/case-05/` — **P1 + P2 (diabetes preemption).** Type 2 diabetic, 50M, ASCVD 12%. ACC/AHA diabetes-specific statin rec preempts both USPSTF Grade B and Grade C. Tests whether the LLM recognizes the more specific rec should take precedence.
- `evals/fixtures/cross-domain/case-06/` — **P3 (Grade B preemption).** 48F, LDL 155, ASCVD 11%, no diabetes. ACC/AHA primary prevention preempts USPSTF Grade B (not just Grade C like existing cases). Tests higher-risk end of the preemption spectrum.
- `evals/fixtures/cross-domain/case-07/` — **P5 + P6 (severe hypercholesterolemia preemption).** 45M, LDL 210, familial pattern. ACC/AHA severe hypercholesterolemia rec (high-intensity statin) preempts both USPSTF grades. Expected action must specify high-intensity, not moderate.
- `evals/fixtures/cross-domain/case-08/` — **M2 (KDIGO modifies severe hypercholesterolemia).** 60F, LDL 195, CKD G4 (eGFR 22). ACC/AHA severe hypercholesterolemia says high-intensity; KDIGO modifies to moderate due to advanced CKD pharmacokinetics. Exercises the second MODIFIES edge that case-03 doesn't reach.
- `evals/fixtures/cross-domain/case-09/` — **P4 + M1 combined (preemption + modification).** 58M, primary prevention, ASCVD 9%, CKD G3b (eGFR 38). ACC/AHA preempts USPSTF Grade C, then KDIGO modifies ACC/AHA intensity to moderate. Both edge types fire on the same patient. Tests whether the LLM can chain two interactions.
- `evals/fixtures/cross-domain/case-10/` — **Bias probe: trace-divergent correct answer.** 52F, ASCVD 6.8%, LDL 160, CKD G3a (eGFR 55), well-controlled on ACEi. The trace fires USPSTF Grade C + KDIGO CKD statin (convergence), but the clinically correct answer emphasizes shared decision-making (Grade C risk level) rather than definitive statin initiation. An LLM that parrots "initiate statin" from the trace should score lower on clinical_appropriateness than one that recognizes the nuance. Tests the bias concern from F42 analysis.

Modified files:

- `evals/INVENTORY.md` — add new fixture rows
- `evals/fixtures/cross-domain/README.md` — update fixture catalog
- `docs/reference/build-status.md` — F48 row

## Constraints

- Patient profiles must be clinically coherent (lab values, vitals, conditions consistent with each other and the target scenario).
- Expected actions must be hand-curated by human review, not derived from API traces. Each action's `rationale` must cite the specific guideline rec ID, evidence grade, and the edge interaction that resolves the conflict.
- Contraindications must be populated where an edge interaction means a specific action should NOT appear (e.g., high-intensity statin when KDIGO modifies to moderate).
- No changes to the harness, serialization, or evaluator. These are pure data additions.
- All fixtures must pass a sanity check: `cd evals && uv run python -m harness --arm c --fixture cross-domain/case-NN` completes without error.

## Verification targets

- 6 new fixture directories, each with `patient-context.json` and `expected-actions.json`.
- Each fixture passes JSON Schema validation against `docs/contracts/patient-context.schema.json`.
- Each fixture's expected-actions includes at least one contraindication where an edge interaction makes a specific action incorrect.
- `cd evals && uv run python -m harness --arm c --fixture cross-domain/case-05 --run fixture-sanity` through `case-10` all complete without error.
- INVENTORY.md updated with 6 new rows.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Human review of expected-actions for clinical correctness (the PM is the reviewer).
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output in the body.
- `pr-reviewer` subagent run; blocking feedback addressed; output posted as PR comment.

## Out of scope

- Running a thesis run with the expanded fixtures (that's F47).
- Modifying the rubric or threshold (document the power improvement, don't change the bar).
- Adding single-guideline fixtures.
- Modifying the harness, serialization, or evaluator code.
- Addressing the Arm C structural information advantage — that's a methodology concern for a future ADR, not a fixture concern.
