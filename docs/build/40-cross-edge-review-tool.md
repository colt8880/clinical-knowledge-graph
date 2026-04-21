# 40: Cross-guideline edge review tool

**Status**: pending
**Depends on**: v1 shipped
**Components touched**: docs / scripts
**Branch**: `feat/cross-edge-review-tool`

## Context

15 cross-guideline edges (9 PREEMPTED_BY, 6 MODIFIES) were removed from the graph in v1 after LLM-authored modeling errors were found — e.g., a preemption between recs with non-overlapping age ranges. The edges need clinician sign-off before re-addition, but there's no structured process for that review.

This feature builds the review artifact: a structured document (or spreadsheet) presenting each proposed edge with source and target Rec eligibility criteria side by side, so a clinician can validate overlap, classify the interaction, and sign off with rationale.

## Required reading

- `docs/ISSUES.md` — "Cross-guideline edges removed" section
- `docs/decisions/0018-preemption-precedence.md` — PREEMPTED_BY semantics
- `docs/decisions/0019-modifies-edge-semantics.md` — MODIFIES semantics
- `docs/specs/schema.md` — edge type definitions
- `docs/reference/guidelines/statins.md`, `cholesterol.md`, `kdigo-ckd.md` — the three guidelines whose interactions are being reviewed

## Scope

- `docs/review/cross-edges.md` — NEW. Structured review document with one section per proposed edge. Each section includes:
  - Source Rec: ID, guideline, eligibility criteria, evidence grade
  - Target Rec: ID, guideline, eligibility criteria, evidence grade
  - Proposed interaction type: PREEMPTED_BY or MODIFIES (with `nature`)
  - Eligibility overlap analysis: can the same patient match both recs? What age/condition/risk ranges overlap?
  - Clinician verdict: approve / reject / modify (blank, to be filled)
  - Rationale (blank, to be filled)
- `docs/review/README.md` — NEW. Instructions for the clinician reviewer: what each field means, how to fill in the verdict, what "overlapping eligibility" means concretely.
- `scripts/generate-edge-review.py` — NEW. Script that queries the graph (or reads the seed files + guideline docs) and generates the review document with pre-populated source/target Rec details. The clinician doesn't need to look up eligibility criteria manually.

## Constraints

- The review document must be completable without reading code or Cypher. Eligibility criteria rendered as plain English, not predicate DSL.
- Each proposed edge maps 1:1 to the edges that were removed (git history of `cross-edges-uspstf-accaha.cypher` and `cross-edges-kdigo.cypher`). Don't invent new edges — review the ones that existed.
- The document is a living artifact: after clinician review, it becomes the provenance record for why each edge was accepted or rejected.

## Verification targets

- `docs/review/cross-edges.md` contains exactly 15 edge review sections (9 PREEMPTED_BY + 6 MODIFIES).
- Each section has source Rec, target Rec, eligibility criteria for both, proposed interaction type, and blank verdict/rationale fields.
- `scripts/generate-edge-review.py` runs without errors and produces the document.

## Definition of done

- Review document generated and committed.
- README with clinician instructions committed.
- Script committed and documented.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Clinician actually completing the review. This feature builds the tool; F41 uses the results.
- UI-based review workflow. A markdown document is sufficient for 15 edges. If the edge count grows (v2+ guidelines), revisit.
- Proposing new edges beyond the 15 that were removed.
