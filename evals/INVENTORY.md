# Evals — Inventory

Top-level inventory. Fixtures live in `evals/fixtures/<domain>/<id>/`. See `evals/SPEC.md` for spec.

## Statins (v0)

### Landed

| ID | Directory | Coverage |
|---|---|---|
| 01 | `fixtures/statins/01-high-risk-55m-smoker/` | 55M smoker, HTN, supplied ASCVD 18.2%. Grade B happy path. |
| 02 | `fixtures/statins/02-borderline-55f-sdm/` | 55F on lisinopril, supplied ASCVD 8.4%. Grade C band; both SDM and moderate-intensity strategies offered. |
| 03 | `fixtures/statins/03-too-young-35m/` | 35M smoker, HTN. Age-below-range exit fires before risk lookup. |
| 04 | `fixtures/statins/04-grade-i-78f/` | 78F HTN + T2DM. Age >= 76 Grade I band. |
| 05 | `fixtures/statins/05-prior-mi-62m/` | 62M post-MI on atorvastatin. Secondary-prevention exit, no Rec emitted. |

### Deferred (tracked in `docs/ISSUES.md`)

- Boundary ages: 39 vs 40, 75 vs 76.
- Patient missing lipid panel: `most_recent_observation_value` returns `unknown`; need semantics before authoring.
- Live ASCVD calculation fixture once the PCE implementation lands. v0 fixtures all supply the score.
- Statin intolerance / contraindications once the structured signal exists.

## Cholesterol (v1 — ACC/AHA 2018)

### Landed

| ID | Directory | Coverage |
|---|---|---|
| 01 | `fixtures/cholesterol/case-01/` | 42F, LDL 230, no ASCVD, no diabetes. Severe hypercholesterolemia (R2): high-intensity statin. |
| 02 | `fixtures/cholesterol/case-02/` | 58M post-MI, LDL 115, on simvastatin. Secondary prevention (R1): upgrade to high-intensity. |
| 03 | `fixtures/cholesterol/case-03/` | 55M diabetes, HTN, LDL 145, ASCVD risk 9.2%. Diabetes statin benefit group (R3): moderate-intensity (high-intensity reasonable). |
| 04 | `fixtures/cholesterol/case-04/` | 48M, LDL 162, no diabetes, ASCVD risk 6.1%. Below R4 threshold (<7.5%): no ACC/AHA rec fires. |

### Deferred

- Cross-domain fixtures (cholesterol + USPSTF overlap) land in F25.
- Adults >75 with ASCVD (moderate-intensity consideration).
- Statin-intolerant patient with LDL ≥190.

## KDIGO CKD (v1 — KDIGO 2024)

### Landed

| ID | Directory | Coverage |
|---|---|---|
| 01 | `fixtures/kdigo/case-01/` | 63M, CKD 3a (eGFR 52), albuminuria A1 (ACR 22), no diabetes. Monitoring (R1) + statin-for-CKD (R3) only. |
| 02 | `fixtures/kdigo/case-02/` | 68M, CKD 3b (eGFR 38), albuminuria A3 (ACR 520), T2DM + HTN. All four Recs fire. |
| 03 | `fixtures/kdigo/case-03/` | 71M, CKD 4 (eGFR 22), albuminuria A2 (ACR 85), T2DM + HTN. All four Recs fire. Near SGLT2/dialysis eGFR boundaries. |

### Deferred

- Cross-domain fixtures (CKD modifies statin intensity) land in F26.
- Dialysis patients (eGFR < 15 / G5D).
- CKD + diabetes deep integration.

## Cross-domain (v1 — preemption + modification)

### Landed

| ID | Directory | Coverage |
|---|---|---|
| 01 | `fixtures/cross-domain/case-01/` | 62M post-MI (ASCVD), on simvastatin. USPSTF exits (secondary prevention). ACC/AHA R1 matches. No preemption fires. |
| 02 | `fixtures/cross-domain/case-02/` | 55M, HTN, LDL 165, ASCVD risk 8.5%. Both USPSTF Grade C and ACC/AHA R4 match. ACC/AHA preempts USPSTF (priority 200 > 100). |
| 03 | `fixtures/cross-domain/case-03/` | 65M post-MI, CKD 3b (eGFR 35), ACR 180. USPSTF exits. ACC/AHA R1 (secondary prevention) fires. KDIGO statin-for-CKD MODIFIES ACC/AHA R1 intensity to moderate. |
| 04 | `fixtures/cross-domain/case-04/` | 55M, HTN, CKD 3a (eGFR 52), LDL 145, ASCVD risk 8.5%. ACC/AHA R4 preempts USPSTF Grade C. KDIGO MODIFIES ACC/AHA R4 (not preempted USPSTF). Demonstrates preemption + modification interaction. |

### Deferred

- Diabetes overlap fixture (USPSTF Grade B + ACC/AHA R3) — candidate for F27 full harness run.
- ASCVD risk ≥10% overlap (USPSTF Grade B + ACC/AHA R4) — candidate for F27.

## Archived

- `archive/` — CRC-era fixtures and inventory retained for reference. Not loaded by the evaluator.
