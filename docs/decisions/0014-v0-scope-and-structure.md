# 0014. v0 scope reduction, repo restructure, Python for /api

Status: Accepted
Date: 2026-04-15
Supersedes parts of: 0004 (name), 0006 (scope — see 0013)
Defers: 0003 (ingestion pipeline), 0008 (pregnancy record)

## Context

The v0 spec set (schema, predicate DSL, patient-context, API primitives, review workflow) was built to be general. Now that we're ready to implement, generality is weight, not leverage. The goal of v0 is four concrete deliverables:

1. Codify USPSTF statin primary prevention as a knowledge graph.
2. Five synthetic patients that exercise each traversal path.
3. An **Eval UI** that steps through evaluation trace-by-trace.
4. An **Explorer UI** for manual graph traversal (co-located with the Eval UI).
5. APIs to support 1–4.

The review-workflow spec (flagging, curator queue, editing) is not on the critical path for proving the eval loop works. The LLM-assisted ingestion pipeline is not needed when a single guideline is hand-authored. Pregnancy as a top-level record is not touched by statins.

## Decisions

### 1. Trace-first evaluator

The evaluator's primary output is a **structured, ordered trace** of every step taken (node visited, predicate evaluated with inputs/result, strategy satisfaction check, exit condition, recommendation emitted). Final recommendations are a derived view over the trace, not a separate output. The trace is specified as a contract (`docs/specs/eval-trace.md` + `docs/contracts/eval-trace.schema.json`) and land **before** any evaluator code is written. The Eval UI is a replay of the trace.

Rationale: retrofitting a trace after the evaluator is built produces a lossy debug log, not a product surface. The UI is the demo; the trace is the API of the demo.

### 2. Scope reductions (active in v0)

Deferred but retained in the schema/catalog (no deletion, just not exercised):
- `PREEMPTED_BY` edges (nothing to preempt to with one guideline).
- Pregnancy top-level record (ADR 0008 remains valid; dormant in v0).
- Cascade `TRIGGERS_FOLLOWUP` (statins has no cascade).
- Procedure-level `expects` / result-conditional satisfaction on procedures.

Deferred and removed from active surface:
- Review workflow: flag categories, curator queue, proposed-edit workflow. `docs/specs/review-workflow.md` moved to `docs/archive/`.
- LLM-assisted ingestion pipeline. `/ingestion/` moved to `docs/archive/ingestion-dir/`. One guideline is hand-authored; a shape-validator script is sufficient.
- CRC model and CRC eval fixtures. `docs/reference/crc-model.archived.md`, `evals/archive/crc/`. Preserved as reference; not in v0 build set.

The predicate catalog is pruned to predicates the statin model and 5 patients actually exercise, plus the composites. Dormant predicates are removed from the active catalog and re-added as needed when new guidelines enter scope. The full pre-prune catalog is in git history.

### 3. Rename `/review-tool` → `/ui`

The app is no longer a "review tool" — it is the application surface for the two user-facing views: Eval (trace stepper) and Explore (manual graph traversal). Both tabs live in one Next.js app. ADR 0004's technology choice (Next.js + Cytoscape.js) stands; the name was stale.

### 4. `/api` in Python (FastAPI + Pydantic v2)

Python chosen over Node/TypeScript. The project's trajectory (FHIR tooling, ontology mappers, future LLM-assisted ingestion per ADR 0003, additional risk calculators) is Python-shaped. The one real cost — no shared types with the Next.js UI — is mitigated by generating a TypeScript client from the OpenAPI contract in CI.

Stack:
- Python 3.12
- FastAPI for HTTP
- Pydantic v2 for request/response models and patient-context validation (Pydantic models derived from `docs/contracts/*.schema.json`)
- neo4j-python-driver for graph access
- `openapi-typescript-codegen` (or equivalent) in CI emits the `/ui` client

### 5. Repo layout (v0)

