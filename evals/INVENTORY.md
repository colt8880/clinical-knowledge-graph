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
| 05 | `fixtures/cross-domain/case-05/` | 50M, T2DM, HTN, ASCVD 12%. ACC/AHA diabetes rec (R3) preempts USPSTF Grade B (P1) and Grade C (P2). Tests diabetes-specific preemption. |
| 06 | `fixtures/cross-domain/case-06/` | 48F, dyslipidemia, LDL 155, ASCVD 11%, no diabetes. ACC/AHA primary prevention R4 preempts USPSTF Grade B (P3). Tests higher-risk preemption spectrum. |
| 07 | `fixtures/cross-domain/case-07/` | 45M, LDL 210 (≥190), HTN, familial pattern. ACC/AHA severe hypercholesterolemia R2 preempts USPSTF (P5 + P6). High-intensity mandated, not moderate. |
| 08 | `fixtures/cross-domain/case-08/` | 60F, LDL 195, CKD G4 (eGFR 22), ACR 145. ACC/AHA R2 high-intensity modified to moderate by KDIGO R3 (M2). Second MODIFIES edge not covered by case-03. |
| 09 | `fixtures/cross-domain/case-09/` | 58M, Black, HTN, smoker, CKD G3b (eGFR 38), ASCVD 9%. ACC/AHA R4 preempts USPSTF Grade C (P4). KDIGO R3 converges on moderate intensity (no MODIFIES edge to R4). Preemption + convergence. |
| 10 | `fixtures/cross-domain/case-10/` | Bias probe: 52F, ASCVD 6.8%, LDL 160, CKD G3a (eGFR 55), controlled HTN on ACEi. Only KDIGO CKD statin fires — ASCVD below both USPSTF and ACC/AHA thresholds. Tests trace-divergent correct answer. |

| 11 | `fixtures/cross-domain/case-11/` | 55M, T2DM on metformin, A1C 7.2%, HTN, ASCVD 14%, eGFR 85. ADA + ACC/AHA + USPSTF. ACC/AHA R3 preempts USPSTF (P1+P2). ADA R5 statin converges with ACC/AHA R3. ADA R4 intensification. Simplest 3-guideline diabetes case. |
| 12 | `fixtures/cross-domain/case-12/` | 62F, T2DM on metformin, A1C 8.5%, prior stroke, CKD 3a (eGFR 48), ACR 180. Full 4-guideline activation. KDIGO M1 modifies ACC/AHA R1 intensity. ADA R2 SGLT2i converges with KDIGO R2. ADA R3 GLP-1 RA. The hardest case. |
| 13 | `fixtures/cross-domain/case-13/` | 68M, T2DM on metformin + empagliflozin, A1C 6.9%, CKD 3b (eGFR 35), ACR 320, HF. ADA + KDIGO. Satisfied SGLT2i strategies. Statin convergence. Metformin dose reduction (eGFR 30-45). |
| 14 | `fixtures/cross-domain/case-14/` | 50M, newly diagnosed T2DM, A1C 8.8%, HTN, smoker, ASCVD 18%, LDL 175, eGFR 72. ADA + ACC/AHA + USPSTF. High-intensity statin (multiple risk enhancers). ADA R1 metformin first-line. |
| 15 | `fixtures/cross-domain/case-15/` | 72F, T2DM on metformin + glargine, A1C 7.8%, CKD 4 (eGFR 22), ACR 250, HF. ADA + KDIGO. Metformin contraindicated (eGFR < 30). SGLT2i borderline (eGFR 22). Hardest eGFR boundary case. |
| 16 | `fixtures/cross-domain/case-16/` | 48M, well-controlled T2DM on metformin, A1C 6.5%, eGFR 95, LDL 110, ASCVD 5.2%. ADA + ACC/AHA borderline. Only moderate statin fires. Tests correct non-activation. |

### Deferred

- Dialysis patient (CKD G5D) — KDIGO statin evidence different for dialysis.

## Diabetes (v2 — ADA 2024)

### Landed

| ID | Directory | Coverage |
|---|---|---|
| 01 | `fixtures/diabetes/case-01/` | 52M, newly diagnosed T2DM, A1C 7.8%, no CVD, no CKD, eGFR 85. Metformin first-line (R1). Statin for diabetes (R5, moderate-intensity). |
| 02 | `fixtures/diabetes/case-02/` | 60F, T2DM on metformin, A1C 8.2%, established ASCVD (prior MI), eGFR 62. SGLT2i cardiorenal (R2). GLP-1 RA CVD (R3). Intensification (R4). Statin high-intensity (R5). |
| 03 | `fixtures/diabetes/case-03/` | 58M, T2DM on metformin, A1C 9.1%, CKD 3a (eGFR 50), albuminuria A2 (ACR 120), HF. SGLT2i cardiorenal (R2). Intensification (R4). Statin (R5). |
| 04 | `fixtures/diabetes/case-04/` | 45F, T2DM on metformin + empagliflozin, A1C 6.8%, no CVD, eGFR 92. At target. Only statin (R5, moderate-intensity) fires. |

### Deferred

- Cross-domain fixtures (ADA + KDIGO SGLT2i overlap, ADA + ACC/AHA statin overlap): F54.
- Type 1 diabetes.
- Insulin titration scenarios.
- Gestational diabetes.

## Archived

- `archive/` — CRC-era fixtures and inventory retained for reference. Not loaded by the evaluator.
