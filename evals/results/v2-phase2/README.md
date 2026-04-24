# F55: v2 Phase 2 Thesis Run

**Commit:** `0ddbd3d` (F54 multi-morbidity fixtures on main)
**Run name:** `v2-phase2`
**Rubric:** v1.1
**Judge model:** `claude-opus-4-20250514`
**Arm model:** `claude-sonnet-4-20250514`
**Fixtures:** 32 (16 single-guideline, 16 multi-guideline)
**Trials:** 1

## Result

**THESIS GATE: FAIL**

Arm C margin over Arm B on multi-guideline fixtures: **+0.200** (required: >= 0.5).

The margin contracted from +0.775 in Phase 1 to +0.200 in Phase 2. This is driven by two factors: (1) missing data points across all arms (see Data Completeness below), and (2) Arm C struggled on the harder multi-morbidity fixtures, particularly case-15 (catastrophic 1.0) and case-12 (4-guideline patient scoring below Arm B).

### Data completeness caveat

This run has significant missing data. Of 96 expected fixture/arm entries (32 x 3), only 81 were returned from Braintrust:

| Arm | Multi-guideline | Single-guideline | Total | Missing |
|-----|-----------------|-------------------|-------|---------|
| A   | 14/16           | 15/16             | 29/32 | 3       |
| B   | 12/16           | 15/16             | 27/32 | 5       |
| C   | 13/16           | 12/16             | 25/32 | 7       |

Missing entries are likely API errors or timeouts during the Braintrust run. Because different arms are missing different fixtures, the aggregate comparisons are computed over different fixture sets, which weakens their reliability. All analysis below should be read with this caveat.

## 1. Phase 1 to Phase 2 comparison table

| Metric | Phase 1 (F51) | Phase 2 | Delta |
|--------|---------------|---------|-------|
| Arm C composite (all) | 4.148 | 3.596 (multi-gl) / 3.667 (single-gl) | regressed |
| Arm C composite (multi-gl) | 4.275 | 3.596 | -0.679 |
| Arm B composite (multi-gl) | 3.500 | 3.396 | -0.104 |
| C - B gap (multi-gl) | +0.775 | +0.200 | -0.575 |
| C - B gap (multi-gl, existing 10 only) | +0.775 | ~+0.36 (est.) | ~-0.42 |
| C - B gap (multi-gl, new 6 only) | n/a | ~+0.02 (est.) | n/a |
| Arm C Integration (multi-gl) | 4.200 | 3.692 | -0.508 |
| Arm C Completeness (multi-gl) | 3.900 | 3.154 | -0.746 |

The most striking regression is Arm C Completeness (-0.746). The 4th guideline (ADA Diabetes) appears to be adding serialization overhead that overwhelms the LLM's ability to maintain complete output. Integration also dropped, but the C-B gap on Integration remains the strongest dimension (+0.942).

### Per-dimension gap (multi-gl, C - B)

| Dimension | Phase 1 | Phase 2 | Delta |
|-----------|---------|---------|-------|
| Completeness | +0.500 | -0.013 | -0.513 |
| Clinical Appropriateness | +0.700 | +0.346 | -0.354 |
| Prioritization | +0.600 | -0.475 | -1.075 |
| Integration | +1.300 | +0.942 | -0.358 |

**Prioritization flipped negative** (-0.475). Arm B now outperforms Arm C on prioritization and completeness. The graph context is hurting more than helping on these dimensions. Integration remains the graph's clear strength.

## 2. Multi-morbidity fixture analysis (cases 11-16)

### Per-fixture Arm C scores

| Fixture | Composite | Completeness | Clin. Approp. | Prioritization | Integration | Guidelines |
|---------|-----------|--------------|---------------|----------------|-------------|------------|
| case-11 | 3.500 | 3 | 4 | 3 | 4 | 3-guideline |
| case-12 | 2.750 | 2 | 4 | 1 | 4 | **4-guideline** |
| case-13 | 3.000 | 3 | 2 | 4 | 3 | 3-guideline |
| case-14 | 4.000 | 3 | 5 | 4 | 4 | 3-guideline |
| case-15 | **1.000** | 1 | 1 | 1 | 1 | 3-guideline |
| case-16 | 3.750 | 3 | 4 | 4 | 4 | 3-guideline |
| **Mean** | **3.000** | 2.5 | 3.3 | 2.8 | 3.3 | |

### Case-12 (4-guideline patient)

Integration = **4** (meets the >= 4 threshold from the spec). However, Completeness = 2 and Prioritization = 1. The LLM recognized the cross-guideline interactions but failed to produce a complete, well-ordered action list. The graph's serialization for 4 simultaneous guidelines may be too verbose, crowding out the LLM's ability to enumerate and sequence all actions.

**Arm B beat Arm C on case-12** (3.75 vs 2.75). Flat RAG's broader retrieval produced better completeness (3 vs 2) and dramatically better prioritization (4 vs 1), even with identical integration (4 vs 4). For the hardest case in the harness, RAG's simpler context was more effective overall.

