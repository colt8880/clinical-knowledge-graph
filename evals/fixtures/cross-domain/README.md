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
