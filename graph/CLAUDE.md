# /graph

Neo4j Community schema + seed for the v0 statin model.

## Load before working here

1. `../docs/specs/schema.md` — authoritative node/edge spec
2. `../docs/reference/schema-reference.md` — quick-reference tables
3. `../docs/reference/guidelines/statins.md` — the concrete model being seeded
4. `../docs/decisions/0001-neo4j-community-for-v0.md`
5. `../docs/decisions/0002-fhir-aligned-clinical-entities.md`
6. `../docs/decisions/0014-v0-scope-and-structure.md`

## Scope

- Cypher schema: constraints + indexes for `Guideline`, `Recommendation`, `Strategy`, and the FHIR-aligned entity labels (`Condition`, `Observation`, `Medication`, `Procedure`).
- `seeds/statins.cypher` — loads the full statin model per `docs/reference/guidelines/statins.md`. Per-guideline seed files live under `seeds/` (ADR 0016).
- Provenance stamped on every node and edge (guideline id, version, section, publication date).

## Not in scope (v0)

- Predicate evaluation — `/api`.
- Ingestion — archived until LLM-assisted drafting lands.
- Multi-guideline content. v0 ships `guideline:uspstf-statin-2022` only.
- PHI of any kind.

## Build conventions

- `seeds/statins.cypher` is idempotent (uses `MERGE` throughout). Re-running against a populated DB is a no-op.
- Every node / edge carries `provenance { guideline, version, section, publication_date }`.
- Human-legible labels on every edge; an opaque-id-only path is a bug.
- Schema changes update `docs/specs/schema.md` and `docs/reference/schema-reference.md` in the same commit.

## Definition of done

Seed is done when:

1. `seeds/statins.cypher` applies cleanly against a fresh Neo4j instance.
2. The resulting graph exactly matches `docs/reference/guidelines/statins.md` (node count, edge count, spot-checked attributes).
3. Backlog row in `docs/reference/build-status.md` updated.
4. The API `/evaluate` endpoint passes all fixtures against this seed.
