# v2 Phase 2 Run 5: Compression Quality Fixes (F59)

**Commit:** `28942d6`
**Run name:** v2-phase2-r5
**Rubric:** v1.1
**Baseline:** v2-phase2-r4 (F58 compression)

## What changed

F59 applies three quality fixes to the compressed serialization format (3+ guideline patients):

1. **Key Action column uses strategy name** instead of evaluator reasoning. "Moderate-intensity statin therapy" replaces "Patient eligible, no strategy satisfied".
2. **Priority ordering** — recs sorted by (preempted last, intent hierarchy, evidence grade). Adds explicit `#` column.
3. **Compact strategy summary** — "Key Therapies" section with strategy name + top 3 action options per indicated rec. Omits preempted recs.

All three are serialization-only changes. No rubric, judge, or arm model changes.

## Thesis gate

**FAIL** — C-B margin = +0.344 (required >= 0.5)

| Metric | R4 (compression) | R5 (quality fixes) | Delta |
|--------|:---:|:---:|:---:|
| Arm B composite (multi-gl) | 3.469 | 3.375 | -0.094 |
| Arm C composite (multi-gl) | 3.703 | 3.719 | +0.016 |
| C-B margin | +0.234 | +0.344 | **+0.110** |

Margin improved from +0.234 to +0.344 (+0.110). The improvement came primarily from Arm B dropping (-0.094, run-to-run LLM variance) rather than Arm C improving. Arm C composite is essentially flat (+0.016).

## Dimension-level analysis (multi-guideline, 16 fixtures)

| Dimension | R4 Arm C | R5 Arm C | R5 Arm B | C-B gap (R5) | C-B gap (R4) | Delta |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Completeness | 3.188 | 3.125 | 3.188 | -0.063 | -0.062 | -0.001 |
| Clinical Appropriateness | 3.875 | 3.938 | 3.375 | **+0.563** | +0.187 | **+0.376** |
| Prioritization | 3.875 | 4.000 | 4.000 | 0.000 | -0.125 | **+0.125** |
| Integration | 3.875 | 3.812 | 2.938 | **+0.874** | +0.937 | -0.063 |

### Spec targets

| Target | R5 Value | Met? |
|--------|:---:|:---:|
| Arm C Completeness (multi-gl) >= 3.5 | 3.125 | **NO** |
| Arm C Prioritization (multi-gl) >= 4.0 | 4.000 | **YES** |
| Case-12 Arm C composite >= 4.0 | 4.250 | **YES** |
| C-B margin >= 0.5 | 0.344 | **NO** |

Prioritization met the target (4.000). Completeness missed (3.125 vs 3.5 target) — the strategy summary was not sufficient to close the gap with Arm B's RAG action detail.

### Dimension analysis

- **Completeness (-0.063 gap):** Unchanged from R4. The strategy summary added specific action options but didn't move the needle. Arm B's RAG chunks continue to surface action-level detail (dosing, specific medications) that the compressed format still lacks.
- **Clinical Appropriateness (+0.563 gap):** Significant improvement over R4 (+0.376). Priority ordering may help the LLM produce clinically coherent output by presenting the most important actions first.
- **Prioritization (0.000 gap):** Improved from -0.125 to parity. The explicit priority ordering (Fix 2) eliminated the Arm B advantage here.
- **Integration (+0.874 gap):** Arm C's structural advantage remains strong but slightly narrowed from R4 (+0.937). Normal variance.

## Case-12 deep-dive

4-guideline patient (ASCVD + T2DM + CKD + HTN).

| Dimension | R4 | R5 |
|-----------|:---:|:---:|
| Completeness | 3 | 3 |
| Clinical Appropriateness | 5 | 5 |
| Prioritization | 3 | 4 |
| Integration | 5 | 5 |
| **Composite** | **4.00** | **4.25** |

Spec target (>= 4.0) met. Prioritization improved 3 → 4, likely from the explicit priority ordering. Composite held and slightly improved.

## Case-15 deep-dive

3-guideline patient.

| Dimension | R4 | R5 |
|-----------|:---:|:---:|
| Completeness | 2 | 1 |
| Clinical Appropriateness | 1 | 1 |
| Prioritization | 2 | 1 |
| Integration | 2 | 1 |
| **Composite** | **1.75** | **1.00** |

Case-15 regressed from 1.75 back to 1.00 (all 1s). This patient continues to be a reproducible catastrophic failure for Arm C — it scored 1.0 in R1-R3, improved to 1.75 in R4, and regressed in R5. This is a fixture-specific issue (likely a context construction edge case), not a serialization quality problem.

## Multi-morbidity fixture analysis (cases 11-16)

| Case | R4 Arm C | R5 Arm C | Delta | Notes |
|------|:---:|:---:|:---:|-------|
| case-11 | 3.50 | 3.50 | 0.00 | Held |
| case-12 | 4.00 | **4.25** | **+0.25** | Prioritization improved |
| case-13 | 2.50 | 2.50 | 0.00 | Flat |
| case-14 | 4.50 | 4.00 | -0.50 | Regression (Clinical Approp or Integration) |
| case-15 | 1.75 | **1.00** | **-0.75** | Catastrophic regression |
| case-16 | 3.25 | 4.00 | **+0.75** | Strong improvement |
| **Mean** | **3.25** | **3.21** | **-0.04** | Flat |

Multi-morbidity mean essentially flat (3.25 → 3.21). Case-16 improved (+0.75), case-12 improved (+0.25), but case-14 (-0.50) and case-15 (-0.75) regressed.

## Thesis gate assessment

The 0.5-point margin is not met at +0.344. This is the best margin achieved across all runs, but it remains below threshold.

**What's working:** Integration (+0.874) and Clinical Appropriateness (+0.563) are strong Arm C advantages. The graph's cross-guideline edges and priority ordering reliably produce better guideline hierarchy reasoning than RAG.

**What's not:** Completeness is still slightly negative (-0.063). The compressed format — even with the strategy summary — doesn't surface enough action-level detail to match Arm B's RAG chunks. Prioritization reached parity but not advantage.

**Path to 0.5:** The margin needs +0.156 more. Options:
1. Fix case-15's catastrophic failure (would add ~0.047 to mean if it reached 2.5).
2. Improve Completeness by ~0.2 across the board (richer action detail in compressed format).
3. Accept that equal-weighted rubric dilutes Integration's structural advantage and consider dimension weighting.

## Files

- `scorecard.md` — full per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file
