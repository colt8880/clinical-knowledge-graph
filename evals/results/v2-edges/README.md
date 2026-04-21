# v2-edges: Cross-guideline edge-value thesis run

**Run name:** v2-edges-final
**Rubric:** v1.1
**Judge runs:** 1
**Braintrust experiments:** `v2-edges-final-arm-a`, `v2-edges-final-arm-b`, `v2-edges-final-arm-c`

## What changed from v1

v1 ran with convergence visibility only (shared clinical entities, no cross-guideline edges). v2-edges adds 8 clinician-validated edges: 6 PREEMPTED_BY (ACC/AHA preempts USPSTF) and 2 MODIFIES (KDIGO intensity reduction on ACC/AHA high-intensity recs). The evaluator now produces `preemption_resolved` and `cross_guideline_match` trace events, which Arm C serializes into the LLM prompt.

Everything else is identical: same 16 fixtures, same rubric v1.1, same models, 1 trial.

## Key question

**Did curated cross-guideline edges improve Arm C's Integration score on multi-guideline fixtures?**

**Answer: No.** The margin narrowed and fell below the 0.5 threshold.

## v1 vs v2-edges comparison

| Metric | v1 (no edges) | v2-edges | Delta |
|--------|---------------|----------|-------|
| Arm C Integration (multi-gl) | 4.250 | 3.250 | -1.000 |
| Arm C composite (multi-gl) | 4.312 | 3.812 | -0.500 |
| C - B gap (multi-gl) | +0.593 | +0.437 | -0.156 |
| Arm B composite (multi-gl) | 3.719 | 3.375 | -0.344 |

### Per-dimension gap (multi-gl, C minus B)

| Dimension | v1 | v2-edges | Delta |
|-----------|-----|----------|-------|
| completeness | +0.000 | +0.250 | +0.250 |
| clinical_appropriateness | +0.250 | -0.250 | -0.500 |
| prioritization | +1.000 | +1.250 | +0.250 |
| integration | +1.125 | +0.500 | -0.625 |

## Thesis gate

**FAIL** (signal below threshold)

- Arm B multi-guideline composite: 3.375
- Arm C multi-guideline composite: 3.812
- Margin (C - B): 0.437
- Required: >= 0.5
- Classification: `thesis_signal_below_threshold`

## Interpretation

Curated edges did not improve scores and may have introduced noise. Three observations:

1. **Integration gap narrowed.** v1's +1.125 Integration gap (C over B) dropped to +0.500 in v2-edges. The graph's structural representation of cross-guideline conflict resolution did not translate into better LLM integration reasoning -- in fact, it may have distracted from the convergence signal that drove v1's advantage.

2. **Clinical appropriateness regressed.** v2-edges shows C at -0.250 vs B on clinical_appropriateness. In v1, C led by +0.250. cross-domain/case-03 is the anchor: Arm C scored 2.0 on clinical_appropriateness vs Arm B's 3.0. The MODIFIES edge (KDIGO intensity reduction) may have caused the LLM to under-recommend statin intensity.

3. **Run-to-run variance is a factor.** Both Arm B and Arm C dropped from v1 levels (B: 3.719 -> 3.375, C: 4.312 -> 3.812). This is expected with 1 trial and 4 multi-gl fixtures -- the signal is real but noisy.

**Bottom line:** Convergence visibility (v1) provides more consistent value than curated edges (v2). The edges add structural information about conflict resolution, but the current serialization of preemption and modifier events may introduce more complexity than signal. Convergence alone is sufficient; edges are documentation, not reasoning input -- at least with this serialization approach.

## Recommended next steps

- **F45 (serialization v2)** may recover the edge value by presenting preemption/modifier information more clearly to the LLM.
- **F43 (Arm B retrieval upgrade)** will provide a stronger RAG baseline, making the true graph advantage clearer.
- Consider a dedicated run that tests edge serialization independently of convergence to isolate the effect.

## Files

- `scorecard.md` -- full scorecard with per-fixture breakdowns
- `scorecard.json` -- machine-readable scorecard
- `README.md` -- this file (v1 comparison)
