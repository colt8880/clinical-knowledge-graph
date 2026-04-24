# 57: Serialization scoping — filter context to relevant guidelines

**Status**: pending
**Depends on**: 56
**Components touched**: evals / api / docs
**Branch**: `feat/serialization-scoping`

## Context

F55 showed that adding ADA Diabetes as the 4th guideline regressed Arm C scores on existing cross-domain fixtures that don't involve diabetes. The root cause: the `/evaluate` endpoint runs all 4 guidelines for every patient, and the serialization includes all guideline results in the Arm C context — even guidelines that produced zero applicable recommendations. A non-diabetic patient gets ADA evaluation prose, negative evidence sections, and convergence noise in their context, diluting the signal from the 2-3 guidelines that actually matter.

The data from F55:
- Existing cross-domain fixtures (cases 01-10) Arm C mean dropped from 4.275 (Phase 1) to ~3.84 (Phase 2). Four of seven available cases regressed.
- Completeness gap (C - B) flipped from +0.500 to -0.013.
- Prioritization gap flipped from +0.600 to -0.475.

The evaluator already knows which guidelines fired (via `guideline_entered` / `recommendation_emitted` / `exit_condition_triggered` events). The serialization just needs to filter based on relevance before building the prompt.

## Required reading

- `evals/harness/serialization.py` — `build_arm_c_context()` and all serialize_* functions
- `evals/harness/arms/graph_context.py` — Arm C prompt template
- `evals/results/v2-phase2/scorecard.json` — per-fixture scores showing regression
- `evals/results/v2-phase2/README.md` — regression analysis
- `docs/ISSUES.md` — "F55 serialization scaling with 4+ guidelines" entry

## Scope

- `evals/harness/serialization.py` — Add a filtering pass to `build_arm_c_context()` that classifies each guideline as "relevant" or "irrelevant" based on the trace events, then excludes irrelevant guidelines from the serialized context.
- `evals/harness/arms/graph_context.py` — No prompt template changes. The scoping happens upstream in serialization.
- `evals/results/v2-phase2-r3/` — NEW directory: re-run with scoped serialization.
  - `scorecard.md`
  - `scorecard.json`
  - `README.md` — comparison to F56 re-run (complete data baseline) and F51 (Phase 1 baseline). Regression check on existing fixtures. Thesis gate assessment.
- `docs/reference/build-status.md` — update row for F57.

## Design

### Relevance classification

A guideline is **relevant** to a patient if any of these are true in the trace:

1. At least one `recommendation_emitted` event with `status` != `not_applicable` exists for the guideline.
2. At least one `exit_condition_triggered` event exists — the guideline was evaluated and the exit is clinically meaningful (e.g., "secondary prevention detected").
3. The guideline has a `cross_guideline_match` event involving it as source or target.

A guideline is **irrelevant** if it was entered, all its recs were `not_applicable` (no exit, no emission, no cross-match), and it contributes nothing to the patient's context.

### What gets filtered

For irrelevant guidelines, exclude from serialization:
- Their entries in `rendered_prose` (the guideline_entered + recommendation prose lines)
- Their matched_recs from the recs list
- Their nodes/edges from the subgraph
- Their contribution to convergence (if any — unlikely since irrelevant guidelines don't fire recs)
- Their entry in negative_evidence (this is the key cut — "ADA 2024 Diabetes: No eligible recommendations" is noise for a non-diabetic patient)

### What is preserved

- All cross-guideline interaction events involving the guideline (preemption, modifier) — even if the guideline itself is irrelevant, the interaction context may matter.
- The guideline's contribution to satisfied_strategies — if a patient happens to be on a medication that satisfies an ADA strategy, that's relevant.

## Constraints

- **Do not modify the evaluator API.** The `/evaluate` endpoint continues to run all guidelines. The filtering happens in the serialization layer only (harness-side, not API-side).
- **No rubric changes, no judge model changes.**
- **Same fixtures, same arm model.** The only variable is the serialization filtering.
- **Deterministic.** Same trace + same filtering rules = same serialized context. No heuristics or LLM-in-the-loop for relevance classification.
- **The re-run must use F56's retry logic.** Expect 0 missing entries.

## Verification targets

- Unit test: given a trace with 4 guidelines where 2 are irrelevant, `build_arm_c_context()` produces a context that mentions only the 2 relevant guidelines.
- Unit test: a guideline with an exit_condition_triggered but no recommendation_emitted is classified as relevant (the exit is clinically meaningful).
- Unit test: a guideline involved in a cross_guideline_match is never filtered out.
- `cd evals && uv run python -m harness --all --run v2-phase2-r3` completes with 0 missing entries.
- Scorecard shows N=16 for all arms on multi-guideline subset.
- Regression check: existing 10 cross-domain fixtures' Arm C scores should recover toward Phase 1 levels (F51). Target: mean Arm C composite on cases 01-10 >= 4.0 (was 4.275 in Phase 1, dropped to ~3.84 in Phase 2).
- README includes Phase 1 vs Phase 2 vs Phase 2-r3 comparison table.
- Thesis gate assessment stated.

## Definition of done

- Serialization scoping implemented with unit tests.
- Full harness re-run completed with complete data.
- Scorecard committed to `evals/results/v2-phase2-r3/`.
- README documents regression recovery and thesis gate status.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Modifying the evaluator API to support per-patient guideline filtering.
- Changing the Arm C prompt template or output format instructions.
- Tiered summarization / token budgeting for large contexts (that's F58).
- Rubric changes or judge model changes.
