# 41: Re-add clinician-validated cross-guideline edges

**Status**: pending
**Depends on**: 40 (review tool), clinician review completed
**Components touched**: graph / api / evals / docs
**Branch**: `feat/validated-cross-edges`

## Context

After F40 builds the review document and a clinician completes it, this feature takes the approved edges and adds them back to the graph seeds. Only edges with clinician sign-off are re-added; rejected edges are documented with rationale and stay removed.

This also updates fixtures and the evaluator to exercise the re-added edges, verifying that preemption and modification events appear correctly in traces.

## Required reading

- `docs/review/cross-edges.md` — completed clinician review (must be done before this feature starts)
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — empty stub to populate
- `graph/seeds/cross-edges-kdigo.cypher` — empty stub to populate
- `docs/build/25-preemption-uspstf-accaha.md` — original preemption feature (the evaluator code already handles these edges)
- `docs/build/26-modifies-edges-kdigo.md` — original MODIFIES feature

## Scope

- `graph/seeds/cross-edges-uspstf-accaha.cypher` — MODIFY. Add clinician-approved PREEMPTED_BY edges with provenance including reviewer ID and review date.
- `graph/seeds/cross-edges-kdigo.cypher` — MODIFY. Add clinician-approved MODIFIES edges with provenance.
- `docs/review/cross-edges.md` — MODIFY. Mark edges as "added to graph" or "rejected" with final status.
- `evals/fixtures/cross-domain/*/expected-trace.json` — MODIFY as needed. Cross-domain fixtures may now produce preemption_resolved or modifier_applied trace events.
- `evals/fixtures/cross-domain/*/expected-actions.json` — MODIFY as needed. Some expected actions may change if preemption removes a rec or modification adjusts intensity.
- `docs/reference/build-status.md` — update.

## Constraints

- Only edges explicitly approved by the clinician are added. No inference, no "probably fine."
- Each edge carries provenance: `reviewer`, `review_date`, `rationale` (from the review document).
- Seeds remain idempotent (MERGE).
- Existing single-guideline fixtures must still pass unchanged — cross-edges don't affect them.

## Verification targets

- `docker compose up --build` loads the graph with new edges. Edge count matches number of approved edges.
- Cross-domain fixtures produce preemption/modifier trace events where expected.
- Single-guideline fixtures (statins, cholesterol, kdigo) still pass all assertions.
- `cd evals && uv run pytest tests/ -v` — all tests pass.

## Definition of done

- Approved edges in seed files with clinician provenance.
- Review document updated with final status per edge.
- Fixtures updated for new trace events.
- All tests pass.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Running the eval harness to measure edge value. That's F44.
- Adding new edges beyond what was in the original 15. New edges require their own review cycle.
- Changing the evaluator's preemption/modification logic (already shipped in F25/F26).
