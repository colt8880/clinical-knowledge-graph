# Preemption map: USPSTF 2022 Statins ↔ ACC/AHA 2018 Cholesterol

Human-readable table of all `PREEMPTED_BY` edges between USPSTF and ACC/AHA statin recommendations. Source of truth for clinicians reviewing cross-guideline connections. Machine source of truth: `graph/seeds/cross-edges-uspstf-accaha.cypher`.

Per ADR 0018: higher `priority` wins. USPSTF default priority 100; ACC/AHA default priority 200. Preemption only activates when both Recs match the patient.

## Edge count

**9 PREEMPTED_BY edges** across 4 clinical scenarios.

## Edge table

| # | Preempted Rec (loser) | Winning Rec (winner) | Priority | Scenario | Will fire in practice? | Rationale |
|---|---|---|---|---|---|---|
| 1 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits on ASCVD | Safety net. USPSTF primary prevention scope excludes ASCVD patients before Recs match. |
| 2 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits on ASCVD | Safety net. Same as #1 for Grade C. |
| 3 | `rec:statin-insufficient-evidence-grade-i` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits on ASCVD | Safety net. Age ≥76 with ASCVD. |
| 4 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-severe-hypercholesterolemia` (ACC/AHA) | 200 | LDL ≥190 | No — USPSTF exits on FH/LDL≥190 | Safety net. USPSTF exits before matching when LDL ≥190. |
| 5 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-severe-hypercholesterolemia` (ACC/AHA) | 200 | LDL ≥190 | No — USPSTF exits on FH/LDL≥190 | Safety net. Same as #4 for Grade C. |
| 6 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-diabetes` (ACC/AHA) | 200 | Diabetes 40-75 | **Yes** — both match for diabetic patients with ASCVD risk ≥10% | ACC/AHA covers all diabetic adults 40-75 with moderate-intensity statin regardless of risk score, plus high-intensity option. More specific than USPSTF Grade B. |
| 7 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-diabetes` (ACC/AHA) | 200 | Diabetes 40-75 | **Yes** — both match for diabetic patients with ASCVD risk 7.5-<10% | ACC/AHA provides definitive COR I recommendation where USPSTF Grade C requires shared decision-making. |
| 8 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-primary-prevention` (ACC/AHA) | 200 | Primary prevention 40-75 | **Yes** — both match when ASCVD risk ≥10%, LDL 70-189, no diabetes | ACC/AHA provides intensity tiers and risk-enhancer guidance. Both fire for non-diabetic patients with risk ≥10% and LDL in range. |
| 9 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-primary-prevention` (ACC/AHA) | 200 | Primary prevention 40-75 | **Yes** — both match when ASCVD risk 7.5-<10%, LDL 70-189, no diabetes | ACC/AHA provides definitive COR I recommendation for risk ≥7.5% where USPSTF Grade C requires shared decision-making. |

## Clinical scenarios

### Scenario 1: Clinical ASCVD (secondary prevention)

Patient has established atherosclerotic cardiovascular disease (prior MI, stroke, PAD). USPSTF scope is primary prevention only — the evaluator fires `out_of_scope_secondary_prevention` exit before any USPSTF Rec matches. ACC/AHA R1 (secondary prevention, high-intensity statin) matches and is emitted. No preemption fires because there is no USPSTF Rec to preempt. Edges 1-3 exist as safety nets.

### Scenario 2: LDL ≥190 mg/dL (severe hypercholesterolemia)

USPSTF fires `out_of_scope_familial_hypercholesterolemia` exit. ACC/AHA R2 (severe hypercholesterolemia, high-intensity statin) matches. No preemption fires. Edges 4-5 are safety nets.

### Scenario 3: Diabetes, age 40-75

Both USPSTF and ACC/AHA address this population. USPSTF Grade B requires ASCVD risk ≥10%; Grade C requires 7.5-<10%. ACC/AHA R3 covers all diabetic adults 40-75 with moderate-intensity statin regardless of ASCVD risk. When both Recs match (e.g., diabetic patient with risk ≥10%), ACC/AHA R3 preempts USPSTF Grade B because ACC/AHA provides more specific statin intensity guidance within the cardiovascular domain (priority 200 > 100).

### Scenario 4: Primary prevention, no diabetes, age 40-75

Both USPSTF and ACC/AHA address primary prevention in this age range. USPSTF Grade B (risk ≥10%) and ACC/AHA R4 (risk ≥7.5%, LDL 70-189) overlap for patients with risk ≥10%. ACC/AHA R4 preempts USPSTF Grade B/C because it provides intensity tiers, risk-enhancer guidance, and quantitative LDL thresholds that USPSTF does not (priority 200 > 100).

## Related

- ADR 0018: preemption precedence rules
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — Cypher source
- `docs/specs/schema.md` § PREEMPTED_BY edge type
- `docs/specs/eval-trace.md` § preemption_resolved event
