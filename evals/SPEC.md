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

## Three-arm eval harness (v1, F22)

The eval harness extends the v0 fixture system with LLM-based evaluation across three arms. The harness measures whether graph-retrieved context (Arm C) produces better clinical next-best-action recommendations than vanilla LLM knowledge (Arm A) or flat RAG (Arm B).

### Arms

| Arm | ID | Context supplied to LLM |
|-----|-----|-------------------------|
| A | `a` | `PatientContext` only. No guideline material. Tests LLM training knowledge. |
| B | `b` | `PatientContext` + top-k chunks from guideline prose (flat RAG over `docs/reference/guidelines/*.md`). |
| C | `c` | `PatientContext` + graph-retrieved context: serialized `EvalTrace` summary + relevant subgraph. |

All arms use the same LLM (pinned in `evals/rubric.md`), same system prompt, same temperature (0), same max tokens. Only the context input varies.

### Fixture format extension

v1 fixtures add `expected-actions.json` alongside the v0 files:

```
evals/fixtures/<guideline>/<fixture_id>/
  patient.json              # PatientContext (v0)
  expected-outcome.json     # trace assertions (v0)
  expected_trace.json       # golden trace (v0)
  expected-actions.json     # NEW: curated NBA list for harness scoring
  arms/                     # runtime output (gitignored)
    a/output.json
    a/meta.json
    a/scores.json
    b/output.json
    b/meta.json
    b/scores.json
    c/output.json
    c/meta.json
    c/scores.json
```

### expected-actions.json schema

```json
{
  "description": "plain-English summary",
  "actions": [
    {
      "id": "string",
      "label": "human-readable action name",
      "rationale": "clinical justification",
      "source_rec_id": "optional: graph rec id",
      "priority": 1
    }
  ],
  "contraindications": [
    {
      "id": "string",
      "label": "action that should NOT appear",
      "rationale": "why it's contraindicated"
    }
  ]
}
```

### Scoring

Two scoring mechanisms run per fixture per arm:

1. **Deterministic structural checks** — binary pass/fail:
   - `expected_actions_present`: all expected action labels/ids found in output
   - `contraindications_absent`: no contraindicated actions found in output
   - `output_parseable`: output is valid JSON

2. **LLM judge** (rubric-based, 1-5 per dimension):
   - `completeness`: are all expected actions present?
   - `clinical_appropriateness`: are recommendations safe and correct?
   - `prioritization`: is sequencing reasonable?
   - `integration`: cross-guideline interactions handled? (scores 5 by default in Phase 1)
   - `composite`: arithmetic mean

Structural checks are logged alongside rubric scores but not combined into the composite.

### Arm C serialization shape

The graph-context arm receives a frozen context object:

```json
{
  "trace_summary": {
    "matched_recs": [
      {
        "recommendation_id": "string",
        "guideline_id": "string",
        "status": "string",
        "evidence_grade": "string",
        "reason": "string",
        "offered_strategies": ["string"],
        "satisfying_strategy": "string | null"
      }
    ],
    "exit_conditions": [...],
    "preemption_events": [],
    "modifier_events": []
  },
  "subgraph": {
    "nodes": [{"id": "string", "type": "string", "label": "string"}],
    "edges": [{"source": "string", "target": "string", "type": "string"}],
    "rendered_prose": "natural-language rendering of the evaluation"
  },
  "convergence_summary": {
    "shared_actions": [
      {
        "entity_id": "string",
        "entity_label": "string",
        "entity_type": "Medication | Condition | Observation | Procedure",
        "recommended_by": [
          {
            "rec_id": "string",
            "guideline": "string",
            "evidence_grade": "string",
            "status": "string",
            "via_strategy": "string"
          }
        ],
        "guideline_count": "integer (>= 2)",
        "convergence_type": "reinforcing"
      }
    ],
    "convergence_prose": "natural-language paragraph summarising cross-guideline agreement"
  }
}
```

The `rendered_prose` field is a natural-language summary so the LLM doesn't have to reason over JSON alone.

The `convergence_summary` key surfaces clinical entities targeted by strategies from two or more guidelines. `shared_actions` is empty when only one guideline is traversed or no entities are shared. `convergence_type` is always `"reinforcing"` until clinician-reviewed cross-guideline edges return (at which point conflicting convergence may also be detected). `convergence_prose` is a human-readable paragraph when shared actions exist, empty string otherwise.

### Arm B chunking

- Source: `docs/reference/guidelines/*.md` (guideline prose; excludes `cross-guideline-map.md` and `preemption-map.md`)
- Chunk size: ~500 tokens with ~50-token overlap
- Embedding model: `text-embedding-3-small` (OpenAI)
- Retrieval: top-k=5 chunks by cosine similarity against a query built from patient demographics and conditions

### Braintrust integration

The harness uses Braintrust's native `Eval()` framework. Each arm runs as a separate experiment (`{run-name}-arm-a`, `{run-name}-arm-b`, `{run-name}-arm-c`), enabling side-by-side comparison in the Braintrust UI. `BRAINTRUST_API_KEY` is required.

Caching, experiment logging, and trial management are handled by Braintrust. The `trial_count` parameter controls self-consistency (number of times each input is scored).

## Related docs

- `docs/specs/patient-context.md` + `docs/contracts/patient-context.schema.json` — input shape.
- `docs/specs/eval-trace.md` + `docs/contracts/eval-trace.schema.json` — trace shape.
- `docs/specs/predicate-dsl.md` + `docs/contracts/predicate-catalog.yaml` — predicates.
- `docs/specs/schema.md` — graph schema.
- `docs/reference/guidelines/statins.md` — the concrete model the fixtures are evaluated against.
- `evals/rubric.md` — rubric v1 dimensions, model pinning, scoring criteria.
- `evals/README.md` — how to run the harness.
