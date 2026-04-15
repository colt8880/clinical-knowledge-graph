# API Primitives

**Status: v0.**

Internal REST API (FastAPI) exposing a fixed set of traversal primitives over the clinical knowledge graph. The agent and the review tool are the only callers; neither issues Cypher directly. See ADR 0005.

This doc is authoritative for **what the API does**. The input shape is authoritative in `patient-context.md` + `patient-context.schema.json`. The predicate evaluator semantics are authoritative in `predicate-dsl.md`. This spec references those rather than duplicating them.

## Design invariants

- **Determinism.** Given a fixed `(graph_version, evaluator_version, PatientContext)`, every endpoint returns byte-identical output. No wall-clock reads. Every response echoes the versions it was computed against. `PatientContext.evaluation_time` is the sole time source.
- **Provenance out.** Every recommendation, strategy, action, and preemption in a response carries `source_guideline_id`, `source_section`, and `effective_date` from the underlying edge or node. Clients never see orphan assertions.
- **Named primitives only.** No generic `/query` endpoint. Each new consumer need is a new primitive, not a new query shape.
- **Read-only.** No write endpoints in v0. Curation happens outside this API. Flagging from the review tool is a separate service (see `review-workflow.md`), not an API primitive.
- **Structured "cannot evaluate," not silent false.** A missing field under `fail_closed` policy is surfaced with the predicate path that produced the unknown, not collapsed to a negative match.

## Request/response conventions

### Envelope

Every response is JSON with a shared envelope:

```json
{
  "data": { ... primitive-specific payload ... },
  "meta": {
    "graph_version": "2026.04.0",
    "evaluator_version": "0.3.1",
    "spec_tag": "v0.5",
    "evaluation_time": "2026-04-14T12:00:00Z",
    "request_id": "uuid",
    "caller": "agent" | "review-tool"
  },
  "warnings": [ ... structured warnings, see below ... ]
}
```

`warnings` carries non-fatal signals (unresolved value-set labels, data-quality gaps, unused PatientContext fields, etc.). It is always present as an array, empty when clean.

### Identity and auth

- Internal API, internal callers only. v0 runs inside a private network; no external exposure.
- Every request carries an `X-Caller` header identifying the service (`agent`, `review-tool`, `eval-runner`) and an `X-Caller-Principal` header identifying the upstream actor when known (user id for review-tool sessions, eval fixture id for the runner, agent session id for agent traffic). Caller identity is logged with every request; it is not used for authorization in v0.
- No per-endpoint authorization. Revisit when we add a second team or an external consumer. Tracked in `docs/ISSUES.md`.
- Requests are rate-limited per-caller at a generous default; exceeding the limit returns `429` with `Retry-After`.

### Error semantics

HTTP status codes map to a small taxonomy. Every error body uses the envelope above with `data: null` and an `error` object:

```json
{
  "error": {
    "code": "missing_required_field",
    "message": "human-readable",
    "details": { "field": "patient.dob", "predicate_path": "$.all_of[2]" }
  }
}
```

| HTTP | `error.code`                         | When                                                                                          |
|------|--------------------------------------|------------------------------------------------------------------------------------------------|
| 400  | `invalid_patient_context`            | PatientContext fails JSON Schema validation                                                    |
| 400  | `missing_required_field`             | A predicate with `policy: require` hit missing data (see `predicate-dsl.md`)                   |
| 400  | `invalid_node_id` / `invalid_code`   | Referenced node or code not in the graph / ontology                                            |
| 404  | `not_found`                          | `node_id` does not exist at `graph_version`                                                    |
| 409  | `unresolvable_preemption`            | Two `PREEMPTED_BY` edges tie on priority with both conditions true (spec bug, surfaces loudly) |
| 422  | `cycle_detected`                     | Traversal hit a cycle the primitive cannot resolve (not cascade depth cap; see below)          |
| 422  | `unresolved_value_set`               | `INCLUDES_ACTION.expects` label has no entry in the value-set registry for this entity         |
| 429  | `rate_limited`                       |                                                                                                |
| 500  | `internal_error`                     | Catchall. Includes `request_id` for correlation.                                               |

A `fail_closed` predicate returning `unknown` at the top level is **not** an error; it returns `200 OK` with the recommendation marked `status: cannot_evaluate` and the offending predicate path in the payload.

### Versioning

- URL-versioned: `/v0/...`. Breaking changes bump the path.
- `graph_version` and `evaluator_version` are echoed, never inputs. The API serves the version it was deployed with.
- Callers that need a specific pin go through the eval runner, not this API.

## Primitives (v0)

All primitives are `POST` — `GET` would require serializing `PatientContext` into query strings, which is hostile to the size and nesting of the payload.

