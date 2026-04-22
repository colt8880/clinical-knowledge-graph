# F51: F50 Scoring Leverage Thesis Run

**Commit:** `e7bc1aa` (F49 + F50 changes on main)
**Run name:** `v2-f50`
**Rubric:** v1.1
**Judge model:** `claude-opus-4-20250514`
**Arm model:** `claude-sonnet-4-20250514`
**Fixtures:** 22 (12 single-guideline, 10 multi-guideline)
**Trials:** 1

## Result

**THESIS GATE: PASS**

Arm C margin over Arm B on multi-guideline fixtures: **+0.775** (required: >= 0.5).

The combined F49 (satisfied strategies + interaction reasoning) and F50 (negative evidence surfacing + completeness licensing + extended integration schema) changes pushed Arm C past the thesis gate threshold. F50's projected improvement of +0.225 to +0.325 on the margin was exceeded — actual margin delta from F47 was **+0.600**.

## 1. Comparison table (F47 baseline -> F51)

| Metric | F47 (v2-phase1) | F51 (v2-f50) | Delta |
|--------|-----------------|--------------|-------|
| Arm C composite (all) | 3.807 | 4.148 | +0.341 |
| Arm C composite (multi-gl) | 3.800 | 4.275 | +0.475 |
| Arm B composite (multi-gl) | 3.625 | 3.500 | -0.125 |
| C - B gap (multi-gl) | +0.175 | +0.775 | +0.600 |
| Arm C Completeness (multi-gl) | 3.400 | 3.900 | +0.500 |
| Arm C Integration (multi-gl) | 3.300 | 4.200 | +0.900 |
| Arm C Clinical Approp. (multi-gl) | 4.300 | 4.300 | +0.000 |
| Arm C Prioritization (multi-gl) | 4.200 | 4.700 | +0.500 |

The margin improvement (+0.600) came from two sources: Arm C improved by +0.475 composite, and Arm B drifted down by -0.125 (expected run-to-run variance at 1 trial). All four dimensions now show positive C-B gaps. Integration is the dominant driver (+1.300 gap).

## 2. Per-fixture delta analysis (multi-guideline, Arm C composite)

| Fixture | F47 | F51 | Delta | Notes |
|---------|-----|-----|-------|-------|
| case-01 | 4.750 | 4.750 | 0.000 | Stable — already at ceiling |
| case-02 | 3.750 | 4.500 | +0.750 | Large gain |
| case-03 | 4.250 | 5.000 | +0.750 | Hit ceiling |
| case-04 | 4.250 | 4.250 | 0.000 | Stable |
| case-05 | 3.500 | 4.250 | +0.750 | Large gain (integration ≤3 target) |
| case-06 | 3.000 | 4.000 | +1.000 | Largest gain (integration ≤3 target) |
| case-07 | 4.500 | 5.000 | +0.500 | Hit ceiling (completeness licensing target) |
| case-08 | 4.000 | 4.500 | +0.500 | Strong gain |
| case-09 | 3.000 | 2.750 | -0.250 | Only regression — see below |
| case-10 | 3.000 | 3.750 | +0.750 | Large gain (negative evidence target) |

**8 of 10 improved or held, 1 declined.**

### Integration ≤ 3 targets (cases 04, 05, 06, 09, 10)

These had Integration scores ≤ 3 in F47 — the extended output schema was designed to help here.

| Fixture | F47 Integration | F51 Integration | Delta |
|---------|-----------------|-----------------|-------|
| case-04 | 3.0 | 5.0 | +2.0 |
| case-05 | 2.0 | 3.0 | +1.0 |
| case-06 | 2.0 | 4.0 | +2.0 |
| case-09 | 2.0 | 3.0 | +1.0 |
| case-10 | 2.0 | 3.0 | +1.0 |

All five improved on Integration. The extended output schema (cross-guideline interaction table with convergence/conflict reasoning) had a clear positive effect. Mean Integration improvement: +1.4.

### Negative evidence targets (cases 09, 10)

These are the fixtures designed to probe whether surfacing "what didn't fire" improves scores.

- **case-10**: +0.750 composite, Integration 2→3. Negative evidence surfacing appears to have helped the LLM contextualize why certain guidelines applied and others didn't.
- **case-09**: -0.250 composite (the only regression). Integration improved 2→3, but Clinical Appropriateness dropped 3→2. The negative evidence may have introduced noise that the LLM misinterpreted. This is the one fixture where the changes hurt.

### Completeness licensing targets (cases 07, 09)

Instruction #4 (licensing the LLM to add lifestyle/non-graph actions) was aimed here.

- **case-07**: +0.500 composite, hit perfect 5.0. Completeness licensing succeeded — the LLM added relevant non-graph actions.
- **case-09**: -0.250. No completeness improvement (stayed at 3). Licensing didn't help on this harder case.

## 3. Thesis gate assessment

**The C-B margin of +0.775 crosses the 0.5 threshold. THESIS GATE: PASS.**

The graph-context arm (Arm C) now outperforms flat RAG (Arm B) by a meaningful margin on multi-guideline fixtures. The result is driven by:

1. **Integration** (+1.300 gap, up from +0.400): The extended cross-guideline output schema forces explicit interaction reasoning that flat RAG cannot replicate.
2. **Prioritization** (+0.600 gap, up from -0.100): Satisfied strategy tracking and interaction-aware ordering produce better clinical sequencing.
3. **Clinical Appropriateness** (+0.700 gap, up from +0.500): Maintained and slightly improved.
4. **Completeness** (+0.500 gap, up from -0.100): Flipped from negative to positive. The completeness licensing instruction and negative evidence surfacing together helped Arm C cover more expected actions.

### Remaining weakness

Case-09 is the only regression and the only fixture where Arm C (2.750) scored below Arm B (3.000). The negative evidence surfacing introduced noise on this complex case. A targeted investigation of case-09's Arm C output would inform whether this is a serialization issue or a fundamental difficulty for the graph approach on this patient profile.

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file (F47 → F51 comparison and analysis)
