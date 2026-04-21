# 46: Serialization v2 thesis run

**Status**: in-progress
**Depends on**: 45
**Components touched**: evals / docs
**Branch**: `feat/serialization-thesis-run`

## Context

After upgrading Arm C serialization to grouped convergence + intensity context + exhaustiveness prompt (F45), this run measures the impact. The graph has edges (F41), Arm B has upgraded retrieval (F43). The only variable vs F44 is the serialization and prompt changes.

This answers: **does better serialization improve Completeness scores?**

## Required reading

- `evals/results/v2-arm-b/scorecard.md` — F44 baseline (edges + better RAG, old serialization)
- `evals/results/v1-thesis/scorecard.md` — v1 baseline

## Scope

- `evals/results/v2-serialization/` — NEW directory.
  - `scorecard.md`, `scorecard.json`, `README.md`

## Constraints

- Same 16 fixtures, same rubric v1.1, same models, 1 trial.
- Note: the system prompt change (exhaustiveness instruction) affects all arms equally, so Arm A and Arm B may also improve. This is intentional and should be documented.
- Braintrust experiments: `v2-serial-arm-a`, `v2-serial-arm-b`, `v2-serial-arm-c`.

## Analysis

| Metric | v1 | F44 (edges + RAG) | F46 (+ serialization) | Delta (F46 vs F44) |
|--------|-----|--------------------|-----------------------|--------------------|
| Arm C Completeness (multi-gl) | 3.75 | 3.50 | 3.40 | -0.10 |
| Arm C composite (multi-gl) | 4.31 | 3.65 | 3.78 | +0.13 |
| Arm B composite (multi-gl) | 3.72 | 3.45 | 3.65 | +0.20 |
| C - B gap (multi-gl) | +0.59 | +0.20 | +0.13 | -0.08 |
| Arm A composite (multi-gl) | 3.22 | 2.73 | 2.70 | -0.03 |

**Answer:** Serialization v2 did NOT improve Completeness (3.40, missed the 4.0 target). The exhaustiveness prompt helped Arm B (+0.20) more than Arm C (+0.13), narrowing the gap further. Integration was the one dimension that improved (+0.1 → +0.4 gap). See `evals/results/v2-serialization/README.md` for full analysis.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-serial` completes with no errors.
- Scorecard generated and committed with comparison table.

## Definition of done

- Harness run completed. Scorecard committed. Serialization impact documented.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- New fixtures. Rubric changes. Combined run (F47).