### `POST /v0/recommendations/for-condition`

End-to-end: pull Recommendations `FOR_CONDITION` a given Condition, apply eligibility, apply preemption, compute Strategy satisfaction, return the ranked set. This is the agent's primary entry point.

**Request:**
```json
{
  "condition_code": { "system": "snomed", "code": "363406005" },
  "patient_context": { ... PatientContext ... },
  "options": {
    "include_not_eligible": false,
    "include_predicate_traces": false,
    "max_cascade_depth": 3
  }
}
```

`condition_code` resolves to a `Condition` node via code-list lookup (every `Condition` node carries `snomed_codes[]` and `icd10_codes[]`; any match on either resolves the node). Unresolvable → `invalid_code`.

**Response `data`:**
```json
{
  "condition": { "id": "cond:crc", "display": "Colorectal cancer" },
  "recommendations": [
    {
      "id": "rec:uspstf-crc-avg-risk-50-75",
      "status": "due" | "up_to_date" | "not_eligible" | "cannot_evaluate",
      "evidence_grade": "A",
      "intent": "screening",
      "clinical_nuance": "...",
      "provenance": { "guideline_id": "...", "source_section": "...", "effective_date": "2021-05-18" },
      "eligibility": {
        "result": true | false | "unknown",
        "matched_predicates": [...],         // present when include_predicate_traces
        "unmet_predicates": [...],           // present when status != up_to_date
        "unknown_predicates": [...]          // present when cannot_evaluate
      },
      "preemption": null | {
        "preempted_by": "rec:...",
        "priority": 10,
        "rationale": "Patient has Lynch syndrome; USPSTF avg-risk does not apply",
        "condition_matched": [...]
      },
      "strategies": [
        {
          "id": "strategy:crc-colonoscopy-alone",
          "name": "Colonoscopy alone",
          "satisfied": false,
          "evidence_note": "...",
          "actions": [
            {
              "entity_id": "proc:colonoscopy",
              "entity_display": "Colonoscopy",
              "codes": [{ "system": "cpt", "code": "45378" }],
              "cadence": "P10Y",
              "lookback": "P10Y",
              "priority": "routine",
              "intent": "screening",
              "expects": null,
              "satisfaction": {
                "satisfied": false,
                "matched_record": null,      // or {date, code, result_label}
                "reason": "no colonoscopy in lookback window"
              }
            }
          ]
        }
      ],
      "followups": [                          // from TRIGGERS_FOLLOWUP
        { "on": "positive_result", "recommendation_id": "rec:..." }
      ]
    }
  ]
}
```

**Semantics:**

1. Pull Recs with `-[:FOR_CONDITION]->(cond)`.
2. Filter by `trigger`. `patient_state` recs are always candidates. Event-triggered recs appear only if the request includes a triggering event (see `/for-event`); from `/for-condition` they are excluded unless `options.include_event_triggered` is set.
3. For each candidate, evaluate `structured_eligibility` against PatientContext.
   - `true` → eligible.
   - `false` → emitted with `status: not_eligible` only if `options.include_not_eligible`; otherwise dropped.
   - top-level `unknown` → `status: cannot_evaluate`, unmet/unknown predicates included.
4. Resolve preemption (see algorithm below) on the eligible set. Preempted recs are dropped; the preempting rec appears with `preemption` populated.
5. For each surviving Rec, compute Strategy satisfaction (see cadence algorithm below). `status` = `up_to_date` if any Strategy satisfied, else `due`.
6. Rank: `due` before `up_to_date` before `not_eligible`; within a tier, by `evidence_grade` (A > B > C > D > I), then by `priority` of the highest-priority action across strategies.

### `POST /v0/recommendations/for-event`

Given a clinical event (new observation result, new diagnosis, medication start), return Recommendations whose `trigger` matches.

**Request:**
```json
{
  "event": {
    "type": "observation_result" | "condition_onset" | "medication_start",
    "entity_id": "obs:fit",                    // resolved from code or given directly
    "code": { "system": "loinc", "code": "57905-2" },
    "value_label": "positive",                 // observation_result only
    "observed_at": "2026-04-10T09:15:00Z"
  },
  "patient_context": { ... },
  "options": { ... same as above ... }
}
```

**Semantics:**

1. Find Recs with `-[:TRIGGERED_BY {criteria}]->(entity)` matching the event's entity, where `criteria` evaluates true against the event payload (including `value_label` resolution through the value-set registry).
2. Evaluate `structured_eligibility` against PatientContext.
3. Same preemption + strategy satisfaction logic as `/for-condition`.
4. Response shape identical to `/for-condition`.

### `POST /v0/evaluate-criterion`

