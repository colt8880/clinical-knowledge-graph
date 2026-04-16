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

## Archived

- `archive/` — CRC-era fixtures and inventory retained for reference. Not loaded by the evaluator.
