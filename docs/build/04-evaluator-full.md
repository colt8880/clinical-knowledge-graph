# 04: Evaluator full (all predicates, all fixtures)

**Status**: pending
**Depends on**: 03
**Branch**: `feat/evaluator-full`

## Context

Feature 03Mer proved the evaluator pipeline on one fixture with one predicate. This feature fills in every remaining predicate needed by the v0 statin model and asserts all 5 fixtures produce their golden traces. After this ships, the evaluator is feature-complete for v0.

## Required reading

- Everything from 03's required reading.
- `evals/SPEC.md` — runner contract.
- `evals/fixtures/statins/README.md` — fixture inventory.
- `evals/fixtures/statins/01-*/`, `02-*/`, `04-*/`, `05-*/` — the remaining fixtures.

## Scope

- `api/app/evaluator/predicates/` — one module per predicate family:
  - `age.py` (extend from 03)
  - `conditions.py` — `has_condition_history`, `has_active_condition`
  - `observations.py` — `most_recent_observation_value`, with window + comparator
  - `medications.py` — `has_medication_active`
  - `smoking.py` — `smoking_status_is`
  - `risk_score.py` — `risk_score_compares` (lookup-only; no PCE calc)
  - `composites.py` — `all_of`, `any_of`, `none_of` evaluation with three-valued logic
- `api/app/evaluator/exits.py` — exit-condition scan (age-below, secondary prevention, FH/LDL≥190).
- `api/app/evaluator/engine.py` — extend to run R1/R2/R3 eligibility, strategy satisfaction, emit `recommendation_emitted`.
- `api/tests/test_evaluator_fixtures.py` — parametrized over all 5 fixtures, golden trace byte-match.
- `api/tests/test_predicates/` — unit tests per predicate family with three-valued logic coverage.
- `evals/runner.py` (or `scripts/run_evals.py`) — CLI that runs the full fixture suite and prints pass/fail.

## Constraints

- Same determinism constraints as feature 03.
- `most_recent_observation_value` tiebreaker when two observations share `effective_date`: lexicographic by `id` (per `docs/ISSUES.md`). Comment the decision in code.
- Unit normalization (`mm[Hg]` ↔ `mmHg`, `mg/dL` casing) happens in the observation predicate, not the adapter.
- No dose-level statin logic (v0 scope).
- Don't introduce new predicates not in `predicate-catalog.yaml`. If one is missing, amend the catalog + spec in a separate PR first.

## Verification targets

- `cd api && pytest` — all tests pass, including all 5 golden-trace fixtures.
- `python evals/runner.py` (or equivalent) — all 5 fixtures pass.
- Each fixture's terminal event matches the row in `docs/reference/guidelines/statins.md#patient-path-summary`.
- Re-running produces identical bytes (determinism check).

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Live ASCVD / Pooled Cohort Equations calculation (deferred; see `docs/ISSUES.md`).
- Cascade / `TRIGGERS_FOLLOWUP` / `expects` semantics.
- Cross-guideline preemption.
- UI — feature 06.
- Performance benchmarking.
