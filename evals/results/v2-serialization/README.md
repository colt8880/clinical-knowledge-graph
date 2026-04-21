# v2-serialization: Serialization v2 thesis run

**Run name:** v2-serial
**Rubric:** v1.1
**Judge runs:** 1
**Braintrust experiments:** `v2-serial-arm-a`, `v2-serial-arm-b`, `v2-serial-arm-c`

## What changed from v2-arm-b (F44)

F45 upgraded Arm C's serialization to grouped convergence by therapeutic class, added intensity-awareness to statin rendering, and injected an exhaustiveness instruction into the system prompt. The exhaustiveness prompt affects all three arms equally. Arm B retrieval is unchanged from F44 (section-level chunking + multi-query). Graph edges are unchanged from F42.

Same 22 fixtures (12 single-guideline, 10 multi-guideline), same rubric v1.1.

## Key questions

1. **Did the serialization and prompt changes improve Arm C Completeness?** Target: ≥ 4.0 (up from 3.50 in F44).
2. **Did the exhaustiveness prompt help all arms equally, or did Arm C benefit disproportionately?**

## Answers

1. **No.** Arm C Completeness on multi-guideline fixtures *dropped* from 3.500 to 3.400. Well below the 4.0 target.
2. **The prompt helped Arm B more than Arm C.** Arm B multi-guideline composite rose +0.200 (3.450 → 3.650), while Arm C rose only +0.125 (3.650 → 3.775). The gap actually narrowed from +0.200 to +0.125.

## Comparison table

| Metric | v1 (N=4) | F42 (edges, N=10) | F44 (better RAG, N=10) | F46 (+ serialization, N=10) | Delta (F46 vs F44) |
|--------|----------|--------------------|-----------------------|----------------------------|---------------------|
| Arm A composite (multi-gl) | 3.219 | 2.625 | 2.725 | 2.700 | -0.025 |
| Arm B composite (multi-gl) | 3.719 | 3.375 | 3.450 | 3.650 | +0.200 |
| Arm C composite (multi-gl) | 4.312 | 3.812 | 3.650 | 3.775 | +0.125 |
| C - B gap (multi-gl) | +0.593 | +0.437 | +0.200 | +0.125 | -0.075 |
| Arm C Completeness (multi-gl) | 3.750 | 3.500 | 3.500 | 3.400 | -0.100 |
| Thesis gate | PASS | FAIL | FAIL | FAIL | — |

### Per-dimension gap (multi-gl, C minus B)

| Dimension | v1 | F42 | F44 | F46 | Delta (F46 vs F44) |
|-----------|-----|------|------|------|---------------------|
| completeness | +0.000 | +0.250 | +0.200 | -0.200 | -0.400 |
| clinical_appropriateness | +0.250 | -0.250 | +0.200 | +0.200 | +0.000 |
| prioritization | +1.000 | +1.250 | +0.300 | +0.100 | -0.200 |
| integration | +1.125 | +0.500 | +0.100 | +0.400 | +0.300 |

## Thesis gate

**FAIL** (signal below threshold)

- Arm B multi-guideline composite: 3.650
- Arm C multi-guideline composite: 3.775
- Margin (C - B): 0.125
- Required: >= 0.5
- Classification: `thesis_signal_below_threshold`

## Interpretation

The serialization v2 changes (F45) did not improve Arm C's Completeness. Three observations:

1. **Completeness regressed.** Arm C multi-guideline Completeness dropped from 3.500 to 3.400, and the C-B Completeness gap flipped negative (-0.200). The concise grouped serialization may be losing detail that the judge scores as "completeness" — shorter context trades coverage for clarity.

2. **Integration improved.** The one bright spot: the C-B integration gap jumped from +0.100 to +0.400. Grouped convergence by therapeutic class does appear to help the LLM articulate cross-guideline agreement. But this alone can't overcome the Completeness and Prioritization regression.

3. **Exhaustiveness prompt helped Arm B more.** Arm B rose +0.200 across multi-guideline fixtures while Arm C rose only +0.125. The prompt may help Arm B by encouraging it to enumerate more items from its retrieved chunks, while Arm C — constrained by the graph's structured output — has less room to expand. This is a counterintuitive finding: the prompt that was intended to level-up all arms disproportionately boosted the baseline competitor.

**Bottom line:** Serialization v2 improved integration visibility but hurt completeness. The net effect is a smaller C-B gap than before. Combined with F44's finding that better RAG closed most of the original v1 gap, the graph's measurable advantage at this rubric granularity is now marginal (+0.125). The v2 combined run (F47) should still proceed — the three improvements (edges + better RAG + better serialization) may interact positively — but the expectation should be that the graph's primary value is in auditability and determinism rather than raw recommendation prose quality.

## Recommended next steps

- **F47 (combined run)** proceeds as planned. The combined effect may differ from the sum of parts.
- Consider whether the rubric adequately captures the graph's structural advantages (auditability, provenance traceability, deterministic reasoning).
- The completeness regression suggests the concise serialization may need to retain more clinical detail in the grouped convergence prose.

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file (comparison analysis)
