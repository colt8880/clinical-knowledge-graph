# Eval Trace

**Status: v1 (F21).** The ordered, structured record of every step the evaluator takes while producing a recommendation set for a patient. This spec is the **primary contract** between the evaluator, the API, and the Eval UI. Contract source of truth: `docs/contracts/eval-trace.schema.json`.

## Why a trace is a first-class output

The knowledge graph exists because LLMs are nondeterministic. The evaluator is deterministic. The eval trace is how a reviewer confirms that claim: given the same `PatientContext` and the same graph version, the evaluator walks the same nodes, evaluates the same predicates with the same inputs, and emits the same events in the same order.

Concretely:
- The Eval UI is a stepper over the trace. There is no separate "debug" mode.
- Golden eval fixtures (`evals/fixtures/statins/<case>/expected-trace.json`) are full traces, not just final rec lists. Regression tests diff traces, not outputs.
- The "final recommendation set" is a derived view over `recommendation_emitted` events in the trace, not a separate API field.

If a design choice would trade trace fidelity for brevity, default to fidelity. A verbose trace is a feature.

## Top-level shape

```
{
  envelope: Envelope                // versions, evaluation_time, patient fingerprint
  events: Event[]                   // ordered, one step each
  recommendations: Recommendation[] // derived view; convenience for consumers (flat list)
  recommendations_by_guideline: {   // per-guideline breakdown; same data, keyed by guideline_id
    [guideline_id]: Recommendation[]
  }
}
```

The envelope is stamped once at the start and echoed in the API response. The `events` array is the trace proper. `recommendations` is a convenience derivation from `recommendation_emitted` events for consumers that don't want to walk the trace. `recommendations_by_guideline` groups the same data by guideline for the UI.

## Envelope

| Field | Type | Notes |
|---|---|---|
| `spec_tag` | string | git tag of the spec set used, e.g., `spec/v2-2026-04-15` |
| `graph_version` | string | identifier for the loaded Neo4j dataset |
| `evaluator_version` | string | identifier for the evaluator binary + predicate catalog |
| `evaluation_time` | ISO 8601 date-time | echoed from `PatientContext.evaluation_time` |
| `patient_fingerprint` | string | deterministic hash of the input `PatientContext` for reproducibility checks |
| `started_at` | ISO 8601 date-time | wall-clock at trace start (for latency only; not used in determinism check) |
| `completed_at` | ISO 8601 date-time | wall-clock at trace end |

Wall-clock times are excluded from `patient_fingerprint` and excluded from regression-test diffs by convention.

## Event model

Every event has:
- `seq` — monotonically increasing integer, starting at 1.
- `type` — one of the types below.
- `guideline_id` — the guideline being evaluated when this event was emitted. **Required on every event** (F21). Null for envelope-level events (`evaluation_started`, `evaluation_completed`) that sit outside any guideline bracket. For all other events, set from the enclosing guideline context. Events referencing shared clinical entities (e.g., `action_checked` on a `Medication`) carry the `guideline_id` of the Rec being evaluated, not the entity.
- `at` — optional wall-clock ISO 8601 date-time (informational, not part of determinism).
- Type-specific payload fields.

Events are ordered by `seq`. `seq` is the only index the UI stepper uses. A trace with gaps in `seq` is malformed.

### Event types

**Traversal events** — describe graph walking.

1. **`evaluation_started`** — always first. `guideline_id` is null.
   - `patient_age_years: int`
   - `patient_sex: string`
   - `guidelines_in_scope: string[]` (e.g., `["guideline:uspstf-statin-2022"]`)

2. **`guideline_entered`** — evaluator begins considering a specific guideline.
   - `guideline_id: string`
   - `guideline_title: string`

3. **`guideline_exited`** — evaluator finishes considering a specific guideline (F21).
   - `guideline_id: string`
   - `recommendations_emitted: int` (count of recs emitted for this guideline)

