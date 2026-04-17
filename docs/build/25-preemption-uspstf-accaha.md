# 25: Preemption and cross-edges, USPSTF ↔ ACC/AHA

**Status**: pending
**Depends on**: 23 (ACC/AHA subgraph must pass its eval gate)
**Components touched**: graph / api / docs / evals
**Branch**: `feat/preemption-uspstf-accaha`

## Context

First cross-guideline connection. Activates the `PREEMPTED_BY` schema (present since v0, unused) and implements the precedence resolution in the evaluator. Scope is limited to USPSTF ↔ ACC/AHA. KDIGO cross-edges are F26.

Preemption scenarios this feature handles:
1. **Patient has clinical ASCVD.** USPSTF scope is primary prevention; USPSTF Recs must not fire when ACC/AHA secondary-prevention triggers. This is the cleanest preemption case.
2. **LDL ≥ 190.** ACC/AHA recommends high-intensity statin regardless of ASCVD risk. USPSTF Grade B/C reasoning becomes non-applicable when LDL ≥ 190 because ACC/AHA has a more specific trigger.
3. **Diabetes age 40-75.** Both guidelines discuss this group. USPSTF Grade B applies if risk ≥ 10%; ACC/AHA covers all patients in this group with moderate-intensity statin. In overlap, ACC/AHA (priority 200) preempts USPSTF (priority 100).
4. **Primary prevention no diabetes, age 40-75.** Both apply. USPSTF Grade B (risk ≥ 10%) and ACC/AHA risk-based (≥ 7.5%) overlap but use different thresholds. v1 rule: both Recs fire but preemption marks USPSTF as preempted when ACC/AHA's stricter threshold is met, because ACC/AHA gives the more specific quantitative guidance. Document edge priority accordingly.

## Required reading

- `docs/build/v1-spec.md` — preemption described in the macro spec; this feature implements it.
- `docs/specs/schema.md` — `PREEMPTED_BY` edge definition; amend to include `priority` property.
- `docs/specs/eval-trace.md` — `preemption_resolved` event schema reserved in F21; implement in this feature.
- `docs/build/21-multi-guideline-evaluator.md` — structural foundation.
- `docs/reference/guidelines/statins.md` and `docs/reference/guidelines/cholesterol.md` — the two guideline references.
- **`docs/decisions/0018-preemption-precedence.md`** — NEW ADR authored alongside this feature. Documents the priority-integer-plus-published-at approach and the default priority assignments per guideline. MUST be merged before this feature's PR opens.

## Scope

- `docs/decisions/0018-preemption-precedence.md` — NEW ADR; preemption precedence rules. Merged on its own branch first; referenced in this feature.
- `graph/seeds/cross-edges-uspstf-accaha.cypher` — new; authors `PREEMPTED_BY` edges between overlapping Recs from the two guidelines. Loaded after both guideline seeds.
- `graph/constraints.cypher` — if not already, index `PREEMPTED_BY.priority`.
- `docs/specs/schema.md` — document the `priority` property and the precedence rule.
- `docs/contracts/` — update schema contract for the edge.
- `api/app/evaluator/preemption.py` — new module; resolves preemption on the trace.
- `api/app/evaluator/trace.py` — add `preemption_resolved(preempted_rec_id, winning_rec_id, edge_priority, reason)` method on `TraceBuilder`. Append-only; does not mutate prior events.
- `api/tests/test_preemption.py` — unit tests for precedence resolution with priority ties, published_at tiebreaks, transitive preemption (disallowed; must raise or log).
- `evals/fixtures/cross-domain/case-01/` — clinical ASCVD patient; USPSTF Recs preempted by ACC/AHA secondary prevention.
- `evals/fixtures/cross-domain/case-02/` — primary prevention patient with LDL 165, ASCVD risk 8.5%; both USPSTF and ACC/AHA apply; tests threshold overlap.
- Each fixture: `patient-context.json`, `expected-trace.json`, `expected-actions.json`.
- `evals/fixtures/cross-domain/README.md` — fixture catalog.
- `docs/reference/guidelines/preemption-map.md` — new; human-readable table of preemption edges: which Rec preempts which, why, at what priority. Source of truth for clinicians reviewing the cross-edges.

## Constraints

- **Precedence rules (from ADR 0018):**
  - Higher `priority` integer wins.
  - Tie on priority: newer `Guideline.published_at` wins.
  - No transitive preemption. If A preempts B and B preempts C, A does not automatically preempt C. Authors must explicitly add the A → C edge if intended. Evaluator raises on detected transitive chains.
