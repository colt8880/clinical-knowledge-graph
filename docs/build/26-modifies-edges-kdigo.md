# 26: MODIFIES edges from KDIGO to USPSTF and ACC/AHA

**Status**: pending
**Depends on**: 24, 25
**Components touched**: graph / api / docs / evals
**Branch**: `feat/modifies-edges-kdigo`

## Context

CKD doesn't cancel other guidelines' Recs; it modifies them. A patient in CKD 3b who also qualifies for ACC/AHA high-intensity statin should still get a statin, but at moderate intensity and with consideration of drug interactions. The USPSTF or ACC/AHA Rec still fires; a `MODIFIES` edge annotates it.

This feature introduces the `MODIFIES` edge class, implements modifier-event emission in the evaluator, authors the edges from KDIGO Recs to USPSTF/ACC-AHA statin Recs, and adds cross-domain fixtures that exercise the behavior.

Scenarios exercised:
1. **CKD 3b + ACC/AHA high-intensity indication.** `MODIFIES` edge from KDIGO "moderate-intensity statin in CKD G3-G5" Rec to ACC/AHA high-intensity Strategies. Evaluator emits modifier events; Arm C context flags the intensity adjustment.
2. **CKD 3a + USPSTF statin-eligible.** KDIGO's statin Rec and USPSTF's overlap in scope; modifier edge ensures Arm C surfaces the CKD context to clinicians.
3. **CKD + cholesterol Strategy.** Same pattern applied to the ACC/AHA cholesterol Rec for LDL ≥ 190.

## Required reading

- `docs/build/v1-spec.md` — `MODIFIES` introduced as a new edge class distinct from `PREEMPTED_BY`.
- `docs/build/25-preemption-uspstf-accaha.md` — preemption is the sibling concept; modifier is additive annotation.
- `docs/specs/schema.md` — amend with `MODIFIES` edge spec.
- `docs/specs/eval-trace.md` — `CROSS_GUIDELINE_MATCH` event reserved in F21; this feature emits it.
- `docs/build/24-kdigo-ckd-subgraph.md` — KDIGO Recs that will author the modifier edges.
- **`docs/decisions/0019-modifies-edge-semantics.md`** — NEW ADR; defines `MODIFIES` semantics, distinguishes from `PREEMPTED_BY`, covers "what if both MODIFIES and PREEMPTED_BY apply" cases. MUST be merged before this feature's PR.

## Scope

- `docs/decisions/0019-modifies-edge-semantics.md` — NEW ADR.
- `graph/seeds/cross-edges-kdigo.cypher` — new; authors `MODIFIES` edges from KDIGO Recs (and, where appropriate, from the CKD staging Observations via a predicate-keyed edge pattern) to USPSTF and ACC/AHA Recs and Strategies.
- `docs/specs/schema.md` — document `MODIFIES` as: `(source:Recommendation|Observation|Condition)-[:MODIFIES {nature: "intensity_reduction"|"dose_adjustment"|"monitoring"|"contraindication_warning", note: "..."}]->(target:Recommendation|Strategy)`. Cross-guideline only (source and target must have different `guideline_id`).
- `docs/contracts/` — update schema contract.
- `api/app/evaluator/modifiers.py` — new module; walks `MODIFIES` edges during evaluation and emits annotation events.
- `api/app/evaluator/trace.py` — emit `CROSS_GUIDELINE_MATCH` events for each triggered modifier. Payload: `{source_rec_id, target_rec_id, nature, note, source_guideline_id, target_guideline_id}`.
- `api/tests/test_modifiers.py` — unit tests for modifier emission, ordering, and interaction with preemption.
- `evals/fixtures/cross-domain/case-03/` — CKD 3b + secondary prevention (ACC/AHA high-intensity indication preempts USPSTF; KDIGO modifies intensity down).
- `evals/fixtures/cross-domain/case-04/` — CKD 3a + primary prevention age 55, LDL 145, ASCVD risk 8.5%; USPSTF and ACC/AHA primary-prevention Recs apply; KDIGO modifies.
- Each fixture: `patient-context.json`, `expected-trace.json`, `expected-actions.json`.
- `docs/reference/guidelines/cross-guideline-map.md` — new (or amend the preemption map from F25); tabulates both `PREEMPTED_BY` and `MODIFIES` edges with clinical rationale.

## Constraints