4. **`recommendation_considered`** — evaluator begins evaluating a specific Rec.
   - `recommendation_id: string`
   - `recommendation_title: string`
   - `evidence_grade: string`
   - `intent: string`
   - `trigger: string`

5. **`eligibility_evaluation_started`** — about to walk the `structured_eligibility` tree.
   - `recommendation_id: string`

6. **`predicate_evaluated`** — one leaf predicate has been resolved.
   - `recommendation_id: string`
   - `path: string[]` (location in the predicate tree, e.g., `["all_of", 0, "any_of", 2]`)
   - `predicate: string` (e.g., `age_between`)
   - `args: object` (literal argument values)
   - `inputs_read: InputRead[]` (which patient-context records were read; see below)
   - `result: "true" | "false" | "unknown"`
   - `missing_data_policy_applied: string | null` (e.g., `"fail_closed"`; null when no missing data)
   - `note: string | null` (optional human-readable detail, e.g., "no final LDL observation within P2Y")

7. **`composite_resolved`** — an `all_of`/`any_of`/`none_of` has been short-circuited or fully evaluated.
   - `recommendation_id: string`
   - `path: string[]`
   - `operator: string`
   - `result: "true" | "false" | "unknown"`
   - `short_circuited: boolean`

8. **`eligibility_evaluation_completed`** — top-level eligibility result is known.
   - `recommendation_id: string`
   - `result: "eligible" | "ineligible" | "unknown"`
   - `final_value: "true" | "false" | "unknown"`

**Strategy events** — describe how the rec is satisfied (or not).

9. **`strategy_considered`** — evaluator begins checking whether an offered Strategy is currently satisfied by patient state.
   - `recommendation_id: string`
   - `strategy_id: string`
   - `strategy_name: string`

10. **`action_checked`** — one `INCLUDES_ACTION` edge has been resolved against patient state.
    - `recommendation_id: string`
    - `strategy_id: string`
    - `action_node_id: string` (e.g., `med:atorvastatin`)
    - `action_entity_type: "Medication" | "Procedure" | "Observation"`
    - `cadence: string | null`
    - `lookback: string | null`
    - `inputs_read: InputRead[]`
    - `satisfied: boolean`
    - `note: string | null`

11. **`strategy_resolved`** — all actions of one Strategy checked.
    - `recommendation_id: string`
    - `strategy_id: string`
    - `satisfied: boolean`

**Risk-score events** — unique to calculated scores.

12. **`risk_score_lookup`** — evaluator is sourcing a score value.
    - `score_name: string` (e.g., `ascvd_10yr`)
    - `resolution: "supplied" | "computed" | "unavailable"`
    - `supplied_value: number | null` (when `resolution="supplied"`)
    - `supplied_computed_date: string | null`
    - `inputs_read: InputRead[]` (when `resolution="computed"` — one per input to the calculator)
    - `computed_value: number | null` (when `resolution="computed"`)
    - `method: string | null` (e.g., `pooled_cohort_equations_2013_goff`)
    - `note: string | null` (e.g., "ancestry missing; defaulted to non-Black" or "inputs insufficient")

**Emission events** — what the evaluator concluded.

13. **`exit_condition_triggered`** — a hard exit is taken (e.g., patient has pre-existing ASCVD).
    - `recommendation_id: string`
    - `exit: string` (controlled token: `out_of_scope_secondary_prevention`, `out_of_scope_familial_hypercholesterolemia`, `out_of_scope_age_below_range`, etc.)
    - `rationale: string` (human-readable)

14. **`recommendation_emitted`** — the evaluator is emitting a rec in the final output.
    - `recommendation_id: string`
    - `status: "due" | "up_to_date" | "not_applicable" | "insufficient_evidence"`
    - `evidence_grade: string`
    - `offered_strategies: string[]` (strategy ids, present when `status="due"`)
    - `satisfying_strategy: string | null` (strategy id, present when `status="up_to_date"`)
    - `reason: string` (human-readable summary)

15. **`evaluation_completed`** — always last. `guideline_id` is null.
    - `recommendations_emitted: int`
    - `duration_ms: int`

