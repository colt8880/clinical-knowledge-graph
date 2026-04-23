# 54: Multi-morbidity fixtures

**Status**: pending
**Depends on**: 53
**Components touched**: evals / docs
**Branch**: `feat/multi-morbidity-fixtures`

## Context

F52 added the ADA Diabetes subgraph and F53 connected it via cross-guideline edges. This feature creates the hardest test cases in the harness: patients with multiple chronic conditions whose care is governed by 3-4 guidelines simultaneously.

The existing 10 cross-domain fixtures exercise USPSTF ↔ ACC/AHA preemption and KDIGO → ACC/AHA modification, but none include diabetes. The v2 thesis — that the graph handles disagreement resolution on complex multi-morbidity patients — requires fixtures where ADA, KDIGO, ACC/AHA, and USPSTF all fire for the same patient.

These fixtures serve dual purpose: they measure whether adding ADA improves the graph's utility, and they stress-test the evaluator's ability to surface convergence, preemption, and modification across 4 guidelines simultaneously.

## Required reading

- `evals/SPEC.md` — fixture spec
- `evals/INVENTORY.md` — current fixture inventory
- `evals/fixtures/cross-domain/case-05/expected-actions.json` — reference expected-actions pattern for diabetic patient
- `docs/review/cross-edges-ada.md` — approved ADA cross-guideline edges (from F53)
- `docs/reference/guidelines/ada-diabetes.md` — ADA model

## Scope

### New files

- `evals/fixtures/cross-domain/case-11/` through `case-16/` — 6 new multi-morbidity fixtures (see Fixture set below).
- Each fixture: `patient-context.json`, `expected-actions.json`.

### Modified files

- `evals/fixtures/cross-domain/README.md` — add case-11 through case-16.
- `evals/INVENTORY.md` — add new cases to cross-domain section.
- `docs/reference/build-status.md` — update F54 row.

## Fixture set

| ID | Patient profile | Guidelines active | Primary interaction tested |
|----|----------------|-------------------|---------------------------|
| 11 | 55M, T2DM on metformin, A1C 7.2%, HTN, ASCVD 14%, eGFR 85, no CKD. | ADA + ACC/AHA + USPSTF | ADA statin convergence with ACC/AHA R3 (diabetes). ACC/AHA preempts USPSTF. ADA SGLT2i/GLP-1 RA not triggered (no ASCVD/HF/CKD). Simplest 3-guideline diabetes case. |
| 12 | 62F, T2DM on metformin, A1C 8.5%, established ASCVD (prior stroke), eGFR 48, ACR 180. | ADA + KDIGO + ACC/AHA + USPSTF | Full 4-guideline activation. ADA SGLT2i converges with KDIGO SGLT2i. KDIGO modifies ACC/AHA statin intensity. ADA GLP-1 RA for CVD. USPSTF preempted by ACC/AHA. The hardest case in the harness. |
| 13 | 68M, T2DM on metformin + empagliflozin, A1C 6.9%, CKD 3b (eGFR 35), ACR 320, HF, no ASCVD. | ADA + KDIGO | ADA SGLT2i already active (satisfied strategy). KDIGO monitoring + ACEi/ARB for albuminuria. KDIGO statin converges with ADA statin. Metformin at eGFR boundary (dose reduction territory). Tests satisfied-strategy handling across guidelines. |
| 14 | 50M, T2DM newly diagnosed, A1C 8.8%, HTN, ASCVD 18%, LDL 175, eGFR 72, no CKD. | ADA + ACC/AHA + USPSTF | ADA metformin + intensification (A1C > 7%). ACC/AHA high-intensity statin (diabetes + high risk). ADA SGLT2i for CVD benefit. USPSTF fully preempted. Tests high-risk diabetes with multiple guideline-concordant actions. |
| 15 | 72F, T2DM on metformin + glargine, A1C 7.8%, CKD 4 (eGFR 22), ACR 250, HF. | ADA + KDIGO | Metformin contraindicated (eGFR < 30) — expected action is discontinue. SGLT2i borderline (eGFR 20-25, can continue if already on, don't initiate). ADA intensification. KDIGO monitoring at high frequency. Tests the hardest eGFR boundary cases. |
| 16 | 48M, T2DM well-controlled, A1C 6.5%, no CVD, no CKD, eGFR 95, LDL 110, ASCVD 5.2%. | ADA + (USPSTF borderline) | ADA metformin continuation + moderate statin. Below ACC/AHA risk threshold. USPSTF Grade C (shared decision-making, ASCVD 7.5-10%) doesn't fire (5.2% < 7.5%). Tests correct non-activation of guidelines. The "boring" 4-guideline patient where most recs don't fire. |

## Constraints

- **No changes to guideline seeds or cross-edges.** Fixtures test the existing graph; they don't modify it.
- **No changes to evaluator code.** If a fixture reveals an evaluator bug, file it in ISSUES.md and note in the PR body.
- **Expected-actions are hand-curated.** Every action cites the source rec ID and explains which cross-guideline interaction (convergence, preemption, modification) applies.
- **Contraindications section required.** Each fixture must list actions that would be clinically wrong for this patient (e.g., high-intensity statin when KDIGO recommends moderate; continuing metformin at eGFR < 30).
- **Patient contexts are clinically realistic.** Lab values, medication lists, and condition combinations must be internally consistent. A patient on empagliflozin should have a plausible reason for it (CKD, HF, or diabetes).
- **ASCVD risk scores are supplied** (not computed), consistent with v1 convention.

## Verification targets

- All 6 fixtures have `patient-context.json` and `expected-actions.json`.
- Patient contexts validate against `patient-context.schema.json`.
- Expected-actions cite specific rec IDs from the graph for every graph-sourced action.
- `cd evals && uv run python -m harness --guideline cross-domain --arm c --run v2-ada-fixtures` runs without errors on all cross-domain fixtures (existing + new).
- Arm C scores completeness >= 3.0 on new fixtures (threshold lower than single-guideline because 4-guideline cases are genuinely harder).

## Definition of done

- All 6 fixtures committed with patient-context and expected-actions.
- INVENTORY.md and cross-domain README updated.
- Harness runs clean on all fixtures.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Changes to the evaluator, seeds, or cross-edges.
- Changes to the rubric or judge prompt.
- Thesis run (F55).
- Fixtures for ADA-specific edge cases (insulin titration, DPP-4i, etc.).
