# 24: KDIGO 2024 CKD subgraph

**Status**: pending
**Depends on**: 20, 21, 22
**Components touched**: graph / docs / evals
**Branch**: `feat/kdigo-ckd-subgraph`

## Context

Hand-author KDIGO 2024 CKD as a standalone subgraph. Like F23, no cross-guideline edges to other domains in this feature; those land in F26. Unlike F23, KDIGO's value in v1 is primarily as connective tissue: CKD stage modifies statin dosing and cholesterol management, and (in v2) diabetes med selection. This feature builds enough of the CKD graph to support F26's modifier edges without over-modeling.

Scope of guideline modeled: CKD staging by eGFR + albuminuria, management recommendations that will modify other guidelines, and the CKD-specific SGLT2 recommendation (which is independently valuable and doesn't conflict with the v1 statin/cholesterol focus).

Decision points modeled:
1. **CKD staging** — G1-G5 by eGFR, A1-A3 by albuminuria. Heatmap-derived risk categories.
2. **SGLT2 inhibitor for CKD** — recommended for CKD + T2DM or CKD + albuminuria regardless of diabetes status.
3. **Statin use in CKD** — KDIGO recommends statins for CKD age ≥50 not on dialysis. This recommendation is the primary modifier target for F26.
4. **ACEi/ARB for albuminuric CKD** — standard guideline-directed therapy; included so the subgraph has breadth.

## Required reading

- `docs/build/v1-spec.md` — v1 scope; KDIGO as connective tissue.
- `docs/specs/schema.md` — node/edge types.
- `docs/specs/predicate-dsl.md` — eligibility predicates; albuminuria thresholds need clean predicate representations.
- `docs/build/20-shared-clinical-entity-layer.md` — canonical entity registry.
- `docs/reference/guidelines/statins.md` — reference modeling pattern.
- KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease — authoritative source; citation added to `docs/reference/guideline-sources.md` in this feature.

## Scope

- `graph/seeds/kdigo-ckd.cypher` — new; KDIGO subgraph with `:KDIGO` domain label. MERGEs against shared entities for SGLT2 meds, ACEi/ARB meds, and any statins referenced.
- `docs/reference/guidelines/kdigo-ckd.md` — prose rendering. Anchored sections matching Rec structure for Arm B.
- `docs/reference/guideline-sources.md` — add KDIGO 2024 citation.
- `evals/fixtures/kdigo/case-01/` — CKD 3a (eGFR 52), albuminuria A1 (ACR 22 mg/g), no diabetes. Age 63.
- `evals/fixtures/kdigo/case-02/` — CKD 3b (eGFR 38), albuminuria A3 (ACR 520 mg/g), T2DM. Age 68.
- `evals/fixtures/kdigo/case-03/` — CKD 4 (eGFR 22), T2DM, hypertension. Age 71.
- Each fixture: `patient-context.json`, `expected-trace.json`, `expected-actions.json`.
- `evals/fixtures/kdigo/README.md` — fixture catalog.
- `evals/INVENTORY.md` — add KDIGO section.
- `scripts/seed.sh` — load `kdigo-ckd.cypher` after `cholesterol.cypher`.
- Expand `graph/seeds/clinical-entities.cypher` if SGLT2 inhibitors or ACEi/ARBs aren't already in the canonical registry from F20.

## Constraints

- **Domain label:** every guideline-scoped node carries `:KDIGO`.
- **Shared entity reuse:** SGLT2 meds (empagliflozin, dapagliflozin), ACEi/ARBs, and any referenced statins MUST come from the canonical registry.
- **No cross-guideline edges.** The KDIGO-statin-for-CKD Rec stands alone in this feature; it will receive `MODIFIES` edges targeting USPSTF/ACC-AHA Recs in F26.
- **CKD staging representation:** use two `Observation` nodes on the patient side (`eGFR`, `ACR`) and an inferred `Condition` node `CKD_stage_Gx_Ay` created by the evaluator's context expansion, OR model staging as a predicate over the two observations directly. Recommendation: stage as a derived predicate, not a synthesized Condition node, to avoid virtual-node drift. Document choice in `docs/reference/guidelines/kdigo-ckd.md`.
- **Albuminuria units:** ACR in mg/g. Fixtures use this unit consistently. Conversion from mg/mmol is not in v1 scope.
- **SGLT2 contraindications:** eGFR < 20 is a contraindication for most SGLT2 starts. Encode as a predicate on the SGLT2 Strategy.
- **Single-guideline eval gate:** running F22 harness on these 3 fixtures with Arm C against the KDIGO subgraph alone must produce expected actions. Composite scores (completeness + clinical_appropriateness) ≥ 4.0 each. Same gate pattern as F23.

## Verification targets

- `cypher-shell < graph/seeds/kdigo-ckd.cypher` runs clean.
- `MATCH (g:Guideline {id: "kdigo-ckd-2024"}) RETURN g` returns 1.
- `MATCH (r:Recommendation:KDIGO) RETURN count(r)` returns ≥ 4 (staging, SGLT2, statin-in-CKD, ACEi/ARB).
- No orphan shared-entity references; canonical registry has all meds this seed uses.
- `cd api && uv run pytest evals/fixtures/kdigo/` — all 3 fixtures produce expected traces.
- `cd evals && uv run python -m harness.runner --guideline kdigo --arm c` — 3 runs, Arm C composite on completeness and clinical_appropriateness ≥ 4.0.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Fixture `expected-actions.json` hand-curated with clinical rationale.
- Prose rendering in `docs/reference/guidelines/kdigo-ckd.md` reviewed for clinical accuracy before merge.
- Single-guideline eval gate passed.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Cross-guideline modifier edges to USPSTF or ACC/AHA (F26).
- Diabetes-specific KDIGO recommendations beyond the generic SGLT2 for CKD + T2DM. Deep diabetes integration is v2.
- Dialysis-specific recommendations (eGFR < 15 and G5D patients).
- Kidney transplant recommendations.
- Pediatric CKD.
- Acute kidney injury.
- CKD-MBD (mineral and bone disorder).
- Dose-adjusted medication tables. v1 encodes "modify statin intensity" as a MODIFIES edge; it does not encode specific dose cutoffs.

## Design notes (not blocking, worth review)

- **Staging as predicate vs. node.** Recommendation is predicate-based (see Constraints). A CKD_Stage_3a node would be tidy but introduces a synthesized Condition not directly present in FHIR patient data. KDIGO itself describes staging as the output of applying eGFR and ACR cutoffs; the predicate approach matches the guideline's framing.
- **The KDIGO "statin for CKD ≥50" Rec is the key modifier anchor for F26.** This Rec says: use statin, but not high-intensity in advanced CKD (specifically, KDIGO recommends moderate-intensity in CKD G3-G5 not on dialysis). F26 will add `MODIFIES` edges from this Rec to the USPSTF and ACC/AHA statin Recs that would otherwise allow high-intensity selection. Model this Rec explicitly even if it overlaps with USPSTF scope, because it's the edge anchor.
- **Heatmap risk categories.** KDIGO categorizes CKD risk into Low/Moderate/High/Very High based on the G × A grid. v1 can skip this; it's a reporting tool, not a decision point modifier that changes downstream recs in the 4 Recs modeled here.
- **eGFR trend vs. point value.** KDIGO 2024 formally requires two measurements ≥ 3 months apart to confirm CKD. Fixtures use a single eGFR for simplicity. Document this simplification in `docs/reference/guidelines/kdigo-ckd.md`. v2 can add the temporal requirement if the patient-context schema gets observation history.
- **Why 3 fixtures, not 4.** KDIGO fixtures are harder to construct cleanly without diabetes overlap, and the cross-domain fixtures in F26 will naturally extend CKD coverage. Fewer standalone fixtures here; more in the cross-domain set.
