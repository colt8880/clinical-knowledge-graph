# 47: v2 Phase 1 combined thesis run

**Status**: pending
**Depends on**: 42, 44, 46, 48
**Components touched**: evals / docs
**Branch**: `feat/v2-phase1-combined-run`

## Context

The capstone feature of v2 Phase 1. All Phase 1 improvements — validated cross-guideline edges (F41), stronger Arm B retrieval (F43), and improved Arm C serialization + prompt (F45) — have been individually measured in isolation runs (F42, F44, F46). This run measures their combined effect and produces the definitive v2 Phase 1 scorecard.

By this point, the isolation runs (F42, F44, F46) have answered each question individually. This run answers: **do the improvements compound, or do they interfere?** The combined effect could be greater than the sum (synergy) or less (e.g., better RAG + better serialization compete for the same points).

## Required reading

- `docs/build/v2-spec.md` — v2 success criteria
- `docs/decisions/0020-three-arm-eval-methodology.md` — methodology (margin, self-consistency)
- `evals/results/v1-thesis/scorecard.md` — v1 baseline to compare against
- `evals/rubric.md` — scoring rubric (unchanged from v1.1)

## Scope

- `evals/results/v2-phase1/` — NEW directory. Commits scorecard artifacts:
  - `scorecard.md` — human-readable results
  - `scorecard.json` — machine-readable results
  - `README.md` — prose summary with v1 → v2 comparison
- `docs/reference/build-status.md` — update.

## Fixture set

Same 16 fixtures as v1. No new fixtures in Phase 1 — isolate the variable to edge/retrieval/serialization changes.

| Subset | Fixtures | Count |
|--------|----------|-------|
| Single-guideline (statins) | 5 | 5 |
| Single-guideline (cholesterol) | 4 | 4 |
| Single-guideline (KDIGO) | 3 | 3 |
| Multi-guideline (cross-domain) | 4 | 4 |
| **Total** | | **16** |

## Constraints

- **Rubric unchanged.** Same v1.1 rubric, same judge model, same arm model. Only the arm context (retrieval quality, serialization, edges) changes.
- **No fixture changes.** If F41 updated expected-actions.json for cross-domain fixtures (due to preemption changing which recs fire), use the updated fixtures. But don't add or remove fixtures.
- **1 trial** for the primary run (self-consistency already validated in v1 at SD ≤ 0.044).
- **Braintrust experiments:** `v2-phase1-arm-a`, `v2-phase1-arm-b`, `v2-phase1-arm-c`.

## Analysis

The scorecard README must include a full comparison table across all runs:

| Metric | v1 | F42 (edges) | F44 (RAG) | F46 (serial.) | F47 (combined) |
|--------|-----|-------------|-----------|---------------|----------------|
| Arm C composite (all) | 4.14 | ? | ? | ? | ? |
| Arm B composite (all) | 3.38 | ? | ? | ? | ? |
| C - B gap (multi-gl) | +1.00 | ? | ? | ? | ? |
| Arm C Completeness | 3.50 | ? | ? | ? | ? |
| Arm C Integration (multi-gl) | 4.75 | ? | ? | ? | ? |

Key question: **do the improvements compound or interfere?**

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-phase1` completes with no errors.
- Braintrust shows 3 experiments with 16 entries each.
- `cd evals && uv run python -m harness --scorecard --run v2-phase1` produces scorecard.
- Scorecard includes v1 → v2 comparison table.
- Scorecard explicitly states whether the C - B gap held, improved, or regressed.

## Definition of done

- Full harness run completed.
- Scorecard committed to `evals/results/v2-phase1/`.
- Full comparison table (v1 + all isolation runs + combined) in README.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Adding ADA Diabetes (Phase 2).
- New fixtures beyond the existing 16.
- Rubric changes.
- Cross-vendor arm validation (running with GPT-4 etc.).
