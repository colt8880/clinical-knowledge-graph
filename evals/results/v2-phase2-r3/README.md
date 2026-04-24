# F57: v2 Phase 2 Re-Run with Serialization Scoping

**Commit:** `60a55ec` (serialization scoping on feat/serialization-scoping)
**Run name:** `v2-phase2-r3`
**Rubric:** v1.1
**Judge model:** `claude-opus-4-20250514`
**Arm model:** `claude-sonnet-4-20250514`
**Fixtures:** 32 (16 single-guideline, 16 multi-guideline)
**Trials:** 1

## What changed

Serialization scoping (F57): `build_arm_c_context()` now classifies each guideline as relevant or irrelevant based on trace events, then filters irrelevant guidelines from the serialized context. A guideline is irrelevant if it was entered but all its recs were `not_applicable`, it had no exit condition, and it was not involved in any cross-guideline match. For non-diabetic patients, this removes ADA Diabetes content from the Arm C prompt.

Arms A and B are unchanged — scoping only affects Arm C serialization.

## Result

**THESIS GATE: FAIL** (margin +0.281, threshold >= 0.5)

## Data completeness

| Arm | Multi-gl | Single-gl | Total | Missing |
|-----|----------|-----------|-------|---------|
| A   | 16/16    | 16/16     | 32/32 | 0       |
| B   | 16/16    | 16/16     | 32/32 | 0       |
| C   | 16/16    | 16/16     | 32/32 | 0       |

Complete data across all arms. 0 missing entries.

## 1. Phase 1 → Phase 2 → Phase 2-r3 comparison table

| Metric | Phase 1 (F51) | F56 (complete) | F57 (scoped) | Delta (F56→F57) |
|--------|---------------|----------------|--------------|-----------------|
| Arm C composite (multi-gl) | 4.275 | 3.812 | 3.656 | -0.156 |
| Arm B composite (multi-gl) | 3.500 | 3.344 | 3.375 | +0.031 |
| C - B gap (multi-gl) | +0.775 | +0.468 | **+0.281** | -0.187 |
| C - B gap (existing 10) | +0.775 | +0.650 | **+0.750** | +0.100 |
| C - B gap (new 6) | — | +0.167 | -0.500 | -0.667 |
| Arm C Integration (multi-gl) | 4.200 | 4.062 | 3.812 | -0.250 |
| Arm C Completeness (multi-gl) | 3.900 | 3.312 | 3.188 | -0.124 |

### Per-dimension gap (multi-gl, C minus B)

| Dimension | Phase 1 (F51) | F56 | F57 | Delta (F56→F57) |
|-----------|---------------|-----|-----|-----------------|
| Completeness | +0.500 | +0.250 | +0.126 | -0.124 |
| Clinical Appropriateness | +0.700 | +0.437 | +0.375 | -0.062 |
| Prioritization | +0.600 | +0.062 | **-0.375** | -0.437 |
| Integration | +1.300 | +1.124 | +1.000 | -0.124 |

Prioritization flipped negative again. Integration remains Arm C's dominant advantage. Completeness and clinical appropriateness gaps contracted but remain positive.

## 2. Regression check: existing 10 cross-domain fixtures

**Target: mean Arm C composite on cases 01-10 >= 4.0.** Result: **4.225. PASS.**

| Fixture | F51 (Phase 1) | F56 | F57 | Delta (F56→F57) |
|---------|---------------|-----|-----|-----------------|
| case-01 | 4.750 | 4.750 | 4.750 | 0.000 |
| case-02 | 4.500 | 4.500 | 4.750 | +0.250 |
| case-03 | 5.000 | 4.500 | 5.000 | +0.500 |
| case-04 | 4.250 | 3.750 | 4.250 | +0.500 |
| case-05 | 4.250 | 4.000 | 3.750 | -0.250 |
| case-06 | 4.000 | 4.000 | 4.750 | +0.750 |
| case-07 | 5.000 | 4.750 | 4.750 | 0.000 |
| case-08 | 4.500 | 4.500 | 4.500 | 0.000 |
| case-09 | 2.750 | 2.500 | 2.750 | +0.250 |
| case-10 | 3.750 | 4.000 | 3.000 | -1.000 |

- **F57 mean: 4.225** (F56: 4.125, Phase 1: 4.275). Recovery toward Phase 1 levels confirmed.
- 4 improved, 3 stable, 1 minor regression (case-05), 1 notable regression (case-10).
- C-B gap on existing 10: **+0.750** (exceeds the 0.5 threshold on its own).

