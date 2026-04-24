# 59: Compressed serialization quality fixes

**Status**: shipped
**Depends on**: 58
**Components touched**: evals / docs
**Branch**: `feat/compression-quality-fixes`

## Context

F58 proved compression works structurally — case-12 jumped +1.75 composite. But the C-B margin actually narrowed slightly (+0.281 → +0.234) because Completeness and Prioritization remain weak. Diagnosis:

1. **Key Action column uses `reason` instead of the clinical action.** The compressed recs table shows evaluator reasoning ("Patient eligible, no strategy satisfied") where it should show the strategy name ("Moderate-intensity statin therapy"). Arm B's RAG chunks surface actual guideline action text, so it wins on Completeness by telling the LLM *what to do*, not *why a rec fired*.

2. **No priority ordering.** Recs are listed in trace evaluation order (guideline traversal order), which is arbitrary. The graph has evidence grades, intent (secondary_prevention > primary_prevention > monitoring), and preemption status — all the data needed to rank actions — but none of it feeds into the serialization order. Arm B wins on Prioritization because RAG chunks often contain guideline language about clinical urgency.

3. **Strategy details fully omitted in compressed mode.** F58 dropped strategy details entirely to save tokens, but went too far — the LLM needs to know the specific therapy class even in compressed mode. A middle ground: one line per rec with the strategy name and top medication options, not one line per medication.

All three fixes are serialization-only changes. No rubric, judge, or arm model changes. Combined re-run after all three land.

## Required reading

- `evals/harness/serialization.py` — `render_compressed_matched_recs()`, `_render_compressed_prose()`, `build_arm_c_context()`
- `evals/harness/arms/graph_context.py` — `get_prompt()` template and how compressed format flows through
- `evals/results/v2-phase2-r4/README.md` — dimension-level analysis showing Completeness/Prioritization gaps
- `evals/rubric.md` — Completeness and Prioritization scoring criteria

## Scope

- `evals/harness/serialization.py` — Three changes:
  1. `render_compressed_matched_recs()`: Replace `reason` with strategy name in Key Action column. Requires looking up strategy names from `strategy_considered` events (same pattern as `serialize_convergence_summary`).
  2. `render_compressed_matched_recs()`: Sort recs by clinical priority before rendering. Priority order: preempted recs last, then by intent (`secondary_prevention` > `primary_prevention` > `treatment` > `monitoring`), then by evidence grade strength.
  3. `build_arm_c_context()`: In compressed mode, add a compact strategy summary to the context — one line per indicated rec showing the strategy name and top 3 medication/action options. Not the full per-action detail from the uncompressed format, but enough that the LLM can enumerate specific therapies.
- `evals/tests/test_serialization.py` — Tests for all three changes.
- `evals/results/v2-phase2-r5/` — NEW directory: re-run with fixes.
  - `scorecard.md`
  - `scorecard.json`
  - `README.md` — comparison to R4, Completeness/Prioritization analysis, case-12/case-15 tracking, thesis gate assessment.
- `docs/reference/build-status.md` — update row for F59.

## Design

### Fix 1: Key Action column

Current:
```
| USPSTF 2022 Statin | statin-initiate-grade-b | B | due | Patient eligible, no strategy satisfied |
```

After:
```
| USPSTF 2022 Statin | statin-initiate-grade-b | B | due | Moderate-intensity statin therapy |
```

Source: look up offered_strategies[0] in the strategy_names dict built from `strategy_considered` events. Fall back to `reason` if no strategy found.

### Fix 2: Priority ordering

Build a sort key per rec:

```python
INTENT_PRIORITY = {
    "secondary_prevention": 0,
    "primary_prevention": 1,
    "treatment": 2,
    "monitoring": 3,
}
```

Sort order: (is_preempted ASC, intent_priority ASC, evidence_grade_sort ASC). Preempted recs sink to the bottom. Within non-preempted, secondary prevention comes first, then primary, then treatment, then monitoring.