- **Default priorities:** USPSTF = 100, ACC/AHA = 200. Specialty society overrides federal task force within the specialty's domain. Documented in ADR.
- **`PREEMPTED_BY` direction:** edge points FROM the preempted Rec TO the winning Rec. `(loser:Recommendation)-[:PREEMPTED_BY {priority: 200}]->(winner:Recommendation)`. Preemption only activates if the winning Rec also matches the patient; an unmatched winner does not preempt.
- **Trace emission (append-only, post-traversal):** preemption resolution runs as a post-traversal step after the guideline loop in `evaluate()` completes, before `flat_recommendations` / `recommendations_by_guideline` are derived. For each firing preemption, the evaluator appends a `preemption_resolved` event to `trace.events` (continuing the monotonic `seq`) with payload `{preempted_rec_id, winning_rec_id, edge_priority, reason}`. F21 established an append-only convention; prior `recommendation_emitted` events are NOT mutated.
- **Derivation enhancement:** `flat_recommendations` and `recommendations_by_guideline` derivations in `evaluate()` include a `preempted_by` field per Rec (null if not preempted, `winning_rec_id` string if preempted). The field is computed by scanning the newly-appended `preemption_resolved` events during derivation. Gives consumers ergonomic access to preemption state without requiring trace-event traversal.
- **Preempted Recs stay in the trace.** They are not removed. Consumers (UI, harness) can filter. This keeps the trace auditable.
- **Determinism preserved:** adding `PREEMPTED_BY` edges must not change trace order for fixtures that don't trigger preemption. Regression against v0 statin fixtures and F23 standalone cholesterol fixtures is required.
- **Cross-edges live in their own seed file.** Not in `statins.cypher` or `cholesterol.cypher`. This keeps each guideline authored in isolation; cross-edges are reviewable as a unit.
- **Single-cross-edge rule per Rec pair.** No multiple `PREEMPTED_BY` edges between the same two Recs. Enforce with a uniqueness check at seed time.

## Verification targets

- ADR 0018 merged before this PR opens.
- `cypher-shell < graph/seeds/cross-edges-uspstf-accaha.cypher` runs clean after both guideline seeds.
- `MATCH ()-[r:PREEMPTED_BY]->() RETURN count(r)` returns the expected count (documented in `preemption-map.md`).
- v0 statin fixtures: unchanged traces (no preemption fires because no ACC/AHA Recs match).
- F23 cholesterol fixtures: unchanged traces (no preemption from the other direction since USPSTF Recs also don't match these patient profiles).
- Cross-domain fixtures: `preemption_resolved` events present and correct.
- Transitive preemption test: constructed graph with A → B → C triggers evaluator error/warning.
- `cd evals && uv run python -m harness.runner --fixture cross-domain/case-01 --arm c` runs clean and scores ≥ 4.0 on completeness and integration.

## Definition of done

- ADR 0018 written, reviewed, merged.
- All scope files exist and match constraints.
- All verification targets pass locally.
- Preemption map reviewed for clinical accuracy.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- KDIGO `MODIFIES` edges (F26).
- Preemption across more than 2 guidelines simultaneously. (Resolves pairwise; if multiple winners match, the one with highest priority wins.)
- UI rendering of preemption (F29).
- Preemption based on anything other than matching patients. No population-level preemption; only Rec-on-Rec for patients where both match.
- Live editing of priority values at runtime. Priorities are graph-time data.

## Design notes (not blocking, worth review)

- **Why cross-edges as a separate seed:** authoring guideline seeds independently keeps the Phase 2 discipline intact. Reviewers can look at `cross-edges-*.cypher` and understand the full connective tissue without reading guideline internals. Scales as more guidelines land: `cross-edges-uspstf-kdigo.cypher`, `cross-edges-accaha-kdigo.cypher`, etc.
- **Priority integers vs. labels:** integers let you interpolate if a future guideline needs to sit between existing priorities. Labels ("high", "medium", "low") are initially clearer but inflexible. Going with integers per the ADR.
- **The "both apply" case with different thresholds.** Example: primary prevention, LDL 160, ASCVD risk 8%. USPSTF Grade B (≥10%) does not match. ACC/AHA (≥7.5% borderline with enhancers) does. No preemption needed; one Rec matches and the other doesn't. Preemption fires only when both match.
- **What about conflicting Recs that agree?** Secondary prevention: USPSTF silent (not primary prevention scope), ACC/AHA prescribes high-intensity statin. USPSTF Recs don't match, so no preemption edge needed. This is the cleanest case and it works by default.
- **Preempted Recs in the output action list:** F30 will render preempted Recs dimmed with a `(superseded by X)` annotation. For the eval harness, Arm C's serialized context includes the preemption events; it's the Arm C story that "the graph knows these interact."
