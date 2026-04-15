# 0004. Next.js + Cytoscape.js for review tool

Status: Accepted
Date: 2026-04-14

## Context

Reviewers need to traverse the graph visually, inspect provenance on nodes and edges, flag issues, and propose edits. The graph is moderately dense (hundreds of visible nodes at once in a busy domain view). Rendering performance, interaction ergonomics, and ecosystem familiarity all matter.

## Decision

Next.js for the web app, Cytoscape.js for graph rendering. Data flows through the internal REST API (ADR 0005); the review tool never queries Cypher directly.

## Alternatives considered

- **React Flow.** Rejected: excellent for workflow-style diagrams but performance degrades with hundreds of nodes and edges; our graph has real density.
- **vis-network / sigma.js.** Rejected: less mature React integration; fewer layout algorithms relevant to clinical hierarchies.
- **D3 from scratch.** Rejected: too much time spent on rendering plumbing vs. clinical functionality.

## Consequences

- Cytoscape's layout algorithms (COSE-Bilkent, concentric) are the default rendering toolkit.
- The review tool's data contract with the graph is the REST API, which means new review features that need new data require an API change, not a client-side Cypher edit.
- Mobile is out of scope; the tool is desktop-first.

## Related

- `docs/specs/review-workflow.md`
- `docs/specs/api-primitives.md`
- ADR 0005
