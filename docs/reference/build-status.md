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
| FastAPI skeleton | spec-only | Target: Python 3.12, Pydantic v2. |
| Trace-first evaluator | spec-only | Spec: `specs/eval-trace.md`. Contract: `contracts/eval-trace.schema.json`. |
| Predicate engine (v0 subset) | spec-only | Contract: `contracts/predicate-catalog.yaml`. |
| Patient-context validator | spec-only | Contract: `contracts/patient-context.schema.json`. |
| REST endpoints | spec-only | Contract: `contracts/api.openapi.yaml`. |

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

## Archived

| Component | State | Notes |
|---|---|---|
| Ingestion pipeline | archived | Deferred until LLM-assisted drafting returns. |
| CRC seed + fixtures | archived | Superseded by statins (ADR 0013). |
| Review-and-flag workflow | archived | Deferred until post-v0. |

## Update protocol

Update this file in the same PR that moves a component's state. If a PR doesn't advance a component, it doesn't touch this file. Partial progress = a note in the Notes column, not an inflated state.
