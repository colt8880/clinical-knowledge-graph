# 52: ADA 2024 Diabetes subgraph

**Status**: pending
**Depends on**: 20, 21, 22
**Components touched**: graph / docs / evals
**Branch**: `feat/ada-diabetes-subgraph`

## Context

Hand-author the ADA 2024 Standards of Medical Care in Diabetes as a standalone subgraph — the fourth guideline in the knowledge graph. ADA Diabetes is the canonical cross-guideline integration challenge: SGLT2 inhibitors appear in both ADA (glycemic control + cardiorenal benefit) and KDIGO (renal protection), metformin dosing depends on eGFR, and ACC/AHA already recommends statins for diabetic patients age 40-75.

No cross-guideline edges in this feature. Those land in F53 after clinician review. The point here is to prove the subgraph stands up on its own before connection work begins.

**Scope of guideline modeled:** pharmacologic glycemic management for type 2 diabetes from ADA Standards 2024, Chapter 9 (Pharmacologic Approaches to Glycemic Treatment) and Chapter 10 (Cardiovascular Disease and Risk Management, statin subsection). Five decision points, not the full 200-page document.

Decision points modeled:

1. **Metformin first-line** — first-line pharmacotherapy for T2DM; initiate unless contraindicated (eGFR < 30).
2. **SGLT2 inhibitor for cardiorenal benefit** — independent of A1C, for patients with established ASCVD, heart failure, or CKD (eGFR 20-60 or albuminuria). This is the primary KDIGO overlap.
3. **GLP-1 RA for cardiovascular benefit** — for patients with established ASCVD or high CVD risk, independent of A1C. Complements or substitutes SGLT2i.
4. **Intensification for glycemic control** — when A1C remains above target (typically ≥ 7%) despite metformin, add SGLT2i, GLP-1 RA, or insulin based on patient factors.
5. **Statin for diabetic patients** — ADA recommends moderate-intensity statin for all diabetic adults 40-75; high-intensity if ASCVD risk factors present. This is the primary ACC/AHA overlap.

## Required reading

- `docs/specs/schema.md` — node/edge types
- `docs/specs/predicate-dsl.md` — eligibility predicates
- `docs/contracts/predicate-catalog.yaml` — current predicate inventory
- `docs/reference/guidelines/cholesterol.md` — reference pattern for a modeled guideline
- `docs/reference/guidelines/kdigo-ckd.md` — KDIGO pattern (CKD staging as predicate)
- `graph/seeds/cholesterol.cypher` — reference Cypher style
- `graph/seeds/kdigo-ckd.cypher` — eGFR predicate patterns
- `graph/seeds/clinical-entities.cypher` — canonical entity registry
- `docs/build/23-accaha-cholesterol-subgraph.md` — template for this spec
- ADA Standards of Medical Care in Diabetes—2024. *Diabetes Care.* 2024;47(Suppl 1). https://doi.org/10.2337/dc24-SINT

## Scope

### New files

- `graph/seeds/ada-diabetes.cypher` — ADA subgraph. Uses `:ADA` domain label. MERGEs against shared entities for all medications.
- `docs/reference/guidelines/ada-diabetes.md` — prose rendering of the modeled subgraph. Structured with stable anchors for Arm B chunking.
- `evals/fixtures/diabetes/case-01/` through `case-04/` — single-guideline fixtures (see Fixture set below).
- `evals/fixtures/diabetes/README.md` — fixture catalog.

### Modified files

- `graph/seeds/clinical-entities.cypher` — add new Medication nodes: metformin, empagliflozin, dapagliflozin, canagliflozin, semaglutide, liraglutide, dulaglutide, insulin glargine, insulin lispro. Add new Observation nodes: HbA1c (LOINC 4548-4), fasting plasma glucose (LOINC 1558-6). Add Condition: heart failure (SNOMED + ICD-10).
- `docs/reference/guideline-sources.md` — add ADA 2024 citation.
- `evals/INVENTORY.md` — add diabetes section.
- `scripts/seed.sh` — add `ada-diabetes.cypher` to load order (after kdigo-ckd, before cross-edges).
- `docs/reference/build-status.md` — add Phase 2 section with F52-F55 rows.

### Predicate additions

New predicates needed for ADA eligibility (add to both `predicate-dsl.md` and `predicate-catalog.yaml`):

- `has_medication_active` — already exists. Used for metformin/statin/SGLT2i active checks.
- `most_recent_observation_value` — already exists. Used for A1C and eGFR thresholds.
- `has_active_condition` — already exists. Used for ASCVD, heart failure, CKD checks.
- No new predicate types are required. The existing catalog covers ADA's eligibility logic.

## Fixture set

| ID | Directory | Coverage |
|----|-----------|----------|
| 01 | `fixtures/diabetes/case-01/` | 52M, T2DM newly diagnosed, A1C 7.8%, no CVD, no CKD, eGFR 85. Metformin first-line (R1). Statin for diabetes (R5, moderate-intensity). |
| 02 | `fixtures/diabetes/case-02/` | 60F, T2DM on metformin, A1C 8.2%, established ASCVD (prior MI), eGFR 62. SGLT2i for cardiorenal benefit (R2). GLP-1 RA for CVD benefit (R3). Statin high-intensity (R5). |
| 03 | `fixtures/diabetes/case-03/` | 58M, T2DM on metformin, A1C 9.1%, CKD 3a (eGFR 50), albuminuria A2 (ACR 120), heart failure. SGLT2i (R2, cardiorenal). Intensification (R4, A1C > 7%). Statin (R5). |
| 04 | `fixtures/diabetes/case-04/` | 45F, T2DM on metformin + empagliflozin, A1C 6.8%, no CVD, eGFR 92. At target — no intensification. Statin for diabetes (R5, moderate-intensity). |