Evaluate a predicate tree against PatientContext. Used by the review tool and by eval fixtures.

**Request:**
```json
{
  "predicate": { ... predicate tree ... },
  "patient_context": { ... },
  "options": { "include_trace": true }
}
```

**Response `data`:**
```json
{
  "result": true | false | "unknown",
  "trace": {
    "node": { "op": "all_of", "children": [...] },
    "evaluation": [
      { "path": "$.all_of[0]", "predicate": "age_between", "args": {...}, "result": true, "evidence": {...} },
      { "path": "$.all_of[1]", "predicate": "has_condition_history", "args": {...}, "result": "unknown", "reason": "no conditions[] array in context; policy: fail_closed" }
    ]
  }
}
```

`evidence` for matching predicates cites which PatientContext resource(s) contributed (e.g., `{ "observation_ids": ["obs-123"] }`). This is how the review tool renders "why did this fire."

Missing data under `require` policy returns HTTP 400 `missing_required_field`, not `unknown` in the trace.

### `POST /v0/traverse`

Bounded graph walk. Powers the review tool's graph canvas and supports tracing a recommendation chain without invoking the evaluator.

**Request:**
```json
{
  "start_node_id": "rec:uspstf-crc-avg-risk-50-75",
  "directions": ["outbound"] | ["inbound"] | ["both"],
  "edge_types": ["FOR_CONDITION", "OFFERS_STRATEGY", "INCLUDES_ACTION", "PREEMPTED_BY", "TRIGGERS_FOLLOWUP"],
  "max_depth": 2,
  "max_nodes": 200
}
```

**Response `data`:**
```json
{
  "nodes": [ { "id": "...", "labels": ["Recommendation"], "attrs": {...} } ],
  "edges": [ { "id": "...", "type": "OFFERS_STRATEGY", "from": "...", "to": "...", "attrs": {...}, "provenance": {...} } ],
  "truncated": false,
  "cycles_detected": []
}
```

Walks are depth-capped and node-capped. Cycles are detected and recorded but do not abort the response (cap truncates first). `not_found` returns 404. No patient context required; this is pure graph structure.

### `POST /v0/cascade-trace`

Starting from a Recommendation, walk `TRIGGERS_FOLLOWUP` edges to return the cascade tree. Distinct from `/traverse` because cascades have cycle risk (surveillance → surveillance) and the review tool renders them differently.

**Request:**
```json
{
  "start_recommendation_id": "rec:uspstf-crc-avg-risk-50-75",
  "max_depth": 5
}
```

**Response `data`:**
```json
{
  "root": "rec:...",
  "nodes": [...],
  "edges": [ { "from": "rec:A", "to": "rec:B", "on": "positive_result", ... } ],
  "cycles_detected": [ { "path": ["rec:surv-3y", "rec:surv-3y"], "truncated_at_depth": 4 } ],
  "truncated_at_depth": false
}
```

See cycle detection algorithm below.

## Cross-cutting algorithms

### Preemption resolution

For a set of eligible Recs `R` and a PatientContext `P`:

```
for each rec in R:
  matching_preemptions = []
  for each incoming PREEMPTED_BY edge e where rec -[e]-> preempting_rec:
    if evaluate(e.condition, P) == true and eligibility(preempting_rec, P) == true:
      matching_preemptions.append((e.priority, preempting_rec, e.rationale))
  if matching_preemptions is non-empty:
    winner = max(matching_preemptions, key=priority)
    if two entries tie at max priority: raise unresolvable_preemption (409)
    mark rec as preempted by winner
```

