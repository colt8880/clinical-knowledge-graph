# 43: Arm C serialization v2 (concise + intensity-aware)

**Status**: pending
**Depends on**: v1 shipped
**Components touched**: evals / docs
**Branch**: `feat/arm-c-serialization-v2`

## Context

v1's Arm C Completeness score was 3.50/5 — the weakest dimension. Two contributing factors:

1. **Context overload.** The convergence table lists every shared medication node individually (7 statins × 3 guidelines = 21 rows). The LLM likely skims rather than processing each row. A summary at the recommendation level would be more concise and actionable.

2. **Missing intensity context.** The graph knows about statin intensity classifications (moderate vs high) but the serialization doesn't surface them. The LLM recommends "statin therapy" without specifying the guideline-appropriate intensity.

This feature also improves the system prompt to instruct the LLM to be exhaustive.

## Required reading

- `evals/harness/serialization.py` — current Arm C context building
- `evals/harness/arms/graph_context.py` — Arm C prompt template
- `evals/harness/config.py` — system prompt
- `evals/results/v1-thesis/scorecard.md` — v1 results showing Completeness gap

## Scope

### Serialization improvements

- `evals/harness/serialization.py` — MODIFY.
  1. **Convergence summary v2.** Instead of listing every shared medication node, group by therapeutic class: "Moderate-intensity statin therapy: recommended by USPSTF (Grade C), ACC/AHA (COR I, LOE A), KDIGO (1A). Any of: atorvastatin, rosuvastatin, simvastatin, pravastatin, lovastatin, fluvastatin, pitavastatin." One row per convergence point, not one row per medication.
  2. **Intensity context.** When strategies reference medication nodes, include the strategy's intensity classification in the serialization: "strategy:accaha-statin-high-intensity → atorvastatin 40-80mg, rosuvastatin 20-40mg" vs "strategy:accaha-statin-moderate-intensity → atorvastatin 10-20mg, ...". Derive from Strategy labels and existing graph properties.

### Prompt improvements

- `evals/harness/config.py` — MODIFY. Update SYSTEM_PROMPT to add: "Be exhaustive — include every action supported by the provided clinical context, even if low priority. Do not omit actions because they seem minor."

- `evals/harness/arms/graph_context.py` — MODIFY. Update the Arm C prompt template convergence section to render the new grouped format instead of the per-entity table.

### Tests

- `evals/tests/test_serialization.py` — MODIFY. Add tests for grouped convergence output and intensity inclusion.

## Constraints

- Changes apply to Arm C only. Arm A and Arm B prompts/retrieval are not modified in this feature.
- The system prompt change applies to all arms (it's shared). This is intentional — improving the instruction should help all arms equally, so it doesn't unfairly advantage Arm C.
- Determinism constraint preserved: same trace + same graph = same serialized output.
- Cache invalidation: changes to the prompt and serialization change both the prompt hash and context hash, invalidating all cached arm outputs. This is correct.

## Verification targets

- `cd evals && uv run pytest tests/test_serialization.py -v` — all tests pass.
- Manual: run Arm C on `cross-domain/case-04`. Verify convergence section shows grouped therapeutic classes, not individual medication rows.
- Manual: verify intensity information appears in the subgraph summary.
- Manual: run Arm A on any fixture. Verify the system prompt now includes the exhaustiveness instruction.

## Definition of done

- All scope files modified.
- Tests pass.
- Convergence serialization is demonstrably more concise (fewer lines, same information).
- Intensity context present in serialized output.
- System prompt updated.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Changing the rubric or scoring criteria. Rubric is frozen.
- Changing Arm B's retrieval or prompt (that's F42).
- Running the full eval harness. That's F44.
- Adding dosing ranges to medication nodes in the graph (would require seed changes). Use Strategy labels for intensity classification.
