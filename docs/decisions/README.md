# Architectural Decision Records

Each ADR captures a single decision: what was decided, why, what was considered, and the consequences. ADRs are append-only. If a decision is reversed, add a new ADR that supersedes the old one (link both directions); do not edit the superseded one.

## Status values

- **Proposed** — under discussion
- **Accepted** — current position
- **Superseded by NNNN** — reversed; link to the successor
- **Deprecated** — no longer applies but not actively replaced

## Filename convention

`NNNN-short-kebab-title.md`, four-digit zero-padded sequence. Sequence never reuses numbers.

## Template

```markdown
# NNNN. Title

Status: Accepted | Proposed | Superseded by NNNN
Date: YYYY-MM-DD

## Context
What's the problem? What constraints apply?

## Decision
What did we decide?

## Alternatives considered
What else did we weigh, and why didn't we pick it?

## Consequences
What does this commit us to? What breaks if we change our minds?

## Related
- specs/files/issues
```

## When to write one

Write an ADR when:
- A design choice will shape future work in a non-obvious way
- A reasonable alternative was rejected and someone might re-litigate it
- A spec edit changes behavior people might build against

Do **not** write an ADR for:
- Code-level patterns (use comments or module docs)
- Choices that are obvious to anyone reading the spec
- Pure preference with no tradeoffs

## Index

| # | Title | Status |
|---|---|---|
| 0001 | Neo4j Community for v0 graph database | Accepted |
| 0002 | FHIR-aligned clinical entity layer | Accepted |
| 0003 | LLM-assisted ingestion with mandatory clinician sign-off | Accepted |
| 0004 | Next.js + Cytoscape.js for review tool | Accepted |
| 0005 | Internal REST API between agent and graph | Accepted |
| 0006 | CRC as the only v0 guideline domain | Superseded by 0013 |
| 0007 | Homegrown predicate DSL over CQL/FHIRPath | Accepted |
| 0008 | Pregnancy as a top-level structured record | Deferred in v0 (see 0014) |
| 0009 | Spec versioning via git tags, not inline versions | Accepted |
| 0010 | Machine contracts paired with prose specs | Accepted |
| 0013 | Statins (USPSTF 2022) replaces CRC as v0 guideline | Accepted |
| 0014 | v0 scope reduction, repo restructure, Python for /api | Accepted |
