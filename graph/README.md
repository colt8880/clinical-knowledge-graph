# /graph

Neo4j schema + seed for the v0 USPSTF 2022 statin primary-prevention model.

## Files

- `constraints.cypher` — uniqueness constraints on `id` per node label. Idempotent (`CREATE CONSTRAINT IF NOT EXISTS`).
- `seeds/statins.cypher` — loads the full statin model per `docs/reference/guidelines/statins.md`. Fully idempotent (`MERGE` with `ON CREATE SET`); re-running against a populated DB is a no-op. Per-guideline seed files live under `seeds/` (ADR 0016).
- `CLAUDE.md` — working notes for Claude inside this directory.

Every node and edge carries `provenance_guideline`, `provenance_version`, `provenance_source_section`, and `provenance_publication_date`.

## Apply the schema and seed

Assumes the `ckg-neo4j` container is running and reachable on the default bolt port. Credentials: `neo4j` / `password123`.

```sh
docker exec -i ckg-neo4j cypher-shell -u neo4j -p password123 < graph/constraints.cypher
docker exec -i ckg-neo4j cypher-shell -u neo4j -p password123 < graph/seeds/statins.cypher
```

Run order matters: constraints first, seed second. The uniqueness constraints keep `MERGE` in the seed unambiguous across multiple runs.

## Verify the seed

```sh
# Node counts by label (expected: Guideline 1, Recommendation 3, Strategy 2,
# Medication 7, Condition 5, Observation 4, Procedure 1 — 23 total).
docker exec -i ckg-neo4j cypher-shell -u neo4j -p password123 \
  "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY label;"

# Edge counts by type (expected: FROM_GUIDELINE 3, OFFERS_STRATEGY 3,
# INCLUDES_ACTION 8 — 14 total).
docker exec -i ckg-neo4j cypher-shell -u neo4j -p password123 \
  "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY type;"
```

Re-running `seeds/statins.cypher` must leave both counts unchanged — that's the idempotency check.

## Notes

- `structured_eligibility` is stored as a JSON string on each `Recommendation`. Neo4j properties cannot hold nested maps; the predicate tree round-trips through JSON.
- `EXCLUDED_BY` / `TRIGGERED_BY` edges are defined in the schema but not materialized in v0. They're materialized views over `structured_eligibility`; the predicate evaluator in `/api` will regenerate them if/when traversal needs them.
- Edge naming follows `docs/specs/schema.md` (`FROM_GUIDELINE`, `OFFERS_STRATEGY`, `INCLUDES_ACTION`).
