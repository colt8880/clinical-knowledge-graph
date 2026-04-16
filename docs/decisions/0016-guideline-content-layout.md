# 0016. Guideline content layout

Status: Accepted
Date: 2026-04-15

## Context

v0 ships one guideline (USPSTF 2022 statins). As the graph grows to 2, 5, 20+ guidelines, we need a convention for where guideline-specific content lives — seed data, eval fixtures, and reference docs — without polluting per-guideline forks of the codebase itself.

Two tensions:

1. Code (evaluator, predicate engine, UI) must stay guideline-agnostic. Forking `/api` or `/ui` per guideline would be a maintenance disaster.
2. Guideline content (Cypher seeds, fixtures, modeling docs) is data, not code. At 1000+ guidelines it does not belong in the repo at all. But for v0 through ~10 guidelines, the filesystem is the simplest store.

## Decision

**(a) Code stays guideline-agnostic.** `/api` and `/ui` never fork per guideline. The evaluator, predicate engine, and UI operate over any guideline in the graph.

**(b) Guideline content is an in-repo bootstrap for v0, migrating to an external content store at ~10-20 guidelines.** v0 uses flat per-guideline files:

- `/graph/seeds/<guideline>.cypher`
- `/evals/fixtures/<guideline>/NN.json`
- `/docs/reference/guidelines/<guideline>.md`

No per-guideline subdirectories at the top level of `/graph`, `/evals`, or `/docs/reference`. Flat namespace with naming convention carries the grouping.

## Alternatives considered

**Per-guideline top-level directories** (e.g., `/guidelines/statins/graph/`, `/guidelines/statins/evals/`). Rejected: splits guideline content from the code that loads it, adds a layer of indirection for no gain at v0 scale, and the directory tree stops scaling around 20 guidelines anyway.

**External content store from day one.** Rejected: premature for v0. We don't know the versioning or access patterns yet. Start in-repo, learn, then migrate.

**Subdirectories per guideline under each component** (e.g., `/graph/statins/seed.cypher`). Rejected: adds nesting without semantic benefit over the flat `seeds/<guideline>.cypher` convention.

## Consequences

- v0 moves `seed.cypher` to `graph/seeds/statins.cypher`, fixtures to `evals/fixtures/statins/`, and the statin model doc to `docs/reference/guidelines/statins.md`.
- A second guideline adds three files in the same locations with a different `<guideline>` slug.
- At ~10-20 guidelines, content moves to a dedicated store (database, S3, content API) with its own versioning. The repo retains only canonical test fixtures. A future ADR will define the migration trigger and target architecture; out of scope for v0.
- CI and scripts must reference the new paths.

## Related

- ADR 0013 — statins as v0 guideline
- ADR 0014 — v0 scope and repo structure
- `docs/reference/build-status.md` — backlog