The intent comes from `recommendation_considered` events (required field per eval-trace schema). The preemption status comes from `preemption_resolved` events already tracked in `trace_summary["preemption_events"]`.

Add a "Priority" column (1, 2, 3...) to the compressed table so the ordering is explicit.

After:
```
| # | Guideline | Rec | Grade | Status | Key Action |
|---|-----------|-----|-------|--------|------------|
| 1 | ACC/AHA 2018 | accaha-statin-high-intensity | COR I, LOE A | due | High-intensity statin therapy |
| 2 | KDIGO 2024 | kdigo-ckd-monitoring | 1B | due | CKD monitoring protocol |
| 3 | ADA 2024 | ada-metformin-first-line | A | due | Metformin therapy |
| 4 | USPSTF 2022 | statin-initiate-grade-b | B | preempted | Moderate-intensity statin therapy |
```

### Fix 3: Compact strategy summary

Add a new section to the compressed context (after the recs table, before convergence):

```
### Key Therapies

1. **High-intensity statin therapy** (ACC/AHA 2018, COR I, LOE A): atorvastatin 40-80mg, rosuvastatin 20-40mg
2. **CKD monitoring protocol** (KDIGO 2024, 1B): eGFR, urine ACR
3. **Metformin therapy** (ADA 2024, A): metformin
```

Source: for each indicated rec, list strategy name + top 3 action_node_ids from `action_checked` events. This adds ~3-5 lines (vs ~20+ lines in the uncompressed strategy detail) while giving the LLM the specific action items it needs for Completeness.

Only rendered in compressed mode. Omits preempted recs (they're deprioritized in the table).

## Constraints

- **No rubric changes, no judge model changes, no arm model changes.**
- **Same fixtures.** The only variable is serialization improvements.
- **Compressed format only.** 1-2 guideline patients are unchanged.
- **Deterministic.** Same trace = same output.
- **Token budget:** The compact strategy summary must not bring the compressed format above 1000 tokens for the variable sections (recs table + strategy summary + prose). Convergence and interactions are unchanged and don't count toward this budget.
- **The re-run must use F56's retry logic.** Expect 0 missing entries.

## Verification targets

- Unit test: `render_compressed_matched_recs()` Key Action column shows strategy name, not reason.
- Unit test: `render_compressed_matched_recs()` with preempted rec sorts it to the bottom.
- Unit test: priority ordering respects intent hierarchy (secondary > primary > treatment > monitoring).
- Unit test: compact strategy summary lists strategy names with top action options.
- Unit test: compact strategy summary omits preempted recs.
- Unit test: 2-guideline trace is unchanged (no compression, no strategy summary).
- Unit test: deterministic — same trace produces identical output.
- `cd evals && uv run python -m pytest tests/test_serialization.py -v` — all pass.
- `cd evals && uv run python -m harness --all --run v2-phase2-r5` completes with 0 missing entries.
- Arm C Completeness (multi-guideline) >= 3.5 (was 3.188 in R4).
- Arm C Prioritization (multi-guideline) >= 4.0 (was 3.875 in R4).
- Case-12 Arm C composite >= 4.0 (hold the R4 gain).
- Thesis gate assessment stated. Target: C-B margin >= 0.5 on full 16-fixture multi-guideline set.

## Definition of done

- All three fixes implemented with unit tests.
- Full harness re-run completed with complete data.
- Scorecard committed to `evals/results/v2-phase2-r5/`.
- README documents Completeness/Prioritization improvement, case-12/case-15 tracking, and thesis gate status.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Dynamic token budgeting or truncation. This is structural improvement, not a budget cap.
- Changes to the uncompressed (1-2 guideline) format.
- Rubric changes, judge model changes, or arm model changes.
- Per-guideline serialization templates.
- Changing the evaluator API or trace schema. All data needed is already in the trace.
- Fixture-specific debugging (e.g., case-15's Clinical Appropriateness = 1). That's a different problem.
