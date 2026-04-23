# 53: ADA cross-guideline edges

**Status**: pending
**Depends on**: 52 + clinician review
**Components touched**: graph / docs / evals
**Branch**: `feat/ada-cross-edges`

## Context

F52 adds the ADA Diabetes subgraph as a standalone guideline. This feature connects it to the existing three guidelines via clinician-reviewed cross-guideline edges. ADA creates the richest interaction surface in the graph:

- **ADA ↔ KDIGO:** SGLT2 inhibitors for cardiorenal benefit (convergence). Metformin dose adjustment at low eGFR (modification). This is the canonical cross-guideline modifier example.
- **ADA ↔ ACC/AHA:** Statin for diabetic patients (convergence — both recommend moderate-intensity, ACC/AHA adds risk-based high-intensity). ADA's CVD risk reduction recs (SGLT2i, GLP-1 RA) complement ACC/AHA's statin therapy.
- **ADA ↔ USPSTF:** Indirect — USPSTF statin recs are already preempted by ACC/AHA for diabetic patients (P1, P2 from F41). ADA reinforces the ACC/AHA preemption but doesn't create new direct edges to USPSTF.

The interaction discovery tool (`scripts/discover-interactions.py`) generates the candidate list. A clinician reviews each pair, classifies as PREEMPTED_BY / MODIFIES / convergence-only / reject, and signs off with rationale. Only approved edges are added to the graph.

## Required reading

- `docs/review/cross-edges.md` — existing clinician review format and decisions
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — edge pattern for PREEMPTED_BY
- `graph/seeds/cross-edges-kdigo.cypher` — edge pattern for MODIFIES
- `docs/decisions/0017-preemption-precedence.md` — preemption semantics
- `docs/decisions/0018-modifies-semantics.md` — MODIFIES semantics
- `docs/build/52-ada-diabetes-subgraph.md` — the subgraph being connected
- `scripts/discover-interactions.py` — interaction candidate generator

## Scope

### New files

- `graph/seeds/cross-edges-ada.cypher` — clinician-approved ADA cross-guideline edges. MERGE pattern with reviewer provenance.
- `docs/review/cross-edges-ada.md` — clinician review document for ADA interaction candidates. Records each pair's verdict, rationale, and reviewer.

### Modified files

- `docs/review/interaction-candidates.md` — updated by running `discover-interactions.py --from-seeds` after ADA seed is loaded.
- `scripts/seed.sh` — add `cross-edges-ada.cypher` to load order (after all guideline seeds).
- `docs/reference/build-status.md` — update F53 row.

## Expected interactions

Based on ADA's scope (subject to clinician review — these are hypotheses, not pre-approved):

### Likely convergence (shared entity layer, no explicit edge)

| ADA Rec | Other Rec | Shared action | Notes |
|---------|-----------|---------------|-------|
| R5 (statin for diabetes) | ACC/AHA R3 (diabetes statin benefit) | Moderate-intensity statin | Near-identical eligibility. Shared entity layer deduplicates. |
| R2 (SGLT2i for cardiorenal) | KDIGO R2 (SGLT2i for CKD) | SGLT2 inhibitor | Both recommend SGLT2i for overlapping populations. Convergence signal. |

### Likely MODIFIES

| Source | Target | Nature | Rationale |
|--------|--------|--------|-----------|
| KDIGO R2 (SGLT2i for CKD) | ADA R4 (intensification) | agent_preference | When a patient has CKD + uncontrolled diabetes, KDIGO's independent SGLT2i recommendation changes the intensification calculus — SGLT2i should be preferred over DPP-4i or sulfonylurea. |
| KDIGO R1 (CKD monitoring) | ADA R1 (metformin first-line) | dose_adjustment | eGFR < 45 requires metformin dose reduction; eGFR < 30 contraindicates. KDIGO monitoring informs ADA dosing. |

### Likely no new PREEMPTED_BY

ADA doesn't directly preempt other guidelines — it's complementary. The statin overlap with ACC/AHA is convergence, not preemption (both recommend the same thing for the same population). USPSTF preemption is already handled by existing ACC/AHA edges.

## Constraints

- **Clinician review is mandatory.** Run `discover-interactions.py`, generate candidates, have a clinician review before adding any edge. No LLM-authored edges.
- **Edge pattern matches existing cross-edge seeds.** Every edge carries `note`, `reviewer`, `review_date`, `provenance_source`, `provenance_date`. MODIFIES edges also carry `nature`.
- **No new edge types.** Only PREEMPTED_BY and MODIFIES. If an interaction doesn't fit either, it's convergence-only (handled by shared entity layer) or not an interaction.
- **Idempotent MERGEs.** Same pattern as existing cross-edge seeds.
- **API evaluator handles new edges without code changes.** The multi-guideline evaluator from F21 already processes PREEMPTED_BY and MODIFIES generically.

## Verification targets

- `scripts/discover-interactions.py --from-seeds` runs clean with ADA seed included. Updated `interaction-candidates.md` includes ADA pairs.
- Clinician review document (`cross-edges-ada.md`) records a verdict for every candidate pair.
- `cypher-shell < graph/seeds/cross-edges-ada.cypher` runs clean.
- Edge counts: `MATCH ()-[r:PREEMPTED_BY|MODIFIES]->(:Recommendation:ADA) RETURN count(r)` and `MATCH (:Recommendation:ADA)-[r:PREEMPTED_BY|MODIFIES]->() RETURN count(r)` return expected counts per the review document.
- `cd api && uv run pytest` — all existing tests pass (no regressions).
- API `/evaluate` handles ADA recs correctly when cross-edges are present (spot-check with a multi-guideline fixture from F54 if available, otherwise manual curl test).

## Definition of done

- Interaction candidates generated and reviewed by clinician.
- All approved edges added to `cross-edges-ada.cypher` with provenance.
- Review document committed to `docs/review/cross-edges-ada.md`.
- All existing tests pass.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- New fixtures (F54).
- Changes to the ADA subgraph itself (amend F52 if issues found).
- Changes to the evaluator's preemption/modification logic.
- ACC/AHA ↔ ADA PREEMPTED_BY edges (convergence is sufficient — they agree).
- USPSTF ↔ ADA direct edges (already handled via ACC/AHA intermediary).
