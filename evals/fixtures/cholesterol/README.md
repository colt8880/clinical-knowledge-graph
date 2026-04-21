# Cholesterol fixtures (ACC/AHA 2018)

Four synthetic patient fixtures covering the four ACC/AHA 2018 statin benefit groups.

## Coverage

| Case | Benefit group | What it exercises |
|---|---|---|
| `case-01` | Severe hypercholesterolemia (R2) | 42F, LDL 230 mg/dL, no ASCVD, no diabetes. LDL ≥190 triggers high-intensity statin without risk calculation. |
| `case-02` | Secondary prevention (R1) | 58M post-MI, LDL 115, on simvastatin (moderate-intensity). Clinical ASCVD → R1 fires. Simvastatin does not satisfy high-intensity strategy → status "due" (upgrade needed). |
| `case-03` | Diabetes (R3) | 55M, diabetes, HTN, LDL 145, ASCVD risk 9.2%. Diabetes age 40-75 → moderate-intensity statin. Risk ≥7.5% supports high-intensity per clinical nuance. |
| `case-04` | Primary prevention below threshold (R4 ineligible) | 48M, LDL 162, no diabetes, ASCVD risk 6.1%. Below 7.5% threshold → R4 ineligible. All four Recs fail eligibility. |

## Fixture shape

Each case directory contains:
- `patient.json` — synthetic `PatientContext` (no PHI)
- `expected-outcome.json` — trace-level assertions (expected recs, expected events, forbidden events)
- `expected-actions.json` — curated next-best-action list with clinical rationale (for harness scoring)

## Running

```sh
# Single-guideline eval gate (Arm C against ACC/AHA subgraph)
cd evals && uv run python -m harness --guideline cholesterol --arm c

# Specific fixture
cd evals && uv run python -m harness --fixture cholesterol/case-01
```

## Deferred

- Cross-domain fixtures (cholesterol + USPSTF overlap): F25.
- Adults >75 ASCVD secondary prevention: v2.
- Statin-intolerant severe hypercholesterolemia: v2.

## Source

ACC/AHA 2018 Cholesterol guideline: Grundy SM, Stone NJ, et al. *Circulation.* 2019;139(25):e1082-e1143.
