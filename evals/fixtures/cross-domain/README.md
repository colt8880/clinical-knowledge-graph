# Cross-domain fixtures

Fixtures exercising multi-guideline interactions: patients matching recommendations from two or more guidelines (USPSTF 2022 Statins, ACC/AHA 2018 Cholesterol, KDIGO 2024 CKD, ADA 2024 Diabetes) with cross-guideline PREEMPTED_BY, MODIFIES, and convergence interactions active.

These are the thesis differentiators for the v1 harness run (F27). The graph's cross-guideline edges enable Arm C to surface explicit preemption and modification — "ACC/AHA preempts USPSTF for this patient" or "KDIGO modifies statin intensity to moderate" — while Arm B's flat RAG retrieves disconnected prose chunks.

## Fixture catalog

| Case | Patient | Guidelines matched | Cross-guideline events |
|------|---------|-------------------|------------------------|
| case-01 | 62M post-MI, on simvastatin | ACC/AHA only (USPSTF exits) | None — USPSTF exits before emitting, no preemption fires |
| case-02 | 55M, HTN, LDL 165, ASCVD risk 8.5% | USPSTF + ACC/AHA | **Preemption:** ACC/AHA primary prevention preempts USPSTF Grade C (P4) |
| case-03 | 65M post-MI, CKD 3b (eGFR 35) | ACC/AHA + KDIGO (USPSTF exits) | **Modifier:** KDIGO CKD statin modifies ACC/AHA secondary prevention intensity (M1) |
| case-04 | 55M, HTN, CKD 3a (eGFR 52), ASCVD risk 8.5% | USPSTF + ACC/AHA + KDIGO | **Preemption:** ACC/AHA primary prevention preempts USPSTF Grade C (P4) |
| case-05 | 50M, T2DM, HTN, ASCVD 12% | USPSTF + ACC/AHA | **Preemption:** ACC/AHA diabetes rec preempts USPSTF Grade B + C (P1 + P2) |
| case-06 | 48F, dyslipidemia, LDL 155, ASCVD 11% | USPSTF + ACC/AHA | **Preemption:** ACC/AHA primary prevention preempts USPSTF Grade B (P3) |
| case-07 | 45M, LDL 210, HTN, familial pattern | ACC/AHA (USPSTF exits for LDL ≥190) | **Preemption:** ACC/AHA severe hypercholesterolemia preempts USPSTF (P5 + P6). High-intensity mandated. |
| case-08 | 60F, LDL 195, CKD G4 (eGFR 22) | ACC/AHA + KDIGO (USPSTF exits for LDL ≥190) | **Modifier:** KDIGO modifies ACC/AHA severe hypercholesterolemia to moderate intensity (M2) |
| case-09 | 58M, Black, HTN, smoker, CKD G3b (eGFR 38), ASCVD 9% | USPSTF + ACC/AHA + KDIGO | **Preemption + Convergence:** ACC/AHA preempts USPSTF Grade C (P4); KDIGO CKD statin converges on moderate intensity |
| case-10 | 52F, ASCVD 6.8%, LDL 160, CKD G3a (eGFR 55) | KDIGO only | **Bias probe:** Only KDIGO CKD statin fires. ASCVD below USPSTF/ACC/AHA thresholds. Tests trace-divergent correct answer. |
| case-11 | 55M, T2DM on metformin, A1C 7.2%, HTN, ASCVD 14%, eGFR 85 | ADA + ACC/AHA + USPSTF | **Preemption + Convergence:** ACC/AHA R3 preempts USPSTF (P1+P2). ADA R5 statin converges with ACC/AHA R3. ADA R4 intensification fires. Simplest 3-guideline diabetes case. |
| case-12 | 62F, T2DM on metformin, A1C 8.5%, prior stroke, eGFR 48, ACR 180 | ADA + KDIGO + ACC/AHA + USPSTF | **Full 4-guideline:** ACC/AHA R1 high-intensity modified to moderate by KDIGO R3 (M1). ADA R2 SGLT2i converges with KDIGO R2. ADA R3 GLP-1 RA for CVD. The hardest case. |
| case-13 | 68M, T2DM on metformin + empagliflozin, A1C 6.9%, CKD 3b (eGFR 35), ACR 320, HF | ADA + KDIGO | **Satisfied strategies:** ADA R2 + KDIGO R2 SGLT2i both satisfied (empagliflozin active). ADA R5 + KDIGO R3 statin convergence. Metformin dose reduction (eGFR 30-45). |
| case-14 | 50M, newly diagnosed T2DM, A1C 8.8%, HTN, smoker, ASCVD 18%, LDL 175, eGFR 72 | ADA + ACC/AHA + USPSTF | **Preemption + Convergence:** ACC/AHA R3 preempts USPSTF (P1+P2). High-intensity statin (multiple risk enhancers). ADA R1 metformin first-line. High-risk diabetes. |
| case-15 | 72F, T2DM on metformin + glargine, A1C 7.8%, CKD 4 (eGFR 22), ACR 250, HF | ADA + KDIGO | **eGFR boundaries:** Metformin contraindicated (eGFR < 30). SGLT2i borderline (eGFR 22, >=20). KDIGO monitoring high frequency. ADA/KDIGO statin convergence. |
| case-16 | 48M, well-controlled T2DM on metformin, A1C 6.5%, eGFR 95, LDL 110, ASCVD 5.2% | ADA + (ACC/AHA borderline) | **Non-activation:** Only ADA R5 + ACC/AHA R3 moderate statin fire. USPSTF below threshold. No CKD/CVD/HF. A1C at target. The "boring" patient. |

