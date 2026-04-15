# 0003. LLM-assisted ingestion with mandatory clinician sign-off

Status: Accepted
Date: 2026-04-14

## Context

Guidelines are long prose documents with tables, caveats, footnotes, and cross-references. Fully manual extraction is slow and inconsistent. Fully automated LLM extraction produces plausible-looking but subtly wrong structure (wrong age cutoffs, dropped exclusions, conflated recommendations). The graph's value proposition is determinism grounded in evidence, so structural errors directly undermine the premise.

## Decision

Ingestion is a two-phase pipeline: an LLM produces a draft structured representation (nodes, edges, predicates) with full provenance (prompt, model version, guideline source, section anchor), and a named clinician reviewer must sign off before the draft merges to the production graph. No auto-merge. Every node and edge records the reviewer identity and review date.

## Alternatives considered

- **Fully manual ingestion.** Rejected: scaling to 20+ guideline domains is infeasible.
- **Fully automated ingestion with post-hoc audits.** Rejected: errors compound and the audit burden exceeds the review burden.
- **LLM-assisted without structured provenance.** Rejected: when a node is wrong, we need to trace back to the exact prompt, model, and source section.

## Consequences

- Every node and edge carries: prompt id, model version, guideline source+version+section, reviewer id, review date, review status.
- The review tool (ADR 0004) is a critical path component, not a nice-to-have.
- A separate staging graph or branch is needed; the production graph only sees signed-off content.

## Related

- `docs/specs/schema.md` (provenance fields)
- `docs/specs/review-workflow.md`
- ADR 0004
