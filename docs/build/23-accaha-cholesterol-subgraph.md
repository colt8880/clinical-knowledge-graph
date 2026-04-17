# 23: ACC/AHA 2018 Cholesterol subgraph

**Status**: pending
**Depends on**: 20, 21, 22
**Components touched**: graph / docs / evals
**Branch**: `feat/accaha-cholesterol-subgraph`

## Context

Hand-author the ACC/AHA 2018 Cholesterol guideline as a standalone subgraph. No cross-guideline edges to USPSTF yet; those land in F25. The point of this feature is to prove the schema holds up against a second guideline and to produce a subgraph that passes its own single-guideline eval gate before connection work begins.

Scope of guideline modeled: the four statin benefit groups from the 2018 update. Not the full guideline. This mirrors the discipline from v0 (decision points, not document mirroring).

Statin benefit groups modeled:
1. **Secondary prevention** — clinical ASCVD; high-intensity statin.
2. **Severe hypercholesterolemia** — LDL ≥190 mg/dL; high-intensity statin.
3. **Diabetes, age 40-75** — moderate-intensity statin, high-intensity if 10-year ASCVD risk ≥7.5%.
4. **Primary prevention, age 40-75, LDL 70-189, no diabetes** — risk-based, aligned with Pooled Cohort Equations. Overlaps with USPSTF; cross-edges handled in F25.

## Required reading

- `docs/build/v1-spec.md` — v1 scope; ACC/AHA is the second guideline.
- `docs/specs/schema.md` — node/edge types.
- `docs/specs/predicate-dsl.md` — eligibility predicates.
- `docs/reference/guidelines/statins.md` — reference pattern for a modeled guideline.
- `graph/seeds/statins.cypher` — reference Cypher style.
- `docs/build/20-shared-clinical-entity-layer.md` — canonical entity registry; shared meds MUST MERGE against it.
- ACC/AHA 2018 Cholesterol guideline text (authoritative source) — `docs/reference/guidelines/cholesterol-source.md` or link to published guideline in comments.

## Scope

- `graph/seeds/cholesterol.cypher` — new; ACC/AHA subgraph. Uses `:ACC_AHA` domain label. MERGEs against shared entities for all medications.
- `docs/reference/guidelines/cholesterol.md` — prose rendering of the modeled subgraph. Structured with stable anchors so F22's Arm B can chunk it.
- `docs/reference/guideline-sources.md` — add ACC/AHA 2018 Cholesterol citation.
- `evals/fixtures/cholesterol/case-01/` — familial hypercholesterolemia, LDL 230, age 42, no prior event.
- `evals/fixtures/cholesterol/case-02/` — secondary prevention, post-MI, LDL 115 on moderate-intensity statin.
- `evals/fixtures/cholesterol/case-03/` — statin-naive, age 55, diabetes, LDL 145, ASCVD risk 9.2%.
- `evals/fixtures/cholesterol/case-04/` — statin-naive, age 48, LDL 162, no diabetes, ASCVD risk 6.1% (below threshold).
- Each fixture: `patient-context.json`, `expected-trace.json`, `expected-actions.json`.
- `evals/fixtures/cholesterol/README.md` — fixture catalog.
- `evals/INVENTORY.md` — add cholesterol section.
- `scripts/seed.sh` — updated to load `cholesterol.cypher` after `statins.cypher`.

## Constraints