Notes:
- Direction: the edge is `source_rec -[:PREEMPTED_BY]-> replacement_rec`. The replacement must itself be eligible; if not, preemption doesn't fire and the source rec stands.
- Preemption chains (A preempted by B preempted by C) resolve by repeating until no further preemption applies. Cap at 5 hops; beyond that raise `cycle_detected`.
- A rec that is preempted is dropped from the output list; the replacing rec appears with its own full payload and a `preemption` block naming what it replaced (not what replaced it — this is written from the replacement's perspective for agent legibility).
- Unknown condition (`fail_closed` predicate in `e.condition`): preemption does not fire, and a warning is attached to the source rec (`preemption_unknown`) so the agent can escalate to clinician review.

### Cadence / Strategy satisfaction

Per schema, a Rec is up-to-date if any offered Strategy is satisfied; a Strategy is satisfied iff every `INCLUDES_ACTION` edge is satisfied (conjunction).

```
for each action edge a in strategy.INCLUDES_ACTION:
  window_start = PatientContext.evaluation_time - a.lookback
  candidates = patient records matching a.entity codes, within [window_start, evaluation_time],
               with status in {final, amended, corrected, completed, active}
  if a.expects is null:
    action.satisfied = candidates is non-empty
  else:
    resolved_value_set = value_set_registry[(a.entity_id, a.expects)]
    if resolved_value_set missing: raise unresolved_value_set (422)
    matching = [c for c in candidates if c.coded_result in resolved_value_set]
    unscored = [c for c in candidates if c.coded_result is null]
    action.satisfied = matching is non-empty
    if not matching and unscored: warnings.append(data_quality_gap)
  action.matched_record = most recent match if satisfied else null

strategy.satisfied = all(action.satisfied for action in strategy.actions)
```

Notes:
- Cadence as a separate concept is just `lookback` in this algorithm; the `cadence` attribute is kept on the response for agent scheduling, not evaluated here.
- Status filter: records with `status in {entered-in-error, cancelled, not-done}` are dropped before matching (mirrors PatientContext resource rules).
- One-shot actions (`cadence: null`, `lookback: null`): window is `[patient.dob, evaluation_time]`.

### Cycle detection

Two distinct cycle classes:

**Preemption chains** (A preempts B preempts C): hard cap at 5 hops; beyond that the response fails with `cycle_detected`. Real guidelines should not chain this deep; hitting the cap means a spec bug.

**`TRIGGERS_FOLLOWUP` cascades** (surveillance → surveillance): legitimate in practice (every 3 years forever). Traversal caps at `max_depth` (default 5 for `/cascade-trace`, 3 for `/recommendations/*`); revisits of the same rec id are recorded in `cycles_detected` but do not abort. Cadence gating prevents infinite reorder loops at agent runtime; the API's job is only to not recurse forever.

### Result-conditional action check

See "Cadence / Strategy satisfaction" above for the full algorithm. Called out separately because the same machinery also applies in `/for-event`: when an event carries `value_label: positive`, the `TRIGGERED_BY` criteria resolve through the same value-set registry, so curators maintain one mapping per `(entity, label)` pair.

### Evaluator version

The evaluator is a separately-versioned component. `evaluator_version` in the response identifies the predicate evaluator behavior (policy interpretation, label resolution rules, value-set registry snapshot). Graph content and evaluator behavior are pinned independently so a semantically-identical graph can be served through a fixed-evaluator-version eval run.

## Performance and caching

v0 targets are advisory; measure and revisit once we have real traffic.

- `/recommendations/for-condition` p95 budget: 300ms for a PatientContext of typical size (<50 observations, <10 conditions, <20 procedures).
- `/evaluate-criterion` p95 budget: 50ms for trees up to 20 predicates.
- `/traverse` p95 budget: 100ms at `max_depth: 3`, `max_nodes: 200`.

**Caching strategy:**
- **Graph structure cache.** Keyed on `graph_version` + node/edge query. Invalidated on graph deploy. In-process LRU is sufficient for v0; revisit when we add a second API instance.
- **No PatientContext-keyed caching.** Contexts are single-use and large; caching them adds complexity without meaningful hit rate. If a caller needs memoization, it caches responses upstream by its own request id.
- **Value-set registry cache.** Loaded on process start, reloaded on `SIGHUP` or graph deploy.

## Machine contract pairing

Per ADR 0010, this spec pairs with:
- `docs/contracts/patient-context.schema.json` — input validation.
- `docs/contracts/predicate-catalog.yaml` — what `evaluate_criterion` accepts.
- A future `docs/contracts/api.openapi.yaml` — request/response shape, error codes, envelope. **Not written for v0**; tracked in `docs/ISSUES.md`. Any change to request/response shape in this doc requires updating the OpenAPI contract in the same commit once it exists.

## Not in v0

- **Write endpoints.** Curation happens via graph operations outside the API. Review-tool flag submissions go to a separate service.
- **External exposure / MCP wrapping.** Internal-only. The REST contract is shaped to be MCP-wrappable later with no semantic changes.
- **Per-endpoint authorization.** Internal, single-team. Caller identity is logged, not enforced.
- **Batch endpoints.** Agents with multi-condition workloads make N requests. Revisit if we see N > 20 per patient encounter.
- **Streaming / subscriptions.** All responses are synchronous.
- **Historical queries** ("what would this have returned on date X"). Deterministic today on a pinned `graph_version`, but we don't retain old graph snapshots as queryable state in v0.

## Open questions

Tracked in `docs/ISSUES.md`:
- OpenAPI contract for this API.
- Auth model when a second team or external caller appears.
- Response shape for the deferred USMSTF procedure-level `expects` (see schema.md "Deferred: procedure-level result expectations").
- Whether `cascade-trace` belongs here or inside the review tool as a client-side traversal over `/traverse`.
