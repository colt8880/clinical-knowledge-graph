# KDIGO CKD fixtures (KDIGO 2024)

Three synthetic patient fixtures covering four KDIGO 2024 CKD management decision points.

## Coverage

| Case | CKD stage | What it exercises |
|---|---|---|
| `case-01` | G3a-A1 | 63M, eGFR 52, ACR 22, no diabetes. Only monitoring (R1) and statin-for-CKD (R3) fire. SGLT2 and ACEi/ARB do not apply. |
| `case-02` | G3b-A3 | 68M, eGFR 38, ACR 520, T2DM + HTN. All four Recs fire: monitoring, SGLT2 (both diabetes and albuminuria paths), statin, ACEi/ARB. |
| `case-03` | G4-A2 | 71M, eGFR 22, ACR 85, T2DM + HTN. All four Recs fire. Exercises low-eGFR boundaries: near SGLT2 contraindication (eGFR 20) and dialysis proxy (eGFR 15). |

## Fixture shape

Each case directory contains:
- `patient.json` — synthetic `PatientContext` (no PHI)
- `expected-outcome.json` — trace-level assertions (expected recs, expected events, forbidden events)
- `expected-actions.json` — curated next-best-action list with clinical rationale (for harness scoring)

## Running

```sh
# Single-guideline eval gate (Arm C against KDIGO subgraph)
cd evals && uv run python -m harness --guideline kdigo --arm c

# Specific fixture
cd evals && uv run python -m harness --fixture kdigo/case-01
```

## Deferred

- Cross-domain fixtures (CKD modifies statin intensity): F26.
- Dialysis patients (eGFR < 15 / G5D): v2.
- CKD + diabetes deep integration: v2.

## Source

KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease. *Kidney International.* 2024;105(4S):S117-S314.
