# Build status

What exists vs. what's spec-only. Update in any PR that moves a component forward.

States: `spec-only` → `scaffolded` → `implemented` → `tested` → `live`.

## Graph (`/graph`)

| Component | State | Notes |
|---|---|---|
| Neo4j schema (constraints, indexes) | implemented | Uniqueness constraints on `id` per label in `graph/constraints.cypher`. Indexes deferred — add when `/api` traversal needs them. |
| Statin seed (`seed.cypher`) | implemented | Model: `reference/statin-model.md`. 23 nodes / 14 edges, fully idempotent. Fixture-level test runs against this when evaluator lands. |
| Value-set registry | spec-only | External, keyed by (clinical_entity_id, label). Storage medium TBD. |

## API (`/api`)

| Component | State | Notes |
|---|---|---|
| FastAPI skeleton | tested | Python 3.12, FastAPI, Pydantic v2. `/healthz`, `/version`, `/nodes/{id}`, `/nodes/{id}/neighbors` wired to Neo4j. 10 tests (unit + integration). Shipped in PR #6. |
| Trace-first evaluator | scaffolded | Spec: `specs/eval-trace.md`. Contract: `contracts/eval-trace.schema.json`. Exit-condition path working (fixture 03). Full rec evaluation in feature 04. |
| Predicate engine (v0 subset) | scaffolded | Contract: `contracts/predicate-catalog.yaml`. Fixture 03 only: age predicates implemented; all others stub to NotImplementedError. |
| Patient-context validator | spec-only | Contract: `contracts/patient-context.schema.json`. |
| REST endpoints | scaffolded | Contract: `contracts/api.openapi.yaml`. `POST /evaluate` implemented in feature 03. `/search` still spec-only. |
| Contract alignment tests | tested | 10 tests: OpenAPI path/method/response alignment, predicate catalog coverage, build-status consistency. PR #8. |

## UI (`/ui`)

| Component | State | Notes |
|---|---|---|
| Next.js skeleton | spec-only | Next.js 14 App Router, TypeScript. |
| OpenAPI → TS codegen | spec-only | Against `contracts/api.openapi.yaml`. |
| Shared GraphCanvas (Cytoscape.js) | spec-only | |
| Explore tab | spec-only | Spec: `specs/ui.md`. |
| Eval tab | spec-only | Spec: `specs/ui.md`. |

## Evals (`/evals`)

| Component | State | Notes |
|---|---|---|
| Eval spec | implemented | `evals/SPEC.md`. |
| Statin fixtures (5) | implemented | `evals/statins/01..05`. Awaiting evaluator to run against. |
| Eval runner | spec-only | Runs each fixture, asserts trace + recommendation expectations. |

## CI

| Component | State | Notes |
|---|---|---|
| GitHub Actions workflow (`ci.yml`) | implemented | Three jobs: `api-tests`, `contract-lint`, `graph-smoke`. Branch protection pending human enablement. |

## Archived

| Component | State | Notes |
|---|---|---|
| Ingestion pipeline | archived | Deferred until LLM-assisted drafting returns. |
| CRC seed + fixtures | archived | Superseded by statins (ADR 0013). |
| Review-and-flag workflow | archived | Deferred until post-v0. |

## Update protocol

Update this file in the same PR that moves a component's state. If a PR doesn't advance a component, it doesn't touch this file. Partial progress = a note in the Notes column, not an inflated state.