## Edge coverage (F48 + F54)

| Edge | Fixture(s) | Status |
|------|-----------|--------|
| P1 (ACC/AHA diabetes preempts USPSTF Grade B) | case-05, case-11, case-14 | covered |
| P2 (ACC/AHA diabetes preempts USPSTF Grade C) | case-05, case-11, case-14 | covered |
| P3 (ACC/AHA primary prev preempts USPSTF Grade B) | case-06 | covered |
| P4 (ACC/AHA primary prev preempts USPSTF Grade C) | case-02, case-04, case-09 | covered |
| P5 (ACC/AHA severe hyperchol preempts USPSTF Grade B) | case-07 | covered |
| P6 (ACC/AHA severe hyperchol preempts USPSTF Grade C) | case-07 | covered |
| M1 (KDIGO modifies ACC/AHA secondary prev intensity) | case-03, case-12 | covered |
| M2 (KDIGO modifies ACC/AHA severe hyperchol intensity) | case-08 | covered |
| M1-ADA (KDIGO monitoring modifies ADA metformin dosing) | case-13, case-15 | covered |

### Convergence coverage (F54)

| Convergence | Fixture(s) | Status |
|-------------|-----------|--------|
| C11 (ADA R5 ↔ ACC/AHA R3 statin for diabetes) | case-11, case-14, case-16 | covered |
| C14-C15 (ADA R2/R4 ↔ KDIGO R2 SGLT2i) | case-12, case-13 | covered |
| C16 (ADA R5 ↔ KDIGO R3 statin for CKD) | case-12, case-13, case-15 | covered |

## History

Originally these fixtures tested LLM-authored cross-guideline edges. Those edges were removed (2026-04-20) pending clinician review after modeling errors were found. After clinician review (2026-04-21, documented in `docs/review/cross-edges.md`), 8 validated edges were re-added in F41: 6 PREEMPTED_BY (ACC/AHA preempts USPSTF) and 2 MODIFIES (KDIGO intensity reduction on ACC/AHA high-intensity recs).

## File structure

Each fixture directory contains:

- `patient-context.json` — synthetic `PatientContext` input
- `expected-trace.json` — assertion templates for trace events and recommendations
- `expected-actions.json` — curated next-best-action list with rationale

## Related

- `docs/review/cross-edges.md` — clinician review decisions
- `docs/build/41-validated-cross-edges.md` — feature spec for re-adding validated edges
- `docs/build/33-arm-c-convergence-serialization.md` — Arm C convergence serialization
- `docs/build/27-full-harness-thesis-test.md` — thesis test spec
