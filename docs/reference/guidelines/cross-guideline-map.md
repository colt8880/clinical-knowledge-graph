# Cross-guideline edge map

Human-readable table of all cross-guideline edges: `PREEMPTED_BY` (F25) and `MODIFIES` (F26). Source of truth for clinicians reviewing cross-guideline connections.

Machine source of truth:
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — PREEMPTED_BY edges
- `graph/seeds/cross-edges-kdigo.cypher` — MODIFIES edges

## Edge counts

- **9 PREEMPTED_BY edges** — USPSTF ↔ ACC/AHA (F25)
- **6 MODIFIES edges** — KDIGO → USPSTF/ACC-AHA (F26)
- **15 total cross-guideline edges**

## PREEMPTED_BY edges (F25, ADR 0018)

Higher `priority` wins. USPSTF default 100; ACC/AHA default 200. Preemption only activates when both Recs match the patient.

| # | Preempted Rec (loser) | Winning Rec (winner) | Priority | Scenario | Fires in practice? | Rationale |
|---|---|---|---|---|---|---|
| 1 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits | Safety net |
| 2 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits | Safety net |
| 3 | `rec:statin-insufficient-evidence-grade-i` (USPSTF) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | 200 | Secondary prevention | No — USPSTF exits | Safety net |
| 4 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-severe-hypercholesterolemia` (ACC/AHA) | 200 | LDL ≥190 | No — USPSTF exits | Safety net |
| 5 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-severe-hypercholesterolemia` (ACC/AHA) | 200 | LDL ≥190 | No — USPSTF exits | Safety net |
| 6 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-diabetes` (ACC/AHA) | 200 | Diabetes 40-75 | **Yes** | ACC/AHA more specific |
| 7 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-diabetes` (ACC/AHA) | 200 | Diabetes 40-75 | **Yes** | ACC/AHA more specific |
| 8 | `rec:statin-initiate-grade-b` (USPSTF) | `rec:accaha-statin-primary-prevention` (ACC/AHA) | 200 | Primary prevention 40-75 | **Yes** | ACC/AHA intensity tiers |
| 9 | `rec:statin-selective-grade-c` (USPSTF) | `rec:accaha-statin-primary-prevention` (ACC/AHA) | 200 | Primary prevention 40-75 | **Yes** | ACC/AHA intensity tiers |

## MODIFIES edges (F26, ADR 0019)

`MODIFIES` is additive, not gating. The target Rec still fires; the modifier annotates. Direction: FROM the modifying Rec TO the modified Rec. Preempted targets do not receive modifiers.

All six edges originate from `rec:kdigo-statin-for-ckd` (KDIGO), which recommends moderate-intensity statin for CKD G3-G5 patients aged ≥50 not on dialysis.

| # | Source Rec (modifier) | Target Rec (modified) | Nature | Scenario | Clinical rationale |
|---|---|---|---|---|---|
| 1 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:accaha-statin-secondary-prevention` (ACC/AHA) | `intensity_reduction` | CKD + ASCVD | ACC/AHA recommends high-intensity statin for ASCVD. KDIGO modifies to moderate-intensity in CKD G3-G5 due to altered pharmacokinetics and increased myopathy risk. |
| 2 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:accaha-statin-severe-hypercholesterolemia` (ACC/AHA) | `intensity_reduction` | CKD + LDL ≥190 | ACC/AHA recommends high-intensity for LDL ≥190. KDIGO modifies to moderate in CKD G3-G5. Balance LDL reduction against CKD-related drug metabolism. |
| 3 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:accaha-statin-primary-prevention` (ACC/AHA) | `intensity_reduction` | CKD + primary prevention | ACC/AHA may recommend moderate-to-high intensity. KDIGO caps at moderate in CKD G3-G5. |
| 4 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:accaha-statin-diabetes` (ACC/AHA) | `intensity_reduction` | CKD + diabetes | ACC/AHA recommends moderate with high-intensity option for risk ≥7.5%. KDIGO restricts to moderate in CKD G3-G5. |
| 5 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:statin-initiate-grade-b` (USPSTF) | `intensity_reduction` | CKD + USPSTF Grade B | Both align on moderate intensity. KDIGO surfaces CKD-specific context: renal dosing, drug interactions, eGFR monitoring. |
| 6 | `rec:kdigo-statin-for-ckd` (KDIGO) | `rec:statin-selective-grade-c` (USPSTF) | `intensity_reduction` | CKD + USPSTF Grade C | KDIGO surfaces CKD context for shared decision-making. CKD is a cardiovascular risk enhancer. |

## Interaction: preemption + modification

When a Rec is both preempted and has a modifier edge, **preemption takes precedence** (ADR 0019). The modifier event is suppressed because the preempted Rec is already overridden.

**Example (case-04):** USPSTF Grade C is preempted by ACC/AHA R4 (primary prevention). KDIGO has modifier edges to both. The modifier fires on ACC/AHA R4 (not preempted) but is suppressed on USPSTF Grade C (preempted). The trace contains a `preemption_resolved` event for USPSTF Grade C and a `cross_guideline_match` event for ACC/AHA R4, but no `cross_guideline_match` for USPSTF Grade C.

## Related

- ADR 0018: preemption precedence rules
- ADR 0019: MODIFIES edge semantics
- `docs/specs/schema.md` § PREEMPTED_BY, MODIFIES edge types
- `docs/specs/eval-trace.md` § preemption_resolved, cross_guideline_match events
