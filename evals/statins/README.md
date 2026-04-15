# Statins eval fixtures

Fixtures that exercise the v0 evaluator against the USPSTF 2022 statin primary prevention guideline (`guideline:uspstf-statin-2022`).

Each case is a directory with two files:

- `patient.json` — a `PatientContext` matching `docs/contracts/patient-context.schema.json`.
- `expected-outcome.json` — the recommendations the evaluator must emit, plus specific trace events that must be present or absent.

## Cases

| ID | Demographics | Scenario | Expected outcome |
|---|---|---|---|
| `01-high-risk-55m-smoker` | 55M, current smoker, HTN, untreated | ASCVD 18.2% (supplied), meets Grade B | `rec:statin-initiate-grade-b` emitted as `due` |
| `02-borderline-55f-sdm` | 55F, dyslipidemia, HTN on lisinopril | ASCVD 8.4% (supplied), lands in 7.5 to 10% band | `rec:statin-selective-grade-c` emitted as `due` |
| `03-too-young-35m` | 35M, smoker, HTN | Under age 40 | `exit_condition_triggered: out_of_scope_age_below_range`; no risk lookup, no recommendation |
| `04-grade-i-78f` | 78F, HTN + T2DM | Age >= 76 | `rec:statin-insufficient-evidence-grade-i` emitted as `insufficient_evidence` |
| `05-prior-mi-62m` | 62M, 2024 MI, on atorvastatin | Established ASCVD (secondary prevention) | `exit_condition_triggered: out_of_scope_secondary_prevention`; no recommendation emitted |

## What these cover

- Age gate below range (case 03) and above the Grade B/C range (case 04).
- Secondary prevention exit (case 05). USPSTF primary prevention guideline does not apply once ASCVD is established; v0 does not model secondary prevention.
- Grade B happy path with a supplied risk score (case 01).
- Grade C band (case 02) to verify the 7.5 to 10% window and that shared-decision-making is surfaced as an offered strategy.

## What they do not cover (deferred)

- Patients missing lipid panels entirely. `most_recent_observation_value` returns `unknown` under three-valued logic; eval semantics for this are tracked in `docs/ISSUES.md`.
- Live ASCVD calculation via Pooled Cohort Equations. v0 fixtures supply `risk_scores.ascvd_10yr` directly to decouple the evaluator test from PCE accuracy.
- Statin intolerance or contraindications (no such structured signal in v0 patient context).
- Diabetes as a qualifying risk factor under the Grade B path. Present in case 04, but that case exits on age before the risk factor check runs.

See `evals/SPEC.md` for fixture shape and execution model.
