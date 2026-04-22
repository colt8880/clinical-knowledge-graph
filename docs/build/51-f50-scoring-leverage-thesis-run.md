# 51: F50 scoring leverage thesis run

**Status**: shipped
**Depends on**: 50
**Components touched**: evals / docs
**Branch**: `feat/f50-scoring-leverage-run`

## Context

F50 shipped three targeted changes to Arm C's serialization and prompt: negative evidence surfacing, extended cross-guideline output schema, and completeness licensing. These changes target Integration and Completeness — the two weakest dimensions in the v2-phase1 scorecard.

The v2-phase1 combined run (F47) showed:
- **C-B margin (multi-gl): +0.175** — far below the 0.5 threshold.
- **Completeness gap (multi-gl): -0.100** — Arm B actually scored higher.
- **Integration gap (multi-gl): +0.400** — strong but not enough to carry the composite.
- **Clinical Appropriateness gap (multi-gl): +0.500** — the bright spot.
- **Prioritization gap (multi-gl): -0.100** — slight Arm B advantage.

F49 (satisfied strategies + interaction reasoning) and F50 (negative evidence + completeness licensing + integration schema) were designed as back-to-back improvements. This run measures their combined effect against the F47 baseline.

F50's estimated margin improvement was +0.225 to +0.325, which would project the combined margin at +0.400 to +0.500. This run tests that projection.

## Required reading

- `evals/results/v2-phase1/scorecard.md` — F47 baseline (the comparison point)
- `evals/results/v2-phase1/scorecard.json` — per-fixture, per-arm, per-dimension scores
- `docs/build/49-arm-c-completeness-fixes.md` — F49 changes (already in the codebase)
- `docs/build/50-arm-c-scoring-leverage.md` — F50 changes (already in the codebase)
- `evals/rubric.md` — scoring rubric (unchanged at v1.1)
- `docs/decisions/0020-three-arm-eval-methodology.md` — methodology

## Scope

- `evals/results/v2-f50/` — NEW directory. Commits scorecard artifacts:
  - `scorecard.md` — human-readable results
  - `scorecard.json` — machine-readable results
  - `README.md` — prose summary with F47 → F50 comparison and dimension-level analysis
- `docs/reference/build-status.md` — update row for F51.

## Fixture set

Same 22 fixtures as F47. No changes.

| Subset | Count |
|--------|-------|
| Single-guideline (statins) | 5 |
| Single-guideline (cholesterol) | 4 |
| Single-guideline (KDIGO) | 3 |
| Multi-guideline (cross-domain) | 10 |
| **Total** | **22** |

## Constraints

- **Rubric unchanged.** Same v1.1 rubric, same judge model (`claude-opus-4-20250514`), same arm model (`claude-sonnet-4-20250514`). The only variable vs F47 is the Arm C serialization and prompt changes from F49 + F50.
- **No fixture changes.** Same 22 fixtures, same expected-actions.
- **1 trial** (self-consistency validated in v1 at SD ≤ 0.044).
- **Arm A and Arm B should also be re-run** for a clean comparison. F50 did not modify their prompts or context, but the completeness licensing instruction (#4) is in the Arm C template only — confirm no spillover.
- **Braintrust experiments:** `v2-f50-arm-a`, `v2-f50-arm-b`, `v2-f50-arm-c`.

## Analysis

The scorecard README must include:

### 1. Comparison table

| Metric | F47 (v2-phase1) | F51 (post-F49+F50) | Delta |
|--------|-----------------|---------------------|-------|
| Arm C composite (all) | 3.800 | ? | ? |
| Arm C composite (multi-gl) | 3.800 | ? | ? |
| Arm B composite (multi-gl) | 3.625 | ? | ? |
| C - B gap (multi-gl) | +0.175 | ? | ? |
| Arm C Completeness (multi-gl) | ? | ? | ? |
| Arm C Integration (multi-gl) | ? | ? | ? |
| Arm C Clinical Approp. (multi-gl) | ? | ? | ? |
| Arm C Prioritization (multi-gl) | ? | ? | ? |

### 2. Per-fixture delta analysis

For the 10 multi-guideline fixtures, show per-fixture Arm C composite change (F47 → F51). Call out:
- **Cases 04, 05, 06, 09, 10** — these had Integration ≤ 3 in F47. Did the extended output schema help?
- **Cases 09, 10** — negative evidence probes. Did surfacing what didn't fire improve scores?
- **Case 07, 09** — completeness licensing targets. Did the LLM add lifestyle/non-graph actions?

### 3. Thesis gate assessment

State whether the C-B margin crossed the 0.5 threshold. If not, identify the remaining gap and what dimension(s) are dragging.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-f50` completes with no errors.
- Braintrust shows 3 experiments with 22 entries each.
- `cd evals && uv run python -m harness --scorecard --run v2-f50` produces scorecard.
- Scorecard includes F47 → F51 comparison table.
- Per-fixture delta analysis for multi-guideline subset.
- Scorecard explicitly states whether C-B margin ≥ 0.5.

## Definition of done

- Full harness run completed (all 3 arms × 22 fixtures).
- Scorecard committed to `evals/results/v2-f50/`.
- Comparison table and per-fixture delta analysis in README.
- Thesis gate assessment stated.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Rubric changes, judge prompt changes, or judge model changes.
- New fixtures or expected-actions changes.
- Arm A or Arm B prompt modifications.
- Further Arm C prompt tuning based on results (that would be a separate feature).
- Combined historical comparison table across all runs (v1, F42, F44, F46, F47, F51) — keep it focused on F47 → F51 delta.
