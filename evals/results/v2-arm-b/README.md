# v2-arm-b: Arm B retrieval upgrade thesis run

**Run name:** v2-arm-b
**Rubric:** v1.1
**Judge runs:** 1
**Braintrust experiments:** `v2-arm-b-arm-a`, `v2-arm-b-arm-b`, `v2-arm-b-arm-c`

## What changed from v2-edges

v2-edges ran with naive paragraph-level chunking and single-query retrieval for Arm B. v2-arm-b upgrades Arm B to section-level chunking + multi-query retrieval (F43), while keeping Arm C serialization unchanged from v1. The only variable vs v2-edges is Arm B's retrieval quality.

Fixture set expanded from 16 to 22 (F48 added 6 cross-domain cases), so multi-guideline N = 10 vs 4 in prior runs. Comparisons on the original 4 cross-domain fixtures are noted separately.

## Key question

**How much of Arm C's advantage was due to Arm B being weak?**

**Answer: Most of it.** On the original 4 cross-domain fixtures, the C-B gap dropped to zero. On the full 10 multi-guideline fixtures, it narrowed to +0.20 — well below the 0.5 threshold.

## Comparison table

| Metric | v1 (naive RAG, N=4) | F42 (edges, N=4) | F44 (better RAG, N=10) | Delta (F44 vs F42) |
|--------|---------------------|-------------------|------------------------|---------------------|
| Arm B composite (multi-gl) | 3.719 | 3.375 | 3.450 | +0.075 |
| Arm C composite (multi-gl) | 4.312 | 3.812 | 3.650 | -0.162 |
| C - B gap (multi-gl) | +0.593 | +0.437 | +0.200 | -0.237 |
| Thesis gate | PASS | FAIL | FAIL | — |

### Original 4 cross-domain fixtures (apples-to-apples)

| Fixture | v2-edges Arm B | v2-arm-b Arm B | v2-edges Arm C | v2-arm-b Arm C |
|---------|----------------|----------------|----------------|----------------|
| cross-domain/case-01 | 4.250 | 4.500 | 4.000 | 4.750 |
| cross-domain/case-02 | 2.750 | 3.500 | 4.000 | 3.250 |
| cross-domain/case-03 | 3.250 | 2.750 | 2.750 | 2.750 |
| cross-domain/case-04 | 3.250 | 4.500 | 4.500 | 4.500 |
| **Mean** | **3.375** | **3.813** | **3.812** | **3.813** |
| **C - B gap** | | **+0.437** | | **0.000** |

On the original 4 fixtures, Arm B rose +0.438 while Arm C stayed flat. The gap closed completely.

### Per-dimension gap (multi-gl, C minus B)

| Dimension | v1 | v2-edges | v2-arm-b | Delta (v2-arm-b vs v2-edges) |
|-----------|-----|----------|----------|------------------------------|
| completeness | +0.000 | +0.250 | +0.200 | -0.050 |
| clinical_appropriateness | +0.250 | -0.250 | +0.200 | +0.450 |
| prioritization | +1.000 | +1.250 | +0.300 | -0.950 |
| integration | +1.125 | +0.500 | +0.100 | -0.400 |

## Thesis gate

**FAIL** (signal below threshold)

- Arm B multi-guideline composite: 3.450
- Arm C multi-guideline composite: 3.650
- Margin (C - B): 0.200
- Required: >= 0.5
- Classification: `thesis_signal_below_threshold`

## Interpretation

The upgraded Arm B retrieval closed most of the gap with Arm C. Three observations:

1. **Prioritization gap collapsed.** v1's +1.000 and v2-edges' +1.250 prioritization advantage for Arm C dropped to +0.300 in v2-arm-b. Section-level chunking gives Arm B access to structured guideline sections (risk stratification tables, grade-specific recommendations) that previously only Arm C's graph traversal surfaced. This was the primary driver of v1's thesis PASS.

2. **Integration gap nearly closed.** v1's +1.125 integration advantage dropped to +0.100. Multi-query retrieval lets Arm B pull chunks from multiple guidelines per patient, providing cross-guideline coverage that was previously Arm C's unique strength. The remaining 0.1-point gap suggests convergence serialization still adds marginal value, but not enough to clear the 0.5 threshold.

3. **Arm B rose; Arm C held.** On the original 4 fixtures, Arm B jumped from 3.375 to 3.813 while Arm C stayed at 3.812. The v1 result was partly a function of weak retrieval, not structural graph advantage. Arm C's absolute quality didn't degrade — it just lost its relative edge.

**Bottom line:** A significant portion of v1's thesis PASS was driven by Arm B having weak retrieval rather than Arm C having structural advantage. With production-quality RAG, the graph's convergence signal provides only marginal lift (+0.20). Serialization improvements (F45) may recover some signal, but the expectation should be modest: the graph's value may be in auditability and determinism rather than raw recommendation quality as measured by this rubric.

## Recommended next steps

- **F45 (serialization v2)** should focus on making cross-guideline convergence *concise and actionable* rather than verbose — the current serialization may be adding noise.
- The v2 combined run (F47) will show whether improved serialization + better RAG + curated edges together clear the threshold.
- Consider whether the rubric itself adequately captures the graph's structural advantages (auditability, provenance, determinism) or only measures recommendation prose quality.

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file (comparison analysis)
