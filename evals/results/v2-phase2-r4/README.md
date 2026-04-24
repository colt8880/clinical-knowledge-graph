# v2 Phase 2 Run 4: Serialization Compression (F58)

**Commit:** `e75047a`
**Run name:** v2-phase2-r4
**Rubric:** v1.1
**Baseline:** v2-phase2-r3 (F57 scoping-only)

## What changed

F58 adds tiered serialization compression. When 3+ relevant guidelines remain after F57 scoping, the Arm C prompt switches to a compressed format:

- **Rendered prose:** one line per guideline instead of multi-line trace walk
- **Matched recs:** markdown table instead of JSON array (~60% shorter)
- **Strategy details:** omitted (key action in recs table instead)
- **Convergence + interactions:** unchanged (already concise)

1-2 guideline patients continue using the full format.

## Thesis gate

**FAIL** — C-B margin = +0.234 (required >= 0.5)

| Metric | R3 (scoping) | R4 (scoping + compression) | Delta |
|--------|:---:|:---:|:---:|
| Arm B composite (multi-gl) | 3.375 | 3.469 | +0.094 |
| Arm C composite (multi-gl) | 3.656 | 3.703 | +0.047 |
| C-B margin | +0.281 | +0.234 | -0.047 |

Compression did not meaningfully move the margin. The C-B gap actually narrowed slightly because Arm B also improved (run-to-run LLM variance at temp 0 accounts for ~0.1-point swings).

## Multi-morbidity fixture analysis (cases 11-16)

These are the 3-4 guideline patients that compression specifically targets.

| Case | R3 Arm C | R4 Arm C | Delta | Notes |
|------|:---:|:---:|:---:|-------|
| case-11 | 2.75 | 3.50 | **+0.75** | 3-guideline; Integration 3→4 |
| case-12 | 2.25 | **4.00** | **+1.75** | 4-guideline; Compl 2→3, Prior 1→3, Integ 3→5 |
| case-13 | 2.50 | 2.50 | 0.00 | Flat; Clinical Appropriateness dropped 2→2 |
| case-14 | 4.50 | 4.50 | 0.00 | Already strong, held |
| case-15 | 1.00 | **1.75** | **+0.75** | Improved from catastrophic, still failing |
| case-16 | 3.25 | 3.25 | 0.00 | Flat |
| **Mean** | **2.71** | **3.25** | **+0.54** | |

Multi-morbidity mean improved from 2.71 → 3.25 (+0.54). Case-12 showed the strongest single-fixture gain in the entire run history (+1.75).

## Case-12 deep-dive

The 4-guideline patient (ASCVD + T2DM + CKD + HTN) was the poster child for the compression hypothesis. Results:

| Dimension | R3 | R4 | Target |
|-----------|:---:|:---:|:---:|
| Completeness | 2 | **3** | >=3 ✓ |
| Clinical Appropriateness | 3 | **5** | — |
| Prioritization | 1 | **3** | >=3 ✓ |
| Integration | 3 | **5** | — |
| **Composite** | **2.25** | **4.00** | — |

Both spec targets met. Compression freed enough context for the LLM to enumerate and sequence all the actions correctly.

## Case-15 deep-dive

Case-15 improved from the catastrophic 1.0 (all dimensions = 1) to 1.75:

| Dimension | R3 | R4 |
|-----------|:---:|:---:|
| Completeness | 1 | 2 |
| Clinical Appropriateness | 1 | 1 |
| Prioritization | 1 | 2 |
| Integration | 1 | 2 |

Composite 1.0 → 1.75. The spec target was "any improvement over 1.0" — met, but the clinical appropriateness score of 1 means the LLM is still producing contraindicated or wrong recommendations. This patient likely needs fixture-specific debugging rather than further serialization tuning.

## Dimension-level analysis (multi-guideline, 16 fixtures)

| Dimension | R3 Arm C | R4 Arm C | R4 Arm B | C-B gap |
|-----------|:---:|:---:|:---:|:---:|
| Completeness | 3.188 | 3.188 | 3.250 | -0.062 |
| Clinical Appropriateness | 3.875 | 3.875 | 3.688 | +0.187 |
| Prioritization | 3.750 | 3.875 | 4.000 | -0.125 |
| Integration | 3.812 | 3.875 | 2.938 | **+0.937** |

Integration remains Arm C's strongest dimension (+0.94 over Arm B). Completeness and Prioritization remain slight negatives — Arm B's RAG retrieval is finding action-level detail that the compressed format now omits.

## Thesis gate assessment

The 0.5-point margin target is not met at +0.234. Signal is real (consistent across runs) but modest. Decomposition:

- **Integration (+0.94):** Arm C's structural advantage. The graph's cross-guideline edges reliably produce better integration reasoning than RAG chunks. This dimension alone carries the thesis.
- **Completeness (-0.06):** Roughly tied. Compression improved multi-morbidity cases but the gain was offset by variance elsewhere.
- **Prioritization (-0.13):** Arm B slightly better. RAG chunks seem to provide actionable detail that helps with sequencing.
- **Clinical Appropriateness (+0.19):** Small Arm C edge from graph-informed accuracy.

The thesis lives or dies on whether Integration's 0.94-point advantage can compensate for Completeness/Prioritization weakness. Under the current equal-weighted rubric, it can't quite get there.

## Files

- `scorecard.md` — full per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file
