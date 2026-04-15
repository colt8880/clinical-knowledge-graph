# 0005. Internal REST API between consumers and graph

Status: Accepted
Date: 2026-04-14

## Context

The graph has two consumers: the agent (which traverses it to recommend actions for a patient) and the review tool (which reads nodes and edges for clinician review). Both need a bounded, reviewable interface. Exposing raw Cypher means any caller can read arbitrary data, recommendations become non-reproducible (no single code path for traversal), and the contract between producer and consumer is Cypher queries, which is too loose.

## Decision

A small internal REST API (FastAPI or equivalent) exposes a fixed set of traversal primitives. Neither the agent nor the review tool issues Cypher. External exposure, if needed later, wraps this API (e.g., via MCP).

## Alternatives considered

- **Direct Cypher from consumers.** Rejected above.
- **GraphQL.** Rejected for v0: nice for flexible client-driven queries but the set of traversal primitives we care about is small and determinism-critical; REST with named primitives keeps the contract tight.
- **gRPC.** Rejected: heavier tooling cost than the size of the call set warrants.

## Consequences

- Every new consumer need is a new API primitive, not a new query. This is good for determinism and evaluability.
- The API layer is the home for preemption resolution, cycle detection, and the evaluator that consumes the predicate DSL.
- If external parties ever need programmatic access, they get the MCP wrapper, not Cypher.

## Related

- `docs/specs/api-primitives.md`
- ADR 0007