- **`MODIFIES` is cross-guideline only.** Same-guideline modifications stay intra-seed (use existing Rec/Strategy structure). Seed-time check enforces this.
- **`MODIFIES` is additive, not gating.** The target Rec still fires. The modifier annotates. Evaluator emits a `CROSS_GUIDELINE_MATCH` event for every triggered modifier in the trace, after the target Rec's `REC_MATCHED` event.
- **Preemption takes precedence over modification.** If a Rec is preempted, its modifiers are not emitted (they would be noise). This interaction is documented in ADR 0019.
- **Modifier edge `nature` enum:** `intensity_reduction`, `dose_adjustment`, `monitoring`, `contraindication_warning`. No free-form string. If a new nature is needed in the future, ADR + schema update.
- **Determinism:** modifier events emitted in deterministic order: ascending by `(source_guideline_id, source_rec_id, target_rec_id)`.
- **Source-side edges:** modifiers can originate from KDIGO Recs OR from patient-state predicates on CKD-related Observations (specifically, the eGFR Observation). v1 uses the Rec-sourced pattern for simplicity; Observation-sourced is a design note below.
- **Regression:** all prior fixture sets (v0 statins, F23 cholesterol standalone, F24 KDIGO standalone, F25 cross-domain cases 01/02) must produce unchanged traces. New fixtures 03/04 are the only ones with new trace content from this feature.

## Verification targets

- ADR 0019 merged before this PR opens.
- `cypher-shell < graph/seeds/cross-edges-kdigo.cypher` runs clean.
- `MATCH ()-[r:MODIFIES]->() WHERE startNode(r).guideline_id = endNode(r).guideline_id RETURN count(r)` returns 0 (no intra-guideline modifiers).
- All prior fixtures unchanged (byte-identical expected-trace.json except for the intentional extensions to cross-domain cases).
- Cross-domain cases 03/04: `CROSS_GUIDELINE_MATCH` events present with correct payload.
- `cd evals && uv run python -m harness.runner --fixture cross-domain/case-03 --arm c` scores ≥ 4.0 on completeness, clinical_appropriateness, and integration.
- Preemption + modifier interaction test: synthetic fixture where a Rec is both preempted and modified produces a trace with preemption but NOT the (now-suppressed) modifier event.

## Definition of done

- ADR 0019 written, reviewed, merged.
- All scope files exist and match constraints.
- All verification targets pass locally.
- Cross-guideline map reviewed for clinical accuracy.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- UI visualization of modifiers (F29).
- Modifier edges to/from ADA, ACIP, or other guidelines (out of v1).
- Drug-drug interaction modifiers within a single guideline.
- Cascade: a MODIFIES edge triggering another MODIFIES edge. v1 is non-cascading.
- Dose tables. Modifier says "intensity_reduction"; it does not say "atorvastatin 20 mg". Exact dosing is clinical judgment.

## Design notes (not blocking, worth review)

- **Rec-sourced vs. Observation-sourced MODIFIES.** Rec-sourced means: the KDIGO "statin for CKD" Rec fires AND has MODIFIES edges to external Recs. Clean because it piggybacks on matching semantics. Observation-sourced would mean: the eGFR Observation carries MODIFIES edges directly (no intermediate Rec needed). More flexible but creates edges from clinical entity nodes, which were designed to be shared and stateless. v1 uses Rec-sourced. If v2 needs purely observation-driven modifiers (e.g., "eGFR < 30 modifies metformin selection" without a guideline Rec wrapping it), revisit.
- **Preemption vs. modification, when both could apply.** Rare but real: USPSTF Grade B could be preempted by ACC/AHA secondary prevention AND modified by KDIGO. Rule: preemption fires, modifier is suppressed. Document the reason in the trace via an explicit `MODIFIER_SUPPRESSED` sub-field on `PREEMPTION_RESOLVED`. This keeps the audit trail complete.
- **How the harness presents modifiers to Arm C.** Arm C's serialized context includes: matched Recs, preemption events, and modifier events. The `rendered_prose` output says something like "USPSTF statin Rec matched; KDIGO modifies intensity to moderate because CKD G3b." The judge then scores whether the LLM output reflects that guidance.
- **Why `intensity_reduction` and `dose_adjustment` as separate nature values:** intensity reduction is a Strategy-level change (high → moderate). Dose adjustment is a Medication-level change within a chosen intensity. v1 only authors intensity_reduction edges; dose_adjustment is reserved for future use but defined in the enum so the contract is stable.
- **Modifier load order:** cross-edges seed loads after both guideline seeds. Modifier edges from KDIGO to ACC/AHA require ACC/AHA Recs to exist first. Seed script order: clinical-entities → statins → cholesterol → kdigo-ckd → cross-edges-uspstf-accaha → cross-edges-kdigo.
