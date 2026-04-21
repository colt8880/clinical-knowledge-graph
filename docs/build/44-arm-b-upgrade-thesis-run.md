# 44: Arm B upgrade thesis run

**Status**: pending
**Depends on**: 43
**Components touched**: evals / docs
**Branch**: `feat/arm-b-upgrade-thesis-run`

## Context

After upgrading Arm B to section-level chunking + multi-query retrieval (F43), this run measures the impact in isolation. The graph still has clinician-validated edges (from F41), but Arm C serialization is unchanged from v1. The only variable vs F42 is Arm B's retrieval quality.

This answers: **how much of Arm C's advantage was due to Arm B being weak?**

## Required reading

- `evals/results/v2-edges/scorecard.md` — F42 baseline (edges added, old RAG)
- `evals/results/v1-thesis/scorecard.md` — v1 baseline

## Scope

- `evals/results/v2-arm-b/` — NEW directory.
  - `scorecard.md`, `scorecard.json`, `README.md`

## Constraints

- Same 16 fixtures, same rubric v1.1, same models, 1 trial.
- Arm C serialization unchanged from v1. Only Arm B retrieval changed.
- Braintrust experiments: `v2-arm-b-arm-a`, `v2-arm-b-arm-b`, `v2-arm-b-arm-c`.

## Analysis

| Metric | v1 (naive RAG) | F42 (edges only) | F44 (better RAG) | Delta (F44 vs F42) |
|--------|----------------|-------------------|--------------------|--------------------|
| Arm B composite (all) | 3.38 | ? | ? | ? |
| C - B gap (multi-gl) | +1.00 | ? | ? | ? |

Key question: **Did the improved Arm B close the gap with Arm C?** If the C - B gap shrinks significantly (e.g., from +1.00 to +0.3), the v1 advantage was partly weak RAG. If it holds (still ≥ 0.5), the structural advantage is real even against production-quality retrieval.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-arm-b` completes with no errors.
- Scorecard generated and committed with comparison table.

## Definition of done

- Harness run completed. Scorecard committed. Arm B impact documented.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Serialization changes (F45). Rubric changes. New fixtures.
