# Evals

**Status: v0 (statins).** Evals define "done" for the v0 slice. Given a synthetic `PatientContext` and a pinned graph version, the evaluator must emit an `EvalTrace` whose structure matches the fixture's expectations. Evals are the acceptance bar for the `guideline:uspstf-statin-2022` model and the regression suite against schema/evaluator drift.

## Scope

**In scope for v0:**

- Evaluator correctness against the statin model: does the right Recommendation fire with the right status, is the right exit triggered, does the trace carry the expected event types in the expected order.
- Deterministic reproducibility: same `PatientContext` + same graph version + same evaluator version produces the same event stream.

**Out of scope for v0 (tracked in `docs/ISSUES.md`):**

- Historical replay across graph versions. Single graph version in v0.
- Cross-guideline preemption. Only one guideline in v0.
- LLM / agent evals. The agent consumes evaluator output; it's tested separately.
- Ingestion-quality evals.

## Fixture shape

Each case is a directory under `evals/fixtures/<domain>/<id>/` with two files. v0 uses JSON, not YAML; the evaluator and API speak JSON end to end.

```
evals/fixtures/statins/01-high-risk-55m-smoker/
  patient.json           # PatientContext
  expected-outcome.json  # what the trace must contain
```

### patient.json

Matches `docs/contracts/patient-context.schema.json`. Only populate fields that are load-bearing for the case.

### expected-outcome.json

```json
{
  "description": "plain-English summary of what this case tests",
  "expected_recommendations": [
    {
      "recommendation_id": "rec:statin-initiate-grade-b",
      "status": "due",
      "evidence_grade": "B"
    }
  ],
  "expected_trace_contains": [
    { "type": "risk_score_lookup", "resolution": "supplied" },
    { "type": "recommendation_emitted", "recommendation_id": "rec:statin-initiate-grade-b", "status": "due" }
  ],
  "must_not_contain": [
    { "type": "exit_condition_triggered" }
  ]
}
```

Matcher semantics:

- `expected_recommendations`: every entry must appear in the derived recommendation view. Order-independent. Extra emitted recommendations cause a failure unless explicitly allowed (none allowed in v0).
- `expected_trace_contains`: every entry is a partial-match template. The evaluator's event stream must contain at least one event that matches each template (all fields specified in the template match; unspecified fields ignored). Order is asserted when two templates both carry an `order_hint` field; otherwise unordered.
- `must_not_contain`: no event in the stream may match any of these partial-match templates.

## Execution model

Pseudocode:

```
for case_dir in evals/**/<id>/:
  ctx = load_json(case_dir / "patient.json")
  expected = load_json(case_dir / "expected-outcome.json")
  graph = load_graph(pinned_version)
  evaluator = load_evaluator(pinned_version)
  trace = evaluator.evaluate(ctx, graph)
  recs = derive_recommendations(trace)
  assert_matches(expected, trace, recs)
```

Trace shape is defined in `docs/specs/eval-trace.md` and `docs/contracts/eval-trace.schema.json`. Recommendations are a derived view; the trace is the primary output.

**Pass/fail:** a fixture passes when every `expected_recommendations` entry matches, every `expected_trace_contains` template matches, and no `must_not_contain` template matches. Determinism is asserted by running each fixture twice and byte-comparing the serialized trace.

## Determinism contract

Same `PatientContext` (including `evaluation_time`) + same graph version + same evaluator version produces a byte-identical serialized trace. If a fixture flakes, fix the evaluator, not the fixture.

## v0 seed set

`evals/fixtures/statins/`:

| ID | Scenario | What it exercises |
|---|---|---|
| `01-high-risk-55m-smoker` | 55M, smoker, HTN, ASCVD 18.2% supplied | Grade B happy path |
| `02-borderline-55f-sdm` | 55F, ASCVD 8.4% supplied | Grade C band, SDM strategy offered |
| `03-too-young-35m` | 35M, smoker, HTN | Age-below-range exit before risk lookup |
| `04-grade-i-78f` | 78F, HTN + T2DM | Grade I band (age >= 76) |
| `05-prior-mi-62m` | 62M, prior MI on atorvastatin | Secondary-prevention exit |

See `evals/fixtures/statins/README.md` for coverage notes and deferred cases.

## Related docs

- `docs/specs/patient-context.md` + `docs/contracts/patient-context.schema.json` — input shape.
- `docs/specs/eval-trace.md` + `docs/contracts/eval-trace.schema.json` — trace shape.
- `docs/specs/predicate-dsl.md` + `docs/contracts/predicate-catalog.yaml` — predicates.
- `docs/specs/schema.md` — graph schema.
- `docs/reference/guidelines/statins.md` — the concrete model the fixtures are evaluated against.
