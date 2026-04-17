# Cross-domain fixtures

Fixtures exercising cross-guideline interactions: `PREEMPTED_BY` (F25, ADR 0018) and `MODIFIES` (F26, ADR 0019) edges between USPSTF 2022 Statins, ACC/AHA 2018 Cholesterol, and KDIGO 2024 CKD.

## Fixture catalog

| Case | Patient | USPSTF outcome | ACC/AHA outcome | KDIGO outcome | Preemption? | Modification? |
|------|---------|----------------|-----------------|---------------|-------------|---------------|
| case-01 | 62M post-MI, on simvastatin | Exit: secondary prevention | R1 (secondary prevention): due | — | No — USPSTF exits | No — no KDIGO Recs match |
| case-02 | 55M, HTN, LDL 165, ASCVD risk 8.5% | Grade C: due | R4 (primary prevention): due | — | **Yes** — ACC/AHA R4 preempts USPSTF Grade C | No — no CKD |
| case-03 | 65M post-MI, CKD 3b (eGFR 35) | Exit: secondary prevention | R1 (secondary prevention): due | Monitoring, SGLT2, statin, ACEi/ARB: due | No — USPSTF exits | **Yes** — KDIGO statin-for-CKD modifies ACC/AHA R1 intensity to moderate |
| case-04 | 55M, HTN, CKD 3a (eGFR 52), ASCVD risk 8.5% | Grade C: due (preempted) | R4 (primary prevention): due | Monitoring, statin: due | **Yes** — ACC/AHA R4 preempts USPSTF Grade C | **Yes** — KDIGO modifies ACC/AHA R4 (not preempted USPSTF) |

## File structure

Each fixture directory contains:

- `patient-context.json` — synthetic `PatientContext` input
- `expected-trace.json` — assertion templates for trace events, recommendations (including `preempted_by` and `modifiers` fields)
- `expected-actions.json` — curated next-best-action list with rationale

## Related

- `docs/reference/guidelines/cross-guideline-map.md` — full edge table (preemption + modifiers)
- `docs/decisions/0018-preemption-precedence.md` — preemption precedence rules
- `docs/decisions/0019-modifies-edge-semantics.md` — modifier semantics
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — PREEMPTED_BY edges
- `graph/seeds/cross-edges-kdigo.cypher` — MODIFIES edges
