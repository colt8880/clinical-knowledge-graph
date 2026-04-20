# 33: Arm C convergence serialization

**Status**: pending
**Depends on**: 22
**Components touched**: evals / docs
**Branch**: `feat/arm-c-convergence`

## Context

The v1 thesis — "graph context produces better clinical recommendations than flat RAG" — originally tested this via cross-guideline edges (PREEMPTED_BY, MODIFIES). Those edges were removed (see `docs/ISSUES.md`) pending clinician review: the LLM-authored edges contained modeling errors (e.g., preemption between recs with non-overlapping eligibility).

But the thesis doesn't require interaction edges. The graph already encodes structural information that flat RAG lacks: the **shared clinical entity layer** (F20). When multiple guidelines independently recommend actions targeting the same medications, conditions, or observations, the graph knows they converge — because they literally point at the same nodes. Flat RAG retrieves disconnected prose chunks and hopes the LLM notices the overlap.

This feature extends Arm C's serialization to surface that convergence explicitly: "Three guidelines independently recommend moderate-intensity statin therapy for this patient, via these pathways, with these evidence grades." The LLM no longer has to infer the connection — the graph hands it over as structured context.

## Required reading

- `evals/harness/serialization.py` — current Arm C serialization (trace summary + subgraph).
- `evals/harness/arms/graph_context.py` — Arm C prompt template.
- `evals/SPEC.md` — harness spec, frozen output shape.
- `docs/build/22-eval-harness-skeleton.md` — harness design.
- `docs/reference/guidelines/statins.md`, `cholesterol.md`, `kdigo-ckd.md` — the guidelines whose convergence we're surfacing.

## Scope

### Serialization

- `evals/harness/serialization.py` — **extend**. Add `serialize_convergence_summary(trace, subgraph_response)` that:
  1. Calls `GET /subgraph` to fetch the full graph structure (nodes + edges) for all guidelines the evaluator traversed.
  2. Identifies shared clinical entities: Medication, Condition, Observation, Procedure nodes that are targets of `INCLUDES_ACTION` edges from Strategies belonging to **two or more guidelines**.
  3. For each shared entity, collects: which Recs recommend it (via Strategy → Action chain), their guideline, evidence grade, and eligibility status from the trace.
  4. Builds a `convergence_summary` dict:
     ```
     {
       "shared_actions": [
         {
           "entity_id": "med:atorvastatin",
           "entity_label": "Atorvastatin",
           "entity_type": "Medication",
           "recommended_by": [
             {
               "rec_id": "rec:statin-initiate-grade-b",
               "guideline": "USPSTF 2022 Statin",
               "evidence_grade": "B",
               "status": "due",
               "via_strategy": "strategy:uspstf-moderate-intensity"
             },
             ...
           ],
           "guideline_count": 3,
           "convergence_type": "reinforcing"
         }
       ],
       "convergence_prose": "... natural language summary ..."
     }
     ```
  5. Generates `convergence_prose`: a human-readable paragraph summarising which actions multiple guidelines agree on, which are unique to one guideline, and any intensity/dosing differences.

- `evals/harness/serialization.py` — **extend** `build_arm_c_context()` to include `convergence_summary` in the output alongside existing `trace_summary` and `subgraph`.

### Prompt

- `evals/harness/arms/graph_context.py` — **extend** prompt template. Add a `### Cross-Guideline Convergence` section between `### Matched Recommendations` and `### Graph Structure`. Renders `convergence_prose` plus a summary table of shared actions. Instruction to the LLM: "Where multiple guidelines converge on the same therapeutic action, this represents independent clinical agreement that should strengthen your confidence in that recommendation."

### Docs

- `evals/SPEC.md` — **extend**. Document the new `convergence_summary` key in the Arm C frozen output shape.

### Tests

- `evals/tests/test_serialization.py` — **extend**. Add tests for `serialize_convergence_summary()`:
  - Given a trace where USPSTF, ACC/AHA, and KDIGO all emit recs targeting the same statin medications, the convergence summary lists those medications with all three guidelines.
  - Given a trace where only one guideline emits a rec for a given entity, that entity does NOT appear in shared_actions (it's not convergence).
  - Given an empty trace (no recs emitted), convergence summary is empty.
  - Convergence prose is non-empty when shared actions exist.

## Constraints

- **Deterministic.** Same trace + same graph = same convergence summary. No wall-clock, no RNG. The subgraph fetch is from the same graph version the evaluator ran against.
- **No new API endpoints.** Uses existing `GET /subgraph` to fetch the graph structure.
- **Additive only.** Existing `trace_summary` and `subgraph` keys are unchanged. `convergence_summary` is a new sibling key.
- **Cache invalidation.** New serialization changes the Arm C context hash, which invalidates cached arm outputs. This is correct — the whole point is that Arm C gets richer context.
- **Convergence requires ≥ 2 guidelines.** A shared entity targeted by only one guideline's strategies is not convergence. It must appear in the action chains of at least two different guidelines' matched Recs.

## Verification targets

- `cd evals && uv run pytest tests/test_serialization.py` — all tests pass.
- Manual: run Arm C on cross-domain case-04 (55M, HTN, CKD 3a). Inspect the serialized context. Verify `convergence_summary.shared_actions` includes statin medications with entries from USPSTF, ACC/AHA, and KDIGO.
- Manual: run Arm C on a single-guideline fixture (statins case-01). Verify `convergence_summary.shared_actions` is empty (only one guideline traversed).
- Manual: verify `convergence_prose` reads as a coherent paragraph a clinician could scan.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `evals/SPEC.md` updated with new output shape.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output (paste serialized context for case-04).
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- **Running the full harness or scoring.** That's F27.
- **UI rendering of convergence.** That's F30.
- **Eligibility comparison table.** Deferred — would require extracting predicate results per-rec from the trace, which is useful but not needed for the thesis test.
- **Conflicting convergence detection** (e.g., one guideline says high-intensity, another says moderate). Requires the removed cross-guideline edges to express. Mark as `convergence_type: "reinforcing"` for now; revisit when clinician-reviewed edges return.
- **Cross-guideline edges.** This feature works without them. When they return post-clinician-review, the serialization will naturally pick up preemption/modifier events too.
