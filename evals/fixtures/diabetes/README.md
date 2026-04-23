# Diabetes fixtures (ADA 2024)

Four synthetic patient fixtures covering the five ADA 2024 pharmacologic management decision points for type 2 diabetes.

## Coverage

| Case | Decision points | What it exercises |
|---|---|---|
| `case-01` | R1 (metformin), R5 (statin) | 52M, newly diagnosed T2DM, A1C 7.8%, no CVD, no CKD, eGFR 85. Metformin first-line. Statin for diabetes (moderate-intensity). Not yet on metformin so R4 (intensification) does not fire. |
| `case-02` | R2 (SGLT2i), R3 (GLP-1 RA), R4 (intensification), R5 (statin) | 60F, on metformin, A1C 8.2%, established ASCVD (prior MI), eGFR 62. SGLT2i cardiorenal. GLP-1 RA CVD benefit. Intensification (A1C above target). Statin high-intensity (ASCVD risk factors). |
| `case-03` | R2 (SGLT2i), R4 (intensification), R5 (statin) | 58M, on metformin, A1C 9.1%, CKD 3a (eGFR 50), albuminuria A2 (ACR 120), heart failure. SGLT2i cardiorenal. Intensification. Statin. |
| `case-04` | R5 (statin) | 45F, on metformin + empagliflozin, A1C 6.8%, no CVD, eGFR 92. At target — no intensification needed. Only statin for diabetes fires. |

## Fixture shape

Each case directory contains:
- `patient.json` — synthetic `PatientContext` (no PHI)
- `expected-outcome.json` — trace-level assertions (expected recs, expected events, forbidden events)
- `expected-actions.json` — curated next-best-action list with clinical rationale (for harness scoring)

## Running

```sh
# Single-guideline eval gate (Arm C against ADA subgraph)
cd evals && uv run python -m harness --guideline diabetes --arm c

# Specific fixture
cd evals && uv run python -m harness --fixture diabetes/case-01
```

## Deferred

- Cross-domain fixtures (ADA + KDIGO SGLT2i overlap, ADA + ACC/AHA statin overlap): F54.
- Type 1 diabetes fixtures.
- Insulin titration scenarios.
- Gestational diabetes.

## Source

ADA Standards of Medical Care in Diabetes—2024. *Diabetes Care.* 2024;47(Suppl 1). https://doi.org/10.2337/dc24-SINT
