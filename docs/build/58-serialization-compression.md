# 58: Serialization compression for multi-guideline patients

**Status**: pending
**Depends on**: 57
**Components touched**: evals / docs
**Branch**: `feat/serialization-compression`

## Context

F57 addresses context noise from irrelevant guidelines. This feature addresses context *length* when 3-4 guidelines are all relevant to the same patient. F55 showed that even after scoping, patients who legitimately trigger many guidelines get overwhelmed:

- Case-12 (4-guideline patient): Integration = 4 (good), Completeness = 2, Prioritization = 1 (bad). The LLM understood the interactions but couldn't enumerate and sequence all the actions.
- Case-15: Arm C scored 1.0 across all dimensions — likely a context-length-induced failure.
- Multi-morbidity mean composite: 3.00 (vs 3.84 for existing non-diabetes multi-guideline cases).

The current serialization scales linearly with guideline count. Each active guideline adds: rendered_prose lines, matched_recs JSON, strategy details, convergence entries, and interaction prose. For a 4-guideline patient, this produces a prompt that's 2-3x longer than a 2-guideline patient, without 2-3x more clinical signal.

This feature introduces tiered summarization: when 3+ guidelines are relevant, compress per-guideline detail and elevate cross-guideline synthesis.

## Required reading

- `evals/harness/serialization.py` — all serialize_* functions (especially `_render_subgraph_prose` and `_render_convergence_prose_v2`)
- `evals/harness/arms/graph_context.py` — prompt template (sections that scale with guideline count)
- `evals/results/v2-phase2-r3/scorecard.json` — post-scoping scores (dependency: F57 must ship first)
- `evals/rubric.md` — completeness and prioritization scoring criteria (the dimensions that suffer)

## Scope

- `evals/harness/serialization.py` — Add a compression pass that triggers when `len(relevant_guidelines) >= 3`. Produces a shorter serialization format that preserves cross-guideline signal while reducing per-guideline verbosity.
- `evals/harness/arms/graph_context.py` — Adjust the prompt template to handle the compressed format. The `{rendered_prose}` and `{matched_recs}` sections change shape when compressed.
- `evals/results/v2-phase2-r4/` — NEW directory: re-run with compression.
  - `scorecard.md`
  - `scorecard.json`
  - `README.md` — comparison to F57 (scoping-only baseline), multi-morbidity fixture analysis, case-12 and case-15 deep-dive, thesis gate assessment.
- `docs/reference/build-status.md` — update row for F58.

## Design

### Compression tiers

| Active guidelines | Format |
|-------------------|--------|
| 1-2 | Current full format (no change) |
| 3+ | Compressed format (this feature) |

### Compressed format changes

**1. Matched recs: table instead of JSON array.**

Replace the per-rec JSON blob with a markdown table:

```
| Guideline | Rec | Grade | Status | Key Action |
|-----------|-----|-------|--------|------------|
| USPSTF 2022 | Statin Grade B | B | indicated | Moderate-intensity statin |
| ACC/AHA 2018 | High-intensity statin | I/A | indicated | High-intensity statin |
| KDIGO 2024 | CKD monitoring | B | indicated | eGFR + urine ACR monitoring |
| ADA 2024 | Metformin first-line | A | indicated | Metformin |
```

This is ~60% shorter than the JSON while preserving the information the LLM needs for action enumeration.

**2. Rendered prose: one line per guideline instead of full trace walk.**

Replace the multi-line per-guideline trace walk with a single-sentence summary per guideline:

```
USPSTF 2022: 1 rec indicated (Grade B statin), ASCVD risk 12.4%.
ACC/AHA 2018: 1 rec indicated (high-intensity statin), preempts USPSTF.
KDIGO 2024: 2 recs indicated (monitoring + ACEi/ARB), modifies statin intensity to moderate.
ADA 2024: 2 recs indicated (metformin + SGLT2i), eGFR-dependent dosing.
```

**3. Strategy details: omitted in compressed mode.**

Per-strategy action lists are the biggest contributor to context length (7 statins x 3 guidelines = 21 action_checked lines). In compressed mode, the strategy section is replaced by the "Key Action" column in the recs table. Individual medication options are only listed in the convergence section where they matter.

**4. Convergence: unchanged.** The grouped therapeutic class format (from F45) is already concise. Keep it.

**5. Interactions: unchanged.** Preemption and modifier prose is already concise and high-signal. Keep it.

### Token budget estimate

| Section | Full (4 guidelines) | Compressed (4 guidelines) |
|---------|---------------------|---------------------------|
| Rendered prose | ~400 tokens | ~120 tokens |
| Matched recs | ~600 tokens | ~200 tokens |
| Strategy details | ~500 tokens | 0 tokens |
| Convergence | ~200 tokens | ~200 tokens |
| Interactions | ~150 tokens | ~150 tokens |
| **Total** | **~1850 tokens** | **~670 tokens** |

This ~60% reduction should free up context window for the LLM to produce a more complete, better-prioritized action list.

## Constraints

- **No rubric changes, no judge model changes, no arm model changes.**
- **Same fixtures.** The only variable is serialization compression.
- **Threshold is 3 guidelines, not configurable.** Hardcode for now — we only have 4 guidelines total. If a future phase adds a 5th, revisit.
- **Deterministic.** Same trace = same compressed output.
- **Must preserve all information needed for Integration scoring.** The LLM must still be able to articulate cross-guideline reasoning. Compression removes *format verbosity*, not *clinical content*.
- **The re-run must use F56's retry logic.** Expect 0 missing entries.

## Verification targets

- Unit test: `build_arm_c_context()` with a 2-guideline trace produces the full format.
- Unit test: `build_arm_c_context()` with a 4-guideline trace produces the compressed format with the markdown recs table and single-line prose.
- Unit test: compressed format preserves all recommendation IDs, evidence grades, statuses, and convergence data.
- Token count: the compressed Arm C prompt for case-12 (4 guidelines) is < 1500 tokens total context (measured via `anthropic.count_tokens` or rough estimation).
- `cd evals && uv run python -m harness --all --run v2-phase2-r4` completes with 0 missing entries.
- Multi-morbidity fixture analysis: case-12 Arm C Completeness >= 3, Prioritization >= 3 (both were 2 and 1 in F55).
- Case-15: Arm C composite > 1.0 (any improvement over the catastrophic failure).
- Thesis gate assessment stated. Target: C-B margin >= 0.5 on full 16-fixture multi-guideline set.

## Definition of done

- Compression logic implemented with unit tests.
- Full harness re-run completed with complete data.
- Scorecard committed to `evals/results/v2-phase2-r4/`.
- README documents multi-morbidity improvement, case-12/case-15 deep-dive, and thesis gate status.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Dynamic token budgeting (hard cap + truncation). The tiered format is a structural solution, not a truncation solution.
- Changing the evaluator API to produce a compressed trace.
- Per-guideline serialization templates (one format per guideline). The compression is generic.
- Rubric changes or judge model changes.
- Arm B changes (Arm B's RAG is unchanged throughout this sequence).
