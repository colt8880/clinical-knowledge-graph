# 46: Serialization v2 thesis run

**Status**: pending
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
| Arm C Completeness | 3.50 | ? | ? | ? |
| Arm C composite (all) | 4.14 | ? | ? | ? |
| Arm A composite (all) | 2.98 | ? | ? | ? (prompt helps all arms) |

Key question: **Did the serialization and prompt changes improve Completeness?** Target: Arm C Completeness ≥ 4.0 (up from 3.50). Secondary: did the exhaustiveness prompt help all arms equally, or did Arm C benefit disproportionately?

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-serial` completes with no errors.
- Scorecard generated and committed with comparison table.

## Definition of done

- Harness run completed. Scorecard committed. Serialization impact documented.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- New fixtures. Rubric changes. Combined run (F47).
