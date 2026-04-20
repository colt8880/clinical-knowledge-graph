# Cross-domain fixtures

Fixtures exercising multi-guideline convergence: patients matching recommendations from two or more guidelines (USPSTF 2022 Statins, ACC/AHA 2018 Cholesterol, KDIGO 2024 CKD) that target the same shared clinical entities.

These are the thesis differentiators for the v1 harness run (F27). The graph's shared entity layer enables Arm C to surface explicit convergence — "three guidelines independently recommend statin therapy for this patient" — while Arm B's flat RAG retrieves disconnected prose chunks.

## Fixture catalog

| Case | Patient | Guidelines matched | Convergence |
|------|---------|-------------------|-------------|
| case-01 | 62M post-MI, on simvastatin | ACC/AHA only (USPSTF exits) | None — single guideline match |
| case-02 | 55M, HTN, LDL 165, ASCVD risk 8.5% | USPSTF + ACC/AHA | 2-guideline convergence on statin medications |
| case-03 | 65M post-MI, CKD 3b (eGFR 35) | ACC/AHA + KDIGO (USPSTF exits) | 2-guideline convergence on statin medications |
| case-04 | 55M, HTN, CKD 3a (eGFR 52), ASCVD risk 8.5% | USPSTF + ACC/AHA + KDIGO | **3-guideline convergence** on statin medications |

## History

Originally these fixtures tested cross-guideline edges (PREEMPTED_BY, MODIFIES). Those edges were removed (2026-04-20) pending clinician review after modeling errors were found. The fixtures now test multi-guideline convergence via shared clinical entities — a more fundamental graph capability that doesn't require curated interaction edges.

## File structure

Each fixture directory contains:

- `patient-context.json` — synthetic `PatientContext` input
- `expected-trace.json` — assertion templates for trace events and recommendations
- `expected-actions.json` — curated next-best-action list with rationale

## Related

- `docs/build/33-arm-c-convergence-serialization.md` — Arm C convergence serialization
- `docs/build/27-full-harness-thesis-test.md` — thesis test spec
- `docs/ISSUES.md` — cross-guideline edge removal and clinician review requirement
