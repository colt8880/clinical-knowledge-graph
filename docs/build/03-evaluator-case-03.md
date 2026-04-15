# 03: Evaluator vertical slice (fixture 03)

**Status**: pending
**Depends on**: 02
**Branch**: `feat/evaluator-case-03`

## Context

Prove the trace-first evaluator end-to-end on the simplest fixture: case 03 (35-year-old, age-below-range exit). This slice exercises the full pipeline (patient context validation → predicate dispatch → exit emission → trace event stream) but only needs one predicate (`age_less_than` or equivalent age check) and the short-circuit exit path. Everything that works here will generalize; everything that breaks here will break every other case. Keeping scope to one fixture keeps the debug surface small.

## Required reading

- `api/CLAUDE.md`
- `docs/specs/eval-trace.md` — event shapes and ordering rules.
- `docs/specs/patient-context.md` — input shape and `require`-policy behavior.
- `docs/specs/predicate-dsl.md` — predicate dispatch, three-valued logic.
- `docs/contracts/eval-trace.schema.json` — authoritative trace event shape.
- `docs/contracts/patient-context.schema.json` — input validation.
- `docs/contracts/predicate-catalog.yaml` — predicate signatures.
- `docs/reference/statin-model.md` — the out-of-scope-age exit definition.
- `evals/statins/03-*/` — the fixture (patient context + golden trace).

## Scope

- `api/app/evaluator/__init__.py` — public `evaluate(patient_context, graph) -> EvalTrace`.
- `api/app/evaluator/trace.py` — `TraceEvent` models, monotonic `event_id` assignment.
- `api/app/evaluator/engine.py` — top-level orchestration: load guideline, run exit-scan, emit events.
- `api/app/evaluator/predicates/age.py` — age comparison predicates needed for fixture 03.
- `api/app/evaluator/predicates/registry.py` — dispatch table; stub entries for predicates not yet implemented (raise `NotImplementedError` with predicate name).
- `api/app/routes/evaluate.py` — `POST /evaluate` endpoint, returns `EvalTrace`.
- `api/tests/test_evaluator_case_03.py` — runs fixture 03, asserts golden trace byte-match.
- Update `api/app/main.py` to register the new route.

## Constraints

- Trace output is byte-deterministic: same input + same graph version + same evaluator version = same bytes. No timestamps in trace bodies; ordering is by monotonic `event_id`.
- `evaluator_version` in the trace header pulls from a single source (e.g., `api/app/__version__.py`).
- Golden trace comparison uses canonical JSON (sorted keys, stable number formatting).
- Predicate `missing_data` default is `unknown_is_false` (per `docs/ISSUES.md`); pin it in code with a comment citing the issue.
- No live ASCVD calculation. `risk_scores.ascvd_10yr` read directly when present.

## Verification targets

- `cd api && pytest tests/test_evaluator_case_03.py -v` — exits 0.
- `POST /evaluate` with fixture 03's patient context returns a trace terminating in `exit_condition_triggered(out_of_scope_age_below_range)`.
- The returned trace, canonically serialized, matches `evals/statins/03-*/expected_trace.json` byte-for-byte.
- Running the same request twice produces identical bytes.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md`: `Trace-first evaluator` moves to `scaffolded`, `Predicate engine (v0 subset)` notes "fixture 03 only".
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Predicates beyond the age check. Everything else stubs to `NotImplementedError`.
- Fixtures 01, 02, 04, 05 — those are feature 04.
- UI integration — that's feature 06.
- Performance tuning.