```
/graph            # hand-authored statin seed + migrations + validator
  seed.cypher
  migrations.cypher
  validate.py
  CLAUDE.md
/api              # single FastAPI service (evaluator + query + trace)
  pyproject.toml
  CLAUDE.md
/ui               # Next.js app with two tabs: /eval and /explore
  CLAUDE.md
/evals
  /statins
    /<case_id>/{patient.json, expected-trace.json}
  /archive/crc/   # preserved CRC fixtures
  SPEC.md
/docs
  /specs          # schema, predicate-dsl, patient-context, api-primitives, eval-trace, ui
  /contracts      # predicate-catalog.yaml, *.schema.json, api.openapi.yaml
  /reference      # statin-model.md, build-status.md, guideline-sources.md, schema-reference.md, crc-model.archived.md
  /decisions      # ADRs
  /archive        # review-workflow.md, ingestion-dir/
  VERSIONS.md
  ISSUES.md
/scripts          # helper scripts (existing)
/diagrams         # visual artifacts (existing)
```

No subdirectories under `/api` — one service, flat file split by module. No `/api/contracts/` — contracts live in `/docs/contracts/` (the spec-pairing rule from ADR 0010). No top-level `/patients/` — patient JSONs co-locate with their expected traces under `/evals/statins/<case>/` so each fixture is self-contained.

### 6. Build order

Sequential gate:
1. Prune schema.md, patient-context.md, predicate-catalog.yaml to statins scope. **Done in this change.**
2. Author `docs/specs/eval-trace.md` + `docs/contracts/eval-trace.schema.json`. **Done in this change.**
3. Author `docs/contracts/api.openapi.yaml`. **Done in this change.**

Parallel tracks (implementation, handed to Claude Code):
- **A. Graph seed** (`/graph`). Inputs: `schema.md`, `statin-model.md`, `predicate-catalog.yaml`. Output: loadable Neo4j, constraint migrations, validator that enforces provenance completeness and predicate-name resolution.
- **B. API** (`/api`). Inputs: `eval-trace.schema.json`, `patient-context.schema.json`, `predicate-catalog.yaml`, `api.openapi.yaml`. Output: FastAPI service implementing `/evaluate`, `/nodes`, `/nodes/{id}/neighbors`, `/search`. Trace emission is primary.
- **C. UI** (`/ui`). Inputs: `api.openapi.yaml`, `eval-trace.schema.json`, `ui.md`. Output: Next.js app, two tabs, one shared graph-render component. Can scaffold against a mocked API using the schemas while B is in flight.
- **D. Patients** (`/evals/statins`). Inputs: `patient-context.schema.json`, `statin-model.md`. Five fixtures. **Done in this change.**

Integration: run the 5 patients through the implemented evaluator, capture actual traces into `expected-trace.json` as goldens, wire UI to real API.

## Alternatives considered

- **Keep the review workflow.** Rejected for v0: not on the critical path for the four deliverables; adds UI surface that does not help validate the eval loop.
- **Keep `/ingestion` scaffolding.** Rejected for v0: one hand-authored guideline does not justify a pipeline. Re-creating the directory when a second guideline lands is trivial; ADR 0003 still holds for that future work.
- **Delete archived content.** Rejected: CRC model and fixtures represent real design exploration. Archiving keeps them accessible without polluting the active build surface. Git history alone is harder to find.

## Consequences

- Anyone loading `CLAUDE.md` for this project sees a smaller, more focused surface. Stale references (review tool, ingestion pipeline, CRC scope) are gone from the active tree.
- Claude Code can be assigned Tracks A/B/C/D in parallel with the contracts as the shared interface. C can begin against mocks as soon as the OpenAPI + trace schema land.
- Re-expanding scope requires a new ADR (e.g., "0015 — add ADA T2DM") that reinstates the relevant predicates, patient-context fields, and reference docs. The archived CRC content is a template for what that looks like.

## Related

- `docs/decisions/0013-statins-v0-guideline.md` — guideline choice.
- `docs/specs/eval-trace.md` — trace contract (new).
- `docs/contracts/api.openapi.yaml` — API contract (new).
- `docs/specs/ui.md` — UI spec (new, replaces `review-workflow.md`).