- **Domain label:** every guideline-scoped node in this seed carries `:ACC_AHA`. No node in this seed carries `:USPSTF`.
- **Shared entity reuse:** statin Medication nodes MUST MERGE against canonical entities (atorvastatin, rosuvastatin, etc.) created in F20. Creating a new Medication node in this seed is a bug.
- **No cross-guideline edges in this feature.** The two Recs that overlap conceptually with USPSTF (primary prevention, diabetes age 40-75) stand alone; `PREEMPTED_BY` edges and any sequencing logic land in F25.
- **Evidence grade:** ACC/AHA uses COR I/IIa/IIb and LOE A/B/C. Map to `evidence_grade` as a string like `"COR I, LOE A"`. Document the mapping in `docs/reference/guidelines/cholesterol.md`.
- **Structured eligibility:** every Rec has `structured_eligibility` as a predicate tree per `predicate-dsl.md`. No free-text gating.
- **Strategies:** each Rec offers at least one Strategy that fans out to the class-level statin Medication nodes (same pattern as v0 USPSTF). High-intensity vs. moderate-intensity is a property on the Strategy or the `INCLUDES_ACTION` edge, not a separate Rec.
- **ASCVD risk input:** fixtures provide `risk_scores.ascvd_10yr` directly; no live calculation. Consistent with v1 out-of-scope.
- **Fixture coverage:** the 4 fixtures must exercise (a) secondary prevention, (b) LDL ≥190, (c) diabetes age 40-75, (d) primary-prevention-below-threshold. Do not add a fifth fixture in this feature; F25 adds cross-domain fixtures.
- **Single-guideline eval gate:** running the harness (F22) on these 4 fixtures with Arm C against the ACC/AHA subgraph alone must produce expected actions. Specifically: completeness and clinical_appropriateness composite ≥ 4.0 on Arm C. If it doesn't, the subgraph is broken and cross-edges will not rescue it.

## Verification targets

- `cypher-shell < graph/seeds/cholesterol.cypher` runs clean after constraints and clinical-entities seeds.
- Node counts: `MATCH (g:Guideline {id: "acc-aha-cholesterol-2018"}) RETURN g` returns 1. `MATCH (r:Recommendation:ACC_AHA) RETURN count(r)` returns 4.
- No orphan Medication nodes introduced: every medication referenced by this seed resolves to a node created in `clinical-entities.cypher` (checked via test).
- `cd api && uv run pytest evals/fixtures/cholesterol/` — all 4 fixtures produce expected traces.
- `cd evals && uv run python -m harness.runner --guideline cholesterol --arm c` — 4 runs, judge scores completeness ≥ 4.0 and clinical_appropriateness ≥ 4.0.
- `docs/reference/guidelines/cholesterol.md` has anchored sections (`## Secondary prevention`, etc.) so Arm B can chunk cleanly.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Fixture `expected-actions.json` hand-curated with clinical rationale.
- Prose rendering in `docs/reference/guidelines/cholesterol.md` reviewed for clinical accuracy before PR merge.
- Single-guideline eval gate passed (Arm C ≥ 4.0 on completeness and appropriateness).
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Cross-guideline edges to USPSTF (F25).
- KDIGO cross-edges that might affect cholesterol recs (F26).
- ezetimibe and PCSK9 inhibitor intensification pathways. v1 scope is statin-only for ACC/AHA; intensification is a v2 addition.
- Non-statin lipid therapies (fibrates, niacin, bile acid sequestrants).
- Adults over 75 (ACC/AHA discusses this group; defer to v2).
- Pediatric or familial hypercholesterolemia genetic testing pathways. Case-01 uses LDL ≥190 trigger, not genetic criteria.

## Design notes (not blocking, worth review)

- **High-intensity vs. moderate-intensity representation.** Recommendation: a property `intensity: "high" | "moderate"` on the `INCLUDES_ACTION` edge from Strategy to Medication. Keeps the class-level statin fan-out pattern from v0; avoids exploding into per-dose-level nodes.
- **Primary prevention with ASCVD risk 5-7.5%.** ACC/AHA says "consider" at this range. Represent as a Rec with `evidence_grade: "COR IIb, LOE B-R"` and `intent: "consider"`. Note that this overlaps with USPSTF Grade C (shared decision-making); cross-edge in F25.
- **Borderline risk (5-7.5%) with risk enhancers.** ACC/AHA lists enhancers (family history, high-risk ethnicity, CKD, metabolic syndrome, chronic inflammatory conditions, pre-eclampsia, early menopause, LDL ≥160, apoB, Lp(a), etc.). Do not model all of these in v1. Pick the 2-3 that fixtures actually exercise (CKD will matter in F26). Rest stay as prose in the reference doc.
- **"Clinical ASCVD" definition.** Secondary prevention Rec triggers on ACS, stable angina, coronary/peripheral revascularization, stroke/TIA, or PAD. Model this as a predicate over the patient's `conditions` with codes for each. Document the condition code list in `docs/reference/guidelines/cholesterol.md`.