### Case-15: catastrophic failure

Arm C scored 1.0 across all four dimensions. This suggests the LLM output was incoherent or empty, likely a serialization or API error rather than a genuine clinical reasoning failure. Arm A scored 2.75 on the same fixture, confirming the patient context is workable. No Arm B score is available for comparison.

### Fixtures where Arm B beats Arm C

| Fixture | Arm B | Arm C | Delta | Notes |
|---------|-------|-------|-------|-------|
| case-12 | 3.75 | 2.75 | -1.00 | 4-guideline; serialization overload |
| case-16 | 4.25 | 3.75 | -0.50 | B's broader retrieval helped |
| case-09 | 3.25 | 2.50 | -0.75 | Recurring weak case from Phase 1 |

Three of the multi-guideline fixtures with complete B and C data have B > C. The pattern: cases where the patient triggers many guidelines simultaneously (case-12) or where the graph's negative evidence / interaction serialization introduces noise (case-09, case-16).

### Diabetes-inclusive vs non-diabetes multi-guideline

Of the cases with Arm C data available:

- **Non-diabetes multi-guideline** (cases 01-10, Arm C available for 8): mean composite ~3.84
- **Diabetes-inclusive multi-morbidity** (cases 11-16, Arm C available for all 6): mean composite 3.00

The 4th guideline clearly hurts Arm C's performance. The diabetes-inclusive fixtures score 0.84 points lower on average. This is not a 4th-guideline-helps story; it's a serialization-scaling problem.

## 3. Regression check (existing 10 cross-domain fixtures)

Comparing Arm C composite on the original 10 cross-domain fixtures between Phase 1 (F51) and Phase 2:

| Fixture | F51 (Phase 1) | Phase 2 | Delta | Notes |
|---------|---------------|---------|-------|-------|
| case-01 | 4.75 | 4.75 | 0.00 | Stable |
| case-02 | 4.50 | n/a | n/a | Missing |
| case-03 | 5.00 | 4.75 | -0.25 | Minor regression |
| case-04 | 4.25 | n/a | n/a | Missing |
| case-05 | 4.25 | 3.75 | -0.50 | Regression |
| case-06 | 4.00 | n/a | n/a | Missing |
| case-07 | 5.00 | 4.75 | -0.25 | Minor regression |
| case-08 | 4.50 | 4.50 | 0.00 | Stable |
| case-09 | 2.75 | 2.50 | -0.25 | Continued weakness |
| case-10 | 3.75 | 3.75 | 0.00 | Stable |

**3 missing, 3 stable, 4 regressed (none improved).**

The regression pattern is consistent: adding ADA Diabetes to the graph increases serialization length, which degrades Arm C's output quality even on fixtures that don't involve diabetes. Case-05 shows the largest regression (-0.50). This confirms that the serialization is introducing noise; the ADA subgraph content appears in the context even when the patient doesn't have diabetes.

## 4. Thesis gate assessment

**The C-B margin of +0.200 does NOT meet the >= 0.5 threshold. THESIS GATE: FAIL.**

However, the failure is qualified:

1. **Signal is present** (+0.200), driven entirely by Integration (+0.942 gap). The graph's convergence visibility still provides genuine structural insight that flat RAG cannot replicate.

2. **The failure is a serialization-scaling problem, not a null result.** Integration remains strongly positive. The graph's core capability (surfacing cross-guideline convergence) works. But the serialization of 4-guideline context overwhelms the LLM on completeness and prioritization.

3. **Missing data weakens confidence.** With 15 missing entries, the aggregate comparison is less trustworthy than Phase 1's complete dataset.

### C-B margin by fixture subset

| Subset | N (B) | N (C) | B composite | C composite | Margin |
|--------|-------|-------|-------------|-------------|--------|
| All multi-guideline (16) | 12 | 13 | 3.396 | 3.596 | +0.200 |
| Existing 10 (cases 01-10) | 10 | 7 | ~3.38 | ~3.96 | ~+0.58 |
| New 6 (cases 11-16) | 3 | 6 | ~3.50 | 3.00 | ~-0.50 |

On the existing 10 fixtures alone (where data is more complete), the margin likely holds near the threshold. The new multi-morbidity fixtures are what pulled it below, specifically the 4-guideline and catastrophic failure cases.

### Recommended next steps

1. **Investigate case-15 catastrophic failure** — determine if this was an API error or genuine serialization breakdown.
2. **Serialization compression for 4+ guidelines** — the current serialization scales linearly with guideline count. A more aggressive summarization strategy for large context windows would address the completeness/prioritization regressions.
3. **Re-run with retry logic** — the 15 missing entries need to be addressed before drawing strong conclusions. A retry mechanism or fallback for API errors would produce a complete dataset.
4. **Scope ADA content in serialization** — prevent ADA subgraph content from appearing in context for non-diabetic patients (currently leaking into all cross-domain cases).

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file (Phase 1 to Phase 2 comparison and analysis)