## Constraints

- **Domain label:** every guideline-scoped node carries `:ADA`. No node in this seed carries `:USPSTF`, `:ACC_AHA`, or `:KDIGO`.
- **Shared entity reuse:** statin Medication nodes, SGLT2i nodes (if empagliflozin/dapagliflozin/canagliflozin already exist in clinical-entities), and Observation nodes MUST MERGE against canonical entities. New Medication nodes for metformin, GLP-1 RAs, and insulin are added to `clinical-entities.cypher`, not this seed.
- **No cross-guideline edges in this feature.** The SGLT2i overlap with KDIGO, statin overlap with ACC/AHA, and metformin/eGFR interaction are documented in the reference doc but not expressed as edges until F53.
- **Evidence grade:** ADA uses letter grades (A, B, C, E) where A = clear evidence, E = expert consensus. Map to `evidence_grade` as `"ADA-A"`, `"ADA-B"`, etc. Document the mapping in the reference doc.
- **Structured eligibility:** every Rec has `structured_eligibility` as a predicate tree. No free-text gating.
- **eGFR contraindication:** metformin contraindicated at eGFR < 30. SGLT2i not recommended at eGFR < 20. Encode as `none_of` predicates in eligibility, consistent with KDIGO pattern.
- **A1C input:** fixtures provide A1C as a LOINC observation in patient context. No computed A1C.
- **ASCVD risk input:** fixtures provide `risk_scores.ascvd_10yr` directly, consistent with v1 convention.
- **Single-guideline eval gate:** running the harness on these 4 fixtures with Arm C must produce expected actions with completeness and clinical_appropriateness composite >= 4.0.

## Verification targets

- `cypher-shell < graph/seeds/ada-diabetes.cypher` runs clean after constraints, clinical-entities, statins, cholesterol, and kdigo-ckd seeds.
- Node counts: `MATCH (g:Guideline:ADA) RETURN count(g)` returns 1. `MATCH (r:Recommendation:ADA) RETURN count(r)` returns 5.
- No orphan Medication nodes: every medication referenced by this seed resolves to a node in `clinical-entities.cypher`.
- New clinical entities are added to `clinical-entities.cypher` with proper codes (RxNorm for meds, LOINC for obs, SNOMED+ICD-10 for conditions).
- `cd api && uv run pytest` — all existing tests still pass (no regressions).
- `cd evals && uv run python -m harness --guideline diabetes --arm c --run v2-ada-single` — 4 runs, judge scores completeness >= 4.0 and clinical_appropriateness >= 4.0.
- `docs/reference/guidelines/ada-diabetes.md` has anchored sections per Rec/Strategy for Arm B chunking.
- Docker compose up loads the new seed cleanly (rebuild api image picks up new seed in load order).

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Fixture `expected-actions.json` hand-curated with clinical rationale.
- Prose rendering reviewed for clinical accuracy before PR merge.
- Single-guideline eval gate passed.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Cross-guideline edges to KDIGO, ACC/AHA, or USPSTF (F53).
- Cross-domain fixtures exercising ADA + other guidelines (F54).
- Type 1 diabetes management.
- Non-pharmacologic management (diet, exercise, weight management, bariatric surgery).
- Insulin titration algorithms (complex multi-step; defer to v3).
- DPP-4 inhibitors, thiazolidinediones, sulfonylureas (second-line agents with weaker evidence for cardiorenal benefit; can add in a follow-up feature).
- Gestational diabetes.
- Continuous glucose monitoring (CGM) recommendations.
- Microvascular complication management beyond CKD (retinopathy screening, neuropathy).
- ADA's detailed statin dosing tables (ACC/AHA already models this; ADA defers to ACC/AHA).

## Design notes

- **SGLT2i dual indication.** ADA recommends SGLT2i for cardiorenal benefit *independent of A1C*. This is a separate Rec from glycemic intensification. The same medication class appears in two Recs with different triggers — one clinical (ASCVD/HF/CKD), one metabolic (A1C above target). Both can fire for the same patient. This parallels KDIGO's SGLT2i rec and is the primary cross-guideline interaction target.
- **GLP-1 RA positioning.** ADA recommends GLP-1 RA for CVD benefit in patients with established ASCVD. For patients who qualify for both SGLT2i and GLP-1 RA, both should be recommended. The graph models them as separate Strategies under the same Rec (R2/R3) rather than competing alternatives.
- **Statin rec overlap with ACC/AHA.** ADA R5 (statin for diabetic adults 40-75) is nearly identical to ACC/AHA R3 (diabetes statin benefit group). In F53, this will become a convergence relationship — shared entity layer handles deduplication, possibly no explicit edge needed (same pattern as KDIGO statin convergence with ACC/AHA).
- **A1C target.** ADA recommends < 7% for most adults but individualizes. Model as a simple threshold (7%) with `clinical_nuance` documenting individualization. Do not model individualized targets as separate Recs.
- **Metformin eGFR boundaries.** ADA: initiate if eGFR >= 30, reduce dose at eGFR 30-45, contraindicated < 30. Model the contraindication as a `none_of` predicate. Dose reduction is `clinical_nuance`, not a separate Rec.