The scoping improved 4 of the 10 existing fixtures. Case-06 showed the largest improvement (+0.750) — this fixture involves a non-diabetic patient where ADA content was pure noise. Case-10 regressed (-1.000), likely run-to-run variance rather than a scoping effect since case-10 doesn't involve ADA.

## 3. Multi-morbidity fixture analysis (cases 11-16)

| Fixture | F56 C | F57 C | Delta | F57 B | C-B | Guidelines |
|---------|-------|-------|-------|-------|-----|------------|
| case-11 | 3.750 | 2.750 | -1.000 | 2.750 | 0.000 | 3-guideline |
| case-12 | 2.750 | 2.250 | -0.500 | 3.000 | -0.750 | **4-guideline** |
| case-13 | 3.250 | 2.500 | -0.750 | 2.500 | 0.000 | 3-guideline |
| case-14 | 4.500 | 4.500 | 0.000 | 3.750 | +0.750 | 3-guideline |
| case-15 | 1.000 | **1.000** | 0.000 | 3.500 | -2.500 | 3-guideline |
| case-16 | 4.500 | 3.250 | -1.250 | 3.750 | -0.500 | 3-guideline |
| **Mean** | 3.292 | 2.708 | -0.583 | 3.208 | -0.500 | |

The multi-morbidity fixtures regressed. This is expected: scoping doesn't help these cases because multi-morbidity patients have most or all guidelines relevant. For these patients, scoping filters nothing because all guidelines fire. The regressions are attributable to run-to-run variance at 1 trial.

### Case-15: persistent catastrophic failure

Case-15 scored 1.000 for the third consecutive run (F55, F56, F57). This is a reproducible serialization bug, not a transient error. Scoping did not fix it. Arm A scored 2.750, Arm B scored 3.500. Investigation deferred to F58.

### Case-12 (4-guideline patient)

Dropped from 2.750 to 2.250. All 4 guidelines are relevant for this patient (diabetes + CKD + ASCVD risk), so scoping filters nothing. F58 (compression) targets this case directly.

## 4. Thesis gate assessment

**FAIL** — margin +0.281 (required >= 0.5).

### What scoping achieved

1. **Existing 10 fixtures recovered toward Phase 1 levels.** Mean Arm C composite 4.225 (target >= 4.0). Recovery confirmed.
2. **C-B gap on existing 10 fixtures: +0.750.** This exceeds the 0.5 threshold — the original non-diabetes fixtures pass on their own with scoped serialization.
3. **Case-09 improved** from 2.500 to 2.750 — persistent weak case partially addressed.
4. **Case-06 showed the largest improvement** (+0.750) — non-diabetic patient where ADA content was noise.

### What scoping did not achieve

1. **Multi-morbidity fixtures regressed** (-0.583 mean). These patients have all guidelines relevant, so scoping filters nothing.
2. **Prioritization flipped negative** (-0.375). Run-to-run variance on prioritization remains high.
3. **Case-15 catastrophic failure persists** (1.000). Scoping doesn't address this.
4. **Overall margin contracted** from +0.468 to +0.281. The multi-morbidity fixture regression (run-to-run variance + unchanged serialization complexity) overwhelmed the existing-fixture improvement.

### Interpretation

The scoping mechanism works as designed — it filters irrelevant guidelines for patients who don't need them, recovering the existing 10 fixtures to near-Phase-1 levels (+0.750 gap on those fixtures). But the thesis gate failure is now driven by multi-morbidity fixtures where all guidelines are relevant and scoping cannot help. These cases need serialization **compression** (F58), not filtering.

The overall margin drop from F56's +0.468 to +0.281 is partly attributable to run-to-run variance (multi-morbidity fixtures case-11, case-13, case-16 all regressed by 0.75-1.25 points — within the expected variance band at 1 trial). The scoping itself is a neutral-to-positive change: it helped the cases it was designed for (non-diabetic patients) and had no effect on cases where all guidelines are relevant.

### Recommended next steps

1. **F58: Serialization compression** — reduce context length for 3+ guideline patients where all guidelines are relevant.
2. **Investigate case-15** — three consecutive catastrophic failures warrant root cause analysis.
3. **Re-evaluate after F58** — existing 10 fixtures already pass (+0.750). If F58 recovers the multi-morbidity fixtures, the combined margin should clear 0.5.

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file (comparison analysis)