**Cross-guideline events** — reserved for F25/F26. Schema defines the types; evaluator does not emit them in F21.

16. **`cross_guideline_match`** — reserved for F25/F26. Indicates a cross-guideline relationship was found during traversal.
    - `source_guideline_id: string`
    - `target_guideline_id: string`
    - `match_type: string`

17. **`preemption_resolved`** — reserved for F25. Indicates a preemption edge was resolved.
    - `preempted_recommendation_id: string`
    - `preempting_recommendation_id: string`
    - `preempted_by_edge_id: string`

### `InputRead` shape

```
{
  source: "patient.demographics" | "patient.conditions" | "patient.observations" |
          "patient.medications" | "patient.social_history" | "patient.risk_scores" |
          "patient.completeness" | "derived"
  locator: string        // dotted path or record id, e.g., "observations[id=obs-ldl-2025-12]"
  value: any             // the literal value read; objects are ok
  present: boolean       // false when the read hit an empty/missing section
}
```

`derived` as a source means the evaluator synthesized the value (e.g., `age_years` from `date_of_birth` + `evaluation_time`). `inputs_read` records every patient-context field the predicate or calculator actually consulted; this is what makes the trace auditable.

## Forest traversal order

**Deterministic traversal order (F21 contract):** guidelines are visited in ascending lexical order of `guideline_id`. This is a contract, not an implementation detail. If the database contains guidelines `guideline:acc-aha-cholesterol-2018`, `guideline:kdigo-ckd-2024`, and `guideline:uspstf-statin-2022`, they are visited in that order.

Within each guideline, traversal follows the v0 ordering: recommendations by id (ascending), depth-first through eligibility trees, strategies by id.

The trace event sequence for a multi-guideline evaluation is:
1. `evaluation_started` (guideline_id: null)
2. For each guideline (in lexical guideline_id order):
   - `guideline_entered`
   - [exit checks, recommendation evaluation, strategy checks — same as v0]
   - `guideline_exited`
3. `evaluation_completed` (guideline_id: null)

## Ordering guarantees

- Traversal is depth-first over offered Recommendations within each guideline.
- Within a Recommendation: `recommendation_considered` → `eligibility_evaluation_started` → predicate tree events (in DFS order) → `eligibility_evaluation_completed`. If eligible, Strategy events follow: for each offered Strategy, `strategy_considered` → N `action_checked` → `strategy_resolved`. Finally, one `exit_condition_triggered` or `recommendation_emitted`.
- Predicate tree events use `path` to locate within the tree; ordering is DFS, left-to-right, short-circuit when a composite can be resolved early.
- The same `PatientContext` + same graph version must produce the same `seq`-ordered event stream. This is the determinism contract.

## Short-circuit semantics

Composites short-circuit in standard three-valued logic:
- `all_of`: any child `false` → `false` (short-circuit); any child `unknown` with no `false` → `unknown`; all `true` → `true`.
- `any_of`: any child `true` → `true` (short-circuit); any child `unknown` with no `true` → `unknown`; all `false` → `false`.
- `none_of`: equivalent to `NOT any_of`.

A short-circuited composite emits a `composite_resolved` event with `short_circuited: true`. Later children in that composite are not evaluated and do not produce `predicate_evaluated` events. This is intentional — the trace reflects what the evaluator actually did, not a counterfactual walk.

## What the trace does NOT include (by design)

- Timing breakdowns per predicate (profile separately if needed).
- Cypher queries issued against Neo4j (the evaluator is free to batch; the trace records *inputs read*, not *queries issued*).
- LLM output — there is no LLM in the evaluator.
- Patient name or any PHI (fixture `patient_fingerprint` is a synthetic hash).

## Related

- Contract: `docs/contracts/eval-trace.schema.json`
- API surface: `docs/contracts/api.openapi.yaml` → `POST /evaluate` returns this trace.
- UI consumption: `docs/specs/ui.md` § Eval tab.
- Predicate semantics: `docs/specs/predicate-dsl.md`
