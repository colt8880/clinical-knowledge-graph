# 45: Arm C serialization v2 (concise + intensity-aware)

**Status**: pending
**Depends on**: v1 shipped
**Components touched**: evals / docs
**Branch**: `feat/arm-c-serialization-v2`

## Context

Three thesis runs have identified serialization as the primary remaining lever for Arm C's advantage:

1. **v1 (F27):** Thesis PASS (C-B gap +0.593). Convergence visibility drove the win, but Completeness was Arm C's weakest dimension at 3.50/5 — the convergence table lists every shared medication node individually (7 statins × 3 guidelines = 21 rows), likely causing the LLM to skim.

2. **v2-edges (F42):** Thesis FAIL (gap +0.437). Adding curated preemption/modifier edges *hurt* scores. Integration gap dropped from +1.125 to +0.500; clinical_appropriateness flipped to -0.250. The MODIFIES edge on cross-domain/case-03 caused the LLM to under-recommend statin intensity. Preemption and modifier events are serialized as bare JSON dicts with no dedicated prompt section — they add noise rather than signal.

3. **v2-arm-b (F44):** Thesis FAIL (gap +0.200). Upgraded Arm B retrieval closed most of the gap. On the original 4 cross-domain fixtures the gap hit zero. Prioritization collapsed from +1.25 to +0.30; integration from +0.50 to +0.10. The remaining signal is thin and spread across all dimensions.

**Implication:** The serialization needs to (a) cut noise — especially the per-medication convergence table and the raw subgraph dump, (b) make preemption/modifier events legible or suppress them, and (c) add intensity context that Arm B's RAG chunks naturally surface but Arm C currently omits.

## Required reading

- `evals/harness/serialization.py` — current Arm C context building
- `evals/harness/arms/graph_context.py` — Arm C prompt template
- `evals/harness/config.py` — system prompt
- `evals/results/v1-thesis/scorecard.md` — v1 baseline
- `evals/results/v2-edges/README.md` — edge serialization regression analysis
- `evals/results/v2-arm-b/README.md` — Arm B upgrade impact analysis

## Scope

### Serialization improvements

- `evals/harness/serialization.py` — MODIFY.
  1. **Convergence summary v2.** Instead of listing every shared medication node, group by therapeutic class: "Moderate-intensity statin therapy: recommended by USPSTF (Grade C), ACC/AHA (COR I, LOE A), KDIGO (1A). Any of: atorvastatin, rosuvastatin, simvastatin, pravastatin, lovastatin, fluvastatin, pitavastatin." One row per convergence point, not one row per medication.
  2. **Intensity context.** When strategies reference medication nodes, include the strategy's intensity classification in the serialization: "strategy:accaha-statin-high-intensity → atorvastatin 40-80mg, rosuvastatin 20-40mg" vs "strategy:accaha-statin-moderate-intensity → atorvastatin 10-20mg, ...". Derive from Strategy labels and existing graph properties.
  3. **Preemption/modifier prose rendering.** Replace bare JSON dicts in `serialize_trace_summary` with prose sentences. Preemption: "ACC/AHA 2018 Cholesterol preempts USPSTF 2022 Statin for this patient — follow ACC/AHA high-intensity recommendation instead." Modifier: "KDIGO 2024 CKD modifies ACC/AHA statin intensity — consider dose reduction for eGFR < 30." If the events are empty, omit the section entirely rather than showing an empty list.

### Prompt template improvements

- `evals/harness/arms/graph_context.py` — MODIFY.
  1. Update convergence section to render the new grouped format instead of the per-entity table.
  2. Add a dedicated `### Cross-Guideline Interactions` section for preemption/modifier prose (between Matched Recommendations and Convergence). Only rendered when events exist.
  3. **Remove raw subgraph node/edge dump.** The bulleted list of every node and edge (lines 120-132) is a wall of text that duplicates what `rendered_prose` already covers more concisely. Remove the `{subgraph_summary}` section from the template; rely on `rendered_prose` only.

### System prompt improvement

- `evals/harness/config.py` — MODIFY. Update SYSTEM_PROMPT to add: "Be exhaustive — include every action supported by the provided clinical context, even if low priority. Do not omit actions because they seem minor."

### Tests

- `evals/tests/test_serialization.py` — MODIFY. Add tests for grouped convergence output, intensity inclusion, and preemption/modifier prose rendering.

## Constraints

- Changes apply to Arm C only. Arm A and Arm B prompts/retrieval are not modified in this feature.
- The system prompt change applies to all arms (it's shared). This is intentional — improving the instruction should help all arms equally, so it doesn't unfairly advantage Arm C.
- Determinism constraint preserved: same trace + same graph = same serialized output.
- Cache invalidation: changes to the prompt and serialization change both the prompt hash and context hash, invalidating all cached arm outputs. This is correct.

## Verification targets

- `cd evals && uv run pytest tests/test_serialization.py -v` — all tests pass.
- Manual: run Arm C on `cross-domain/case-04`. Verify convergence section shows grouped therapeutic classes, not individual medication rows.
- Manual: verify intensity information appears in the evaluation summary.
- Manual: verify preemption/modifier events render as prose (not JSON) when present, and the section is omitted when absent.
- Manual: verify the raw subgraph node/edge list is no longer in the prompt.
- Manual: run Arm A on any fixture. Verify the system prompt now includes the exhaustiveness instruction.

## Definition of done

- All scope files modified.
- Tests pass.
- Convergence serialization is demonstrably more concise (fewer lines, same information).
- Intensity context present in serialized output.
- Preemption/modifier events rendered as prose or omitted.
- Raw subgraph dump removed from prompt template.
- System prompt updated.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Changing the rubric or scoring criteria. Rubric is frozen.
- Changing Arm B's retrieval or prompt (shipped in F43).
- Running the full eval harness. That's F46.
- Adding dosing ranges to medication nodes in the graph (would require seed changes). Use Strategy labels for intensity classification.
