# 40: Cross-guideline interaction discovery and review tool

**Status**: pending
**Depends on**: v1 shipped
**Components touched**: scripts / docs
**Branch**: `feat/cross-edge-review-tool`

## Context

15 cross-guideline edges were removed in v1 after LLM-authored modeling errors — e.g., a preemption between recs whose age ranges don't overlap. The root cause: the edges were proposed without systematically checking whether two recs can actually co-match the same patient.

Rather than just reviewing the 15 known edges, this feature builds a **discovery tool** that identifies all Rec pairs across guidelines whose eligibility criteria overlap. This scales to any number of guidelines — when ADA Diabetes lands in v2 Phase 2, the same tool discovers ADA ↔ KDIGO and ADA ↔ ACC/AHA candidates automatically.

The tool does the mechanical work (parse predicates, compute overlap, classify candidates). The clinician does the clinical judgment (is this preemption, modification, or no interaction?).

## Required reading

- `docs/ISSUES.md` — "Cross-guideline edges removed" section
- `docs/decisions/0018-preemption-precedence.md` — PREEMPTED_BY semantics
- `docs/decisions/0019-modifies-edge-semantics.md` — MODIFIES semantics
- `docs/specs/schema.md` — edge type definitions
- `docs/specs/predicate-dsl.md` — predicate language used in `structured_eligibility`
- `graph/seeds/statins.cypher`, `cholesterol.cypher`, `kdigo-ckd.cypher` — Rec nodes with `structured_eligibility` JSON

## Scope

### Discovery script

- `scripts/discover-interactions.py` — NEW. The core tool. Given a running Neo4j instance (or seed files), it:

  1. **Loads all Recs across all guidelines.** For each Rec, parses `structured_eligibility` (JSON predicate tree), extracts the eligibility criteria: age range, required conditions, excluded conditions, required observations (lab thresholds), required medications.

  2. **Compares every cross-guideline Rec pair.** For each pair of Recs from different guidelines, computes eligibility overlap:
     - Age range intersection (e.g., Rec A: 40-75, Rec B: 18-75 → overlap: 40-75)
     - Condition compatibility (does Rec A require a condition Rec B excludes? → no overlap)
     - Shared therapeutic targets (do both Recs' strategies target the same medication/observation nodes via the shared entity layer? → convergence candidate)

  3. **Classifies each overlapping pair** into candidate interaction types:
     - **Convergence (same action):** Both recs' strategies include the same medication or observation nodes → potential PREEMPTED_BY (more specific rec preempts less specific) or reinforcing convergence (already handled by F33).
     - **Modification (different actions, same patient):** Recs target different therapeutic actions but can co-match → potential MODIFIES (one adjusts the other's intensity/approach).
     - **No interaction:** Recs can co-match but address unrelated clinical domains with no shared entities.

  4. **Generates the review document** with pre-populated details per candidate pair.

  The script takes flags:
  - `--from-graph` — queries a running Neo4j instance
  - `--from-seeds` — parses seed `.cypher` files directly (no Neo4j required)
  - `--guidelines statins,cholesterol,kdigo` — which guidelines to include (default: all)

### Review document

- `docs/review/interaction-candidates.md` — NEW. Generated output. One section per candidate pair with:
  - Source Rec: ID, guideline, evidence grade, eligibility (plain English)
  - Target Rec: ID, guideline, evidence grade, eligibility (plain English)
  - Overlap analysis: age range intersection, condition compatibility, shared therapeutic targets
  - Candidate interaction type: PREEMPTED_BY / MODIFIES / convergence-only / no interaction
  - Shared entities (if any): which medication/observation nodes both recs' strategies target
  - **Clinician verdict:** approve as PREEMPTED_BY / approve as MODIFIES / reject / convergence-only (blank, to be filled)
  - **Clinician rationale:** (blank, to be filled)

- `docs/review/README.md` — NEW. Instructions for the clinician reviewer: what each field means, decision criteria for preemption vs modification vs no-interaction, what "overlapping eligibility" means concretely, examples of each verdict type.

### Predicate parsing

- `scripts/predicate_parser.py` — NEW. Utility module that parses `structured_eligibility` JSON into a normalized representation suitable for overlap computation. Handles: `all_of`, `any_of`, `none_of`, `age_between`, `age_greater_than_or_equal`, `has_active_condition`, `most_recent_observation_value`, `has_medication_active`, `has_condition_history`. Returns a structured dict with `age_range`, `required_conditions`, `excluded_conditions`, `required_observations`, `required_medications`.

## Constraints

- The review document must be completable without reading code or Cypher. Eligibility criteria rendered as plain English.
- The tool must not propose interaction types as ground truth — it proposes candidates. The clinician decides.
- Overlap computation is conservative: if two predicates can't be mechanically compared (e.g., complex `any_of` nesting), flag the pair as "manual review needed" rather than silently skipping it.
- The tool must be re-runnable: when a new guideline is added (ADA in Phase 2), re-running the script discovers new cross-guideline candidates without losing existing clinician verdicts.

## Verification targets

- `python scripts/discover-interactions.py --from-seeds` runs without errors and produces `docs/review/interaction-candidates.md`.
- The document contains at least the 15 previously removed edges as candidate pairs (they should all be rediscovered).
- Each section has source Rec, target Rec, eligibility in plain English, overlap analysis, and blank verdict/rationale fields.
- Pairs where eligibility doesn't overlap (like the USPSTF Grade I ↔ ACC/AHA secondary prevention error) are flagged with "no eligibility overlap" in the analysis, making the reject decision obvious.
- Re-running the script with `--guidelines statins,cholesterol` produces only USPSTF ↔ ACC/AHA candidates (no KDIGO pairs).

## Definition of done

- Discovery script produces the review document.
- Predicate parser handles all predicate types in the current catalog.
- README with clinician instructions committed.
- All scripts committed and documented.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Clinician actually completing the review. This feature builds the tool; F41 uses the results.
- UI-based review workflow. Markdown is sufficient for the current scale (~15-30 candidates). Revisit when the graph has 5+ guidelines.
- LLM-assisted interaction classification. The tool does mechanical overlap analysis; the clinician does clinical judgment. An LLM step between them is a v2 Phase 3 candidate if the candidate count grows large.
- Automatically adding edges to the graph. The output is a review document, not a seed file.
