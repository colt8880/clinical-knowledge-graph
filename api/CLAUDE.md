# /api

Python/FastAPI service that runs the trace-first evaluator and exposes graph read endpoints. Consumed by `/ui` (Explore tab reads graph nodes/edges; Eval tab posts `PatientContext` and renders the returned `EvalTrace`).

## Stack

- Python 3.12
- FastAPI + Pydantic v2
- `neo4j` (official driver)
- `pytest` for unit and fixture tests

## Load before working here

1. `../docs/specs/eval-trace.md` — event-stream shape (this is the primary output)
2. `../docs/contracts/eval-trace.schema.json`
3. `../docs/specs/patient-context.md` — evaluator input
4. `../docs/contracts/patient-context.schema.json`
5. `../docs/specs/predicate-dsl.md` + `../docs/contracts/predicate-catalog.yaml`
6. `../docs/contracts/api.openapi.yaml` — HTTP surface
7. `../docs/specs/api-primitives.md`
8. `../docs/reference/guidelines/statins.md` — the graph the evaluator runs against
9. `../docs/decisions/0005-internal-rest-api.md`, `0007-homegrown-predicate-dsl.md`, `0014-v0-scope-and-structure.md`

## Scope

- Trace-first evaluator. `evaluate(ctx, graph)` returns an ordered `EvalTrace`; recommendations are derived from the trace, not stored separately.
- Predicate engine backed by the v0 predicate subset in `predicate-catalog.yaml`.
- Three-valued logic (true / false / unknown) plus per-predicate missing-data policy, overridable via `PatientContext.policy_overrides`.
- REST endpoints per `api.openapi.yaml`: `/healthz`, `/version`, `POST /evaluate`, `GET /nodes/{id}`, `GET /nodes/{id}/neighbors`, `GET /search`.
- Every response carries the version envelope (`spec_tag`, `graph_version`, `evaluator_version`, echoed `evaluation_time`).

## Not in scope (v0)

- Cross-guideline preemption (single guideline).
- Cascade / `TRIGGERS_FOLLOWUP` evaluation (schema-only in v0).
- `expects` result-conditional semantics (schema-only).
- Live ASCVD / PCE calculation. Evaluator reads `patient.risk_scores.ascvd_10yr` if supplied; otherwise it emits a `risk_score_lookup` event with `resolution: missing` and treats the predicate as `unknown`.
- Auth, multi-tenant, caching beyond a single in-process graph load.

## Build conventions

- Evaluator is pure: no wall-clock reads, no RNG, no external I/O during `evaluate()`. All inputs are `PatientContext` + a loaded graph snapshot.
- Event order is deterministic. Recommendations visited in the order defined by the graph seed.
- Adding a predicate: entry in `predicate-catalog.yaml`, prose in `predicate-dsl.md`, one evaluator function, one unit test, at least one trace-level assertion.
- Pydantic models for request/response; regenerate / hand-sync from the JSON Schema and OpenAPI contracts.
- Trace serialization is stable: canonical field order, sorted object keys, no optional whitespace. Eval tests byte-compare the serialized trace across two runs.

## Definition of done

Evaluator:

1. Every predicate in `predicate-catalog.yaml` implemented and unit-tested.
2. Three-valued logic matches `predicate-dsl.md`.
3. Missing-data defaults match the catalog; `policy_overrides` honored.
4. All fixtures in `evals/fixtures/statins/` pass (structural + determinism byte-compare).
5. Every emitted event validates against `eval-trace.schema.json`.

API:

1. Every endpoint in `api.openapi.yaml` implemented with matching request/response shapes.
2. Contract tests (OpenAPI-driven) pass.
3. Version envelope present on every response.
