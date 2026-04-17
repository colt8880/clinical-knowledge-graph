# 21: Multi-guideline evaluator + trace extension

**Status**: pending
**Depends on**: 20
**Components touched**: api / docs / evals
**Branch**: `feat/multi-guideline-evaluator`

## Context

Today the evaluator traverses a single guideline. v1 requires it to walk the full forest of guidelines in scope and emit a unified `EvalTrace` with per-event provenance. This feature implements forest traversal and extends the trace event vocabulary, but does not implement preemption resolution or modifier-edge handling (those land in F25 and F26). Think of this as structural plumbing: multi-guideline in, unified trace out, no new semantics yet.

## Required reading

- `docs/build/v1-spec.md` — v1 macro spec; the three-arm thesis depends on this trace being usable as Arm C context.
- `docs/specs/eval-trace.md` — current trace spec; will be amended.
- `docs/contracts/eval-trace.schema.json` — source of truth for trace shape; extend in the same commit.
- `api/app/evaluator/*` — current evaluator; structure to extend.
- `evals/fixtures/statins/` — regression target.
- `docs/build/20-shared-clinical-entity-layer.md` — the labeling scheme this feature assumes is in place.

## Scope

- `api/app/evaluator/traversal.py` (or current equivalent) — add forest entry point that walks every `:Guideline` node in deterministic order.
- `api/app/evaluator/trace.py` — extend event model with `guideline_id` on every event; add new event types.
- `docs/specs/eval-trace.md` — document new event types and the `guideline_id` field; update example trace.
- `docs/contracts/eval-trace.schema.json` — add `guideline_id` (required) and new event type enum values.
- `api/app/routes/evaluate.py` — response shape includes per-guideline rec list plus unified trace.
- `docs/contracts/api.openapi.yaml` — reflect new response shape.
- `api/tests/test_evaluator_multi_guideline.py` — new; constructs a two-guideline fixture (mock second guideline, not ACC/AHA yet) and asserts forest traversal order and trace shape.
- `evals/harness/` — no changes yet; F22 builds on top.

## Constraints

- **Deterministic traversal order:** guidelines visited in ascending lexical order of `guideline_id`. Document this in `docs/specs/eval-trace.md` so it's contract, not implementation detail.
- **New event types added:**
  - `guideline_entered` — emitted at the start of each guideline's traversal. Carries `guideline_id`, `version`.
  - `guideline_exited` — emitted at end.
  - `cross_guideline_match` — placeholder type for F25/F26; schema reserves it but evaluator does not emit in this feature.
  - `preemption_resolved` — same; reserved for F25.
- **`guideline_id` required on every event.** For existing single-guideline event types, the field is set from the enclosing guideline context.
- **Determinism invariant:** re-running any fixture produces a byte-identical trace. This holds today for single-guideline and must hold after the refactor for single-guideline fixtures. Multi-guideline determinism is tested with a synthetic two-guideline fixture in this feature since ACC/AHA content doesn't land until F23.
- **Backwards compat on trace shape:** the `guideline_id` field is additive. Consumers that ignore unknown fields still parse v0-style traces. v0 fixtures must have their `expected-trace.json` golden files updated in this feature to include `guideline_id` (mechanical update, not a semantic change).
- **No preemption logic.** If two guidelines' Recs both match, both are emitted in the trace. Resolution is F25.
- **No `MODIFIES` handling.** Reserved for F26.
- **Trace event ordering within a guideline:** unchanged from v0.

## Verification targets

- `cd api && uv run pytest api/tests/test_evaluator_multi_guideline.py` — exits 0.
- All 5 v0 statin fixtures produce traces where every event carries `guideline_id = "uspstf-statin-primary-prevention-2022"`.
- Running an evaluator against a synthetic two-guideline graph emits `guideline_entered` events in lexical guideline-id order.
- `docs/contracts/eval-trace.schema.json` validates against all 5 updated v0 goldens.
- Re-running any fixture twice produces byte-identical trace output (checked in test).

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- v0 expected-trace goldens updated mechanically (new `guideline_id` field added to every event); diff reviewed in PR.
- Contract and spec updated in the same commit as the implementation.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Preemption resolution logic (F25).
- `MODIFIES` edge handling (F26).
- Authoring ACC/AHA or KDIGO content (F23, F24).
- Eval harness (F22) — this feature just produces the trace; F22 consumes it.
- UI changes (F29).

## Design notes (not blocking, worth review)

- **Synthetic second guideline for the test:** build a minimal `TESTGUIDE-A` seed that lives under `api/tests/fixtures/` (not `graph/seeds/`) so the test graph is self-contained and doesn't pollute the real database. This avoids a chicken-and-egg with F23.
- **Per-guideline rec lists vs. flat list:** evaluator emits both. The flat list is for API consumers; the per-guideline breakdown is for the UI. Both derived from the same trace; no duplicated state.
- **What about the `guideline_id` on shared entity references?** Shared entities don't have a guideline_id. Events that reference them (e.g., `ACTION_SATISFIED` on a `Medication`) still carry the `guideline_id` of the Rec being evaluated, not the entity. Document this in the spec.
