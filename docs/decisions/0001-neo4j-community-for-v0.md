# 0001. Neo4j Community for v0 graph database

Status: Accepted
Date: 2026-04-14 (backfilled from CLAUDE.md "Resolved design decisions")

## Context

v0 needs a graph database that clinicians can skim queries on, supports the ~10k-node scale expected at first expansion, and has adequate tooling for dev, review, and ops without standing up enterprise infrastructure.

## Decision

Neo4j Community Edition for v0. Cypher is the query language of record.

## Alternatives considered

- **Postgres + recursive CTEs.** Rejected: CRC and hereditary-syndrome preemption involve multi-hop traversals with conditional predicates; expressing those as CTEs is possible but harder for clinician reviewers to read.
- **TigerGraph / Memgraph / other commercial graph DBs.** Rejected for v0: licensing and ops overhead without a clear performance win at our scale.
- **In-memory graph (NetworkX / Cytoscape.js only).** Rejected: we want server-side traversal so multiple consumers (agent, review tool, eval harness) share a coherent view.

## Consequences

- The schema (`docs/specs/schema.md`) is expressed in Cypher and Neo4j-idiomatic constraints.
- Ingestion writes to Neo4j directly; the review tool queries via the REST API, never Cypher.
- Revisit if traversal latency under agent load becomes a problem, or if v2+ needs features (e.g., strong ACID across distributed nodes) that Community doesn't support.

## Related

- `docs/specs/schema.md`
- `docs/specs/api-primitives.md`
