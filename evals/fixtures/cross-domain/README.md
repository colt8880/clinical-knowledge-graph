# Cross-domain fixtures

Fixtures exercising multi-guideline interactions: patients matching recommendations from two or more guidelines (USPSTF 2022 Statins, ACC/AHA 2018 Cholesterol, KDIGO 2024 CKD) with cross-guideline PREEMPTED_BY and MODIFIES edges active.

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
| case-09 | 58M, Black, HTN, smoker, CKD G3b (eGFR 38), ASCVD 9% | USPSTF + ACC/AHA + KDIGO | **Preemption + Modifier:** ACC/AHA preempts USPSTF Grade C (P4), then KDIGO modifies ACC/AHA to moderate (M1) |
| case-10 | 52F, ASCVD 6.8%, LDL 160, CKD G3a (eGFR 55) | KDIGO only | **Bias probe:** Only KDIGO CKD statin fires. ASCVD below USPSTF/ACC/AHA thresholds. Tests trace-divergent correct answer. |

## Edge coverage (F48)

| Edge | Fixture(s) | Status |
|------|-----------|--------|
| P1 (ACC/AHA diabetes preempts USPSTF Grade B) | case-05 | covered |
| P2 (ACC/AHA diabetes preempts USPSTF Grade C) | case-05 | covered |
| P3 (ACC/AHA primary prev preempts USPSTF Grade B) | case-06 | covered |
| P4 (ACC/AHA primary prev preempts USPSTF Grade C) | case-02, case-04, case-09 | covered |
| P5 (ACC/AHA severe hyperchol preempts USPSTF Grade B) | case-07 | covered |
| P6 (ACC/AHA severe hyperchol preempts USPSTF Grade C) | case-07 | covered |
| M1 (KDIGO modifies ACC/AHA secondary prev intensity) | case-03, case-09 | covered |
| M2 (KDIGO modifies ACC/AHA severe hyperchol intensity) | case-08 | covered |

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
