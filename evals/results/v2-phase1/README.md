# v2 Phase 1 Combined Thesis Run

**Run name:** v2-phase1
**Rubric:** v1.1
**Judge runs:** 1
**Fixtures:** 22 (12 single-guideline, 10 multi-guideline)
**Braintrust experiments:** `v2-phase1-arm-a`, `v2-phase1-arm-b`, `v2-phase1-arm-c`

## What changed from isolation runs

This run combines all three Phase 1 improvements simultaneously:

| Component | Source | What's new |
|-----------|--------|------------|
| Cross-guideline edges | F41 | 8 validated edges: 6 PREEMPTED_BY, 2 MODIFIES |
| Arm B retrieval | F43 | Section-level chunking + multi-query retrieval |
| Arm C serialization | F45 | Grouped convergence by therapeutic class, intensity-aware statin rendering |
| System prompt | F45 | Exhaustiveness instruction (affects all arms) |

Same 22 fixtures as F44/F46 (12 single-guideline, 10 multi-guideline), same rubric v1.1.

## Key question

**Do the improvements compound or interfere?**

**Answer: Neither -- they roughly cancel out.** The combined margin (+0.175) is slightly better than F46 serialization alone (+0.125) but worse than F42 edges alone (+0.437) and F44 better RAG alone (+0.200). The improvements do not synergize.

## Full comparison table

| Metric | v1 (N=4) | F42 edges (N=4) | F44 better RAG (N=10) | F46 serial. (N=10) | F47 combined (N=10) |
|--------|----------|------------------|-----------------------|--------------------|---------------------|
| Arm A composite (multi-gl) | 3.219 | 3.125 | 2.725 | 2.700 | 2.625 |
| Arm B composite (multi-gl) | 3.719 | 3.375 | 3.450 | 3.650 | 3.625 |
| Arm C composite (multi-gl) | 4.312 | 3.812 | 3.650 | 3.775 | 3.800 |
| C - B gap (multi-gl) | **+0.593** | +0.437 | +0.200 | +0.125 | **+0.175** |
| Arm C Completeness (multi-gl) | 3.750 | 3.500 | 3.500 | 3.400 | 3.400 |
| Arm C Integration (multi-gl) | 4.250 | 3.250 | 2.600 | 3.300 | 3.300 |
| Thesis gate | **PASS** | FAIL | FAIL | FAIL | **FAIL** |

Note: v1 and F42 used the original 4 cross-domain fixtures; F44, F46, and F47 used the expanded 10 (F48). Absolute scores are not directly comparable across fixture-count changes, but the C-B gap is.

### Per-dimension gap (multi-gl, C minus B)

| Dimension | v1 | F42 | F44 | F46 | F47 | Delta (F47 vs F46) |
|-----------|-----|------|------|------|------|---------------------|
| completeness | +0.000 | +0.250 | +0.200 | -0.200 | -0.100 | +0.100 |
| clinical_appropriateness | +0.250 | -0.250 | +0.200 | +0.200 | +0.500 | +0.300 |
| prioritization | +1.000 | +1.250 | +0.300 | +0.100 | -0.100 | -0.200 |
| integration | +1.125 | +0.500 | +0.100 | +0.400 | +0.400 | +0.000 |

### Single-guideline comparison (informational)

| Metric | v1 (N=12) | F42 (N=12) | F44 (N=12) | F46 (N=12) | F47 (N=12) |
|--------|-----------|------------|------------|------------|------------|
| Arm B composite | 3.521 | 3.542 | 3.854 | 3.750 | 3.917 |
| Arm C composite | 4.000 | 4.083 | 4.042 | 3.792 | 3.812 |
| C - B gap | +0.479 | +0.541 | +0.188 | +0.042 | **-0.105** |

Arm C now *loses* to Arm B on single-guideline fixtures. This is a new finding: the combination of all improvements slightly hurts Arm C's single-guideline performance while the upgraded Arm B benefits from better retrieval.

## Thesis gate

**FAIL** (signal below threshold)

- Arm B multi-guideline composite: 3.625
- Arm C multi-guideline composite: 3.800
- Margin (C - B): 0.175
- Required: >= 0.5
- Classification: `thesis_signal_below_threshold`

## C - B gap trajectory

```
v1:          +0.593  ████████████  PASS
F42 (edges): +0.437  █████████     FAIL (close)
F44 (RAG):   +0.200  ████          FAIL
F46 (serial):+0.125  ███           FAIL
F47 (all):   +0.175  ████          FAIL
                      ─────┼──────
                     0    0.5    1.0
```

The gap has not recovered. Phase 1 improvements collectively produce a +0.175 margin -- better than F46 alone but far short of the 0.5 threshold.

## Interpretation

The three improvements do not compound. Five observations:

1. **Clinical appropriateness is the one bright spot.** The C-B gap on clinical_appropriateness jumped to +0.500 (up from +0.200 in F44/F46). The combination of curated edges + better serialization is helping Arm C produce more clinically appropriate recommendations. This is the only dimension where the combined run outperforms all isolation runs.

2. **Prioritization regressed.** The C-B prioritization gap flipped negative (-0.100) for the first time across all runs. In v1, Arm C's structural ordering produced a +1.000 advantage. With better RAG retrieval, Arm B now surfaces structured guideline sections (risk stratification tables, grade-specific recommendations) that give it ordering cues comparable to the graph.

3. **Completeness remains the weak spot.** Arm C Completeness (3.400) has been flat since F44. The concise grouped serialization trades coverage for clarity -- and the judge penalizes the lost detail.

4. **Single-guideline inversion.** For the first time, Arm C trails Arm B on single-guideline fixtures (3.812 vs 3.917). The graph's structured output may be constraining the LLM compared to Arm B's retrieved prose, which benefits from both section-level chunking and the exhaustiveness prompt.

5. **Integration holds at +0.400.** The convergence serialization continues to provide a consistent integration advantage, unchanged from F46. This is the graph's most durable signal -- but it alone cannot clear the 0.5 composite threshold.

**Bottom line:** v1's PASS was substantially driven by Arm B having weak retrieval rather than Arm C having a fundamental structural advantage. With production-quality RAG, the graph provides measurable but modest lift (+0.175 composite) concentrated in clinical appropriateness (+0.500) and integration (+0.400). The graph's primary value at this rubric granularity is in auditability, determinism, and provenance rather than raw recommendation quality.

## What this means for Phase 2

The v2 Phase 1 combined run confirms that the C-B gap has structurally narrowed. Phase 2 options:

1. **Accept the result.** The graph provides modest quality lift and strong structural advantages (auditability, provenance, determinism). Reframe the thesis around these structural properties rather than pure recommendation quality.

2. **ADA Diabetes subgraph (Phase 2).** Adding a 4th guideline increases cross-guideline complexity. If the graph's advantage scales with guideline count (more convergence opportunities, more preemption/modification), the gap may widen on harder fixtures.

3. **Rubric revision.** The current rubric measures recommendation prose quality. Adding dimensions for provenance, auditability, or clinical reasoning traceability could capture the graph's structural value that the current rubric misses.

4. **Deeper serialization investigation.** The completeness regression suggests the concise serialization is losing clinically relevant detail. A hybrid approach (concise convergence + full action lists) might recover completeness without losing integration.

## Files

- `scorecard.md` -- full scorecard with per-fixture breakdowns
- `scorecard.json` -- machine-readable scorecard
- `README.md` -- this file (full comparison analysis)
