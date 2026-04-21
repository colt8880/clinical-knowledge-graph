# 42: Edge-value thesis run

**Status**: pending
**Depends on**: 41
**Components touched**: evals / docs
**Branch**: `feat/edge-value-thesis-run`

## Context

After clinician-validated cross-guideline edges are re-added (F41), this run measures their incremental value in isolation. Same Arm B (naive RAG), same Arm C serialization as v1 — the only variable is the presence of PREEMPTED_BY and MODIFIES edges in the graph.

This is the cleanest possible test of whether curated conflict resolution adds value on top of convergence visibility.

## Required reading

- `evals/results/v1-thesis/scorecard.md` — v1 baseline (no edges)
- `docs/decisions/0020-three-arm-eval-methodology.md` — methodology

## Scope

- `evals/results/v2-edges/` — NEW directory.
  - `scorecard.md` — human-readable results
  - `scorecard.json` — machine-readable results
  - `README.md` — v1 → v2-edges comparison, answering: did edges improve Integration scores on multi-guideline fixtures?

## Constraints

- Same 16 fixtures, same rubric v1.1, same models, 1 trial.
- Arm B unchanged from v1. Arm C serialization unchanged from v1. Only the graph content (edges) changed.
- Braintrust experiments: `v2-edges-arm-a`, `v2-edges-arm-b`, `v2-edges-arm-c`.

## Analysis

The README must include:

| Metric | v1 (no edges) | v2-edges | Delta |
|--------|---------------|----------|-------|
| Arm C Integration (multi-gl) | 4.75 | ? | ? |
| Arm C composite (multi-gl) | 4.25 | ? | ? |
| C - B gap (multi-gl) | +1.00 | ? | ? |
| Arm B composite (unchanged) | 3.25 | ? | ~0 expected |

Key question: **Did edges improve Arm C's Integration score on multi-guideline fixtures?** If yes, curated reasoning adds measurable value. If no, convergence alone is sufficient and edges are documentation, not reasoning input.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-edges` completes with no errors.
- Scorecard generated and committed.
- v1 comparison table in README.

## Definition of done

- Harness run completed.
- Scorecard committed.
- Edge impact documented clearly.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Arm B retrieval changes (F43).
- Serialization changes (F45).
- Adding fixtures.
