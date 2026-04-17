# Cross-domain fixtures

Fixtures exercising cross-guideline interactions between USPSTF 2022 Statins and ACC/AHA 2018 Cholesterol. Tests `PREEMPTED_BY` edge resolution per ADR 0018.

## Fixture catalog

| Case | Patient | USPSTF outcome | ACC/AHA outcome | Preemption? |
|------|---------|----------------|-----------------|-------------|
| case-01 | 62M post-MI, on simvastatin | Exit: `out_of_scope_secondary_prevention` | R1 (secondary prevention): due for high-intensity upgrade | No — USPSTF exits, no Rec to preempt |
| case-02 | 55M, HTN, LDL 165, ASCVD risk 8.5% | Grade C: due (7.5-<10%) | R4 (primary prevention): due (risk ≥7.5%, LDL 70-189) | **Yes** — ACC/AHA R4 preempts USPSTF Grade C (priority 200 > 100) |

## File structure

Each fixture directory contains:

- `patient-context.json` — synthetic `PatientContext` input
- `expected-trace.json` — assertion templates for trace events and recommendations (including `preempted_by` field)
- `expected-actions.json` — curated next-best-action list with rationale

## Related

- `docs/reference/guidelines/preemption-map.md` — full edge table
- `docs/decisions/0018-preemption-precedence.md` — precedence rules
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — Cypher source
