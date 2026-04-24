# 55: v2 Phase 2 thesis run

**Status**: shipped
**Depends on**: 54
**Components touched**: evals / docs
**Branch**: `feat/v2-phase2-thesis-run`

## Context

Phase 2 added ADA Diabetes as a 4th guideline (F52), connected it via clinician-reviewed cross-guideline edges (F53), and created 6 multi-morbidity fixtures exercising 3-4 guidelines simultaneously (F54). This run measures the combined effect on all 32 fixtures (22 existing + 4 new diabetes single-guideline + 6 new multi-morbidity).

The v2 Phase 1 thesis run (F51) passed with a C-B margin of +0.775 on 10 multi-guideline fixtures. Phase 2 tests whether:

1. The margin holds or improves when 6 harder multi-morbidity fixtures are added (16 multi-guideline total).
2. ADA's cardiorenal interactions (SGLT2i convergence with KDIGO, metformin/eGFR modification) produce measurably better recommendations than flat RAG.
3. The 4-guideline patient (case-12) — the hardest case in the harness — scores well on Integration.

## Required reading

- `evals/results/v2-f50/scorecard.md` — Phase 1 baseline (comparison point)
- `evals/results/v2-f50/scorecard.json` — per-fixture, per-arm, per-dimension scores
- `evals/rubric.md` — scoring rubric (unchanged)
- `docs/decisions/0020-three-arm-eval-methodology.md` — methodology

## Scope

- `evals/results/v2-phase2/` — NEW directory:
  - `scorecard.md` — human-readable results
  - `scorecard.json` — machine-readable results
  - `README.md` — prose summary with Phase 1 → Phase 2 comparison and multi-morbidity analysis
- `docs/reference/build-status.md` — update row for F55.

## Fixture set

| Subset | Count |
|--------|-------|
| Single-guideline (statins) | 5 |
| Single-guideline (cholesterol) | 4 |
| Single-guideline (KDIGO) | 3 |
| Single-guideline (diabetes) | 4 |
| Multi-guideline (existing cross-domain) | 10 |
| Multi-guideline (new multi-morbidity) | 6 |
| **Total** | **32** |

## Constraints

- **Rubric unchanged.** Same v1.1 rubric, same judge model (`claude-opus-4-20250514`), same arm model (`claude-sonnet-4-20250514`).
- **No fixture changes to existing cases.** Same 22 fixtures from F51, plus 6 new from F54.
- **1 trial** (self-consistency validated in prior runs at SD <= 0.044).
- **All 3 arms re-run** for a clean comparison across the full 32-fixture set.
- **Braintrust experiments:** `v2-phase2-arm-a`, `v2-phase2-arm-b`, `v2-phase2-arm-c`.

## Analysis

The scorecard README must include:

### 1. Phase 1 → Phase 2 comparison table

| Metric | Phase 1 (F51) | Phase 2 | Delta |
|--------|---------------|---------|-------|
| Arm C composite (all) | 4.148 | ? | ? |
| Arm C composite (multi-gl) | 4.275 | ? | ? |
| Arm B composite (multi-gl) | 3.500 | ? | ? |
| C - B gap (multi-gl) | +0.775 | ? | ? |
| C - B gap (multi-gl, existing 10 only) | +0.775 | ? | ? |
| C - B gap (multi-gl, new 6 only) | — | ? | — |
| Arm C Integration (multi-gl) | 4.200 | ? | ? |
| Arm C Completeness (multi-gl) | 3.900 | ? | ? |

### 2. Multi-morbidity fixture analysis

For the 6 new multi-morbidity fixtures (case-11 through case-16):

- Per-fixture Arm C composite and per-dimension scores.
- Call out case-12 (4-guideline patient) specifically — does Integration score >= 4?
- Identify any fixture where Arm B beats Arm C (these reveal where flat RAG's broader retrieval may capture ADA content that the graph's serialization misses).
- Compare diabetes-inclusive multi-guideline fixtures to the existing non-diabetes fixtures. Does the 4th guideline help or hurt?

### 3. Regression check

Compare the existing 10 cross-domain fixtures' Arm C scores between Phase 1 and Phase 2. Adding ADA to the graph should not regress scores on cases that don't involve diabetes. If it does, the serialization is introducing noise.

### 4. Thesis gate assessment

State whether the C-B margin holds >= 0.5 on the full 16-fixture multi-guideline set. Also report the margin on the 6 new multi-morbidity fixtures alone.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-phase2` completes with no errors.
- Braintrust shows 3 experiments with 32 entries each.
- `cd evals && uv run python -m harness --scorecard --run v2-phase2` produces scorecard.
- Scorecard includes Phase 1 → Phase 2 comparison table.
- Multi-morbidity fixture analysis for cases 11-16.
- Regression check on existing fixtures.
- Thesis gate assessment stated.

## Definition of done

- Full harness run completed (all 3 arms × 32 fixtures).
- Scorecard committed to `evals/results/v2-phase2/`.
- Comparison table, multi-morbidity analysis, regression check, and thesis gate in README.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Rubric changes, judge prompt changes, or judge model changes.
- New fixtures beyond F54's set.
- Arm prompt modifications based on results (that would be a separate feature).
- Cross-vendor validation (separate feature in Phase 3).
- Combined historical comparison across all runs (v1 through Phase 2).
