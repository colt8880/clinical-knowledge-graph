# v1: Multi-guideline graph + three-arm eval harness

**Status**: pending
**Supersedes scope in**: ADR 0014 (v0 scope)
**New ADRs required** (draft alongside the corresponding feature; merge before the feature's PR):
- ADR 0017: shared clinical entity coding (paired with F20)
- ADR 0018: preemption precedence (paired with F25)
- ADR 0019: MODIFIES edge semantics (paired with F26)
- ADR 0020: three-arm eval methodology (paired with F27)

## Purpose

v0 proved one guideline can be modeled as a traversable graph and evaluated deterministically. v1 proves the thesis: **a graph-retrieved context produces more accurate clinical next-best-action recommendations than vanilla LLMs or flat RAG**, specifically on multi-morbidity patients where decision points interact across guidelines.

Two work streams of roughly equal weight:

1. **Content**: add ACC/AHA 2018 Cholesterol and KDIGO 2024 CKD as independent subgraphs, then wire cross-guideline edges. This activates `PREEMPTED_BY` (schema-only in v0) and demonstrates graph-shaped reasoning that flat retrieval cannot replicate.
2. **Measurement**: build a three-arm eval harness using Braintrust. Without this, adding content is decoration. With this, content becomes thesis proof.

v1 is done when the harness shows Arm C (graph context) beating Arm B (flat RAG) on the multi-domain fixture set by a measurable margin, on a preregistered rubric.

## Scope

### In

- ACC/AHA 2018 Cholesterol guideline, hand-authored, as a standalone subgraph in the same Neo4j database.
- KDIGO 2024 CKD guideline, hand-authored, as a standalone subgraph.
- Cross-guideline edges between USPSTF statins / ACC/AHA cholesterol / KDIGO CKD. Activates `PREEMPTED_BY` and introduces a cross-guideline `MODIFIES` edge class.
- Shared clinical entity layer: `Medication`, `Condition`, `Observation`, `Procedure` nodes resolve to a single canonical instance across guideline seeds (statin-X referenced by USPSTF and ACC/AHA is the same node). `Condition` nodes use FHIR-style multi-coding (SNOMED + ICD-10-CM) so patient data carrying either system matches cleanly; other entity types use single-system primary keys (RxNorm / LOINC / CPT).
- Multi-guideline evaluator traversal with unified `EvalTrace` emission.
- Three-arm eval harness with Braintrust integration: vanilla LLM, flat RAG, graph-context LLM.
- Rubric-based LLM-judge scoring + deterministic structural checks.
- UI additions: domain filter on Explore; preemption visualization on Eval; multi-guideline recommendation list in Eval output.
- New fixtures: cholesterol-only, CKD-only, and cross-domain (statin + cholesterol conflict; CKD modifies statin; CKD modifies cholesterol).

### Out (deferred to v2 or later)

- ADA Standards of Care, ACIP immunizations, other USPSTF grades beyond statins.
- The full 5-domain multi-morbidity archetype. v1 stays at 2-domain overlaps.
- Live ASCVD calculation via Pooled Cohort Equations. Fixtures still supply `risk_scores.ascvd_10yr` directly.
- LLM-assisted ingestion. Both new guidelines are hand-authored.
- Historical replay across graph versions.
- Cascade-triggered follow-up Recs; `expects` result-conditional semantics.
- Oncology, psychiatry, obstetrics, pediatrics.
- Multi-tenant access control, any PHI work.

## Guideline selection rationale

**Why ACC/AHA Cholesterol first:** direct overlap with USPSTF 2022 statins creates natural preemption scenarios (ACC/AHA recommends statin for secondary prevention where USPSTF stays silent; ACC/AHA has LDL thresholds USPSTF does not). This activates the `PREEMPTED_BY` schema in v1 rather than deferring it again. Existing statin fixtures extend with minor additions rather than requiring a new patient archetype.

**Why KDIGO CKD second:** CKD is connective tissue. eGFR modifies statin dosing and cholesterol management; it will modify diabetes med selection in v2. Adding it now forces the evaluator and schema to handle cross-domain modifier edges, which is the capability v2 builds on. Without a second downstream guideline (diabetes) in v1, CKD's value is partially realized, but the architectural investment pays off in v2.

**Why not ADA, ACIP, additional USPSTF:**
- ADA: better in v2 paired with KDIGO (CKD modifies diabetes med selection is the canonical cross-guideline example).
- ACIP: pure lookup, flat RAG competes well, does not differentiate Arm B from Arm C.
- Other USPSTF grades: similar to ACIP, most are conditional lookup with limited cross-guideline interaction.

## Architecture changes

### Schema

- **Activate `PREEMPTED_BY`** cross-guideline edges. Requires ADR on precedence rules (specificity? publication recency? explicit numeric priority? a combination). Recommend explicit `priority` integer on the edge with a tie-break on `published_at`, but the ADR makes this concrete.
- **Shared clinical entity layer.** Today each guideline seed creates its own `Medication` and `Condition` nodes. In v1, seeds `MERGE` against a canonical registry (probably `/graph/seeds/clinical-entities.cypher`, loaded first). Guideline-specific nodes (Recs, Strategies) still live per-guideline; shared entities resolve globally. `Condition` nodes carry a `codings` list (FHIR `CodeableConcept`-style) with both SNOMED and ICD-10-CM populated; MERGE matches on any `(system, code)` pair. Medication / Observation / Procedure use single-system primary keys (RxNorm / LOINC / CPT). See F20 for full semantics.
- **Domain labels.** Add `:USPSTF`, `:ACC_AHA`, `:KDIGO` labels to all guideline-scoped nodes for filtering in the UI and evaluator. Shared entity nodes do not get domain labels.
- **Trace event extensions.** New event types (schema is snake_case, matching what shipped in F21): `guideline_entered`, `guideline_exited`, `cross_guideline_match`, `preemption_resolved`. Existing events gain `guideline_id` provenance. All new events are appended to the trace; F21 established an append-only convention and F25/F26 honor it (no mutation of prior events).
- **New edge class: `MODIFIES`** from a Condition or Observation node (e.g., CKD stage 3) to a Strategy or Recommendation node in a different guideline. This is distinct from `PREEMPTED_BY` (which removes a Rec entirely) and encodes "consider this, but adjust."

### Evaluator

- Traverses all guidelines in scope, not one.
- Emits a unified trace; every event tagged with originating guideline.
- Resolves preemption using the precedence rules from the ADR.
- Processes `MODIFIES` edges as annotations on the relevant Rec rather than as gating logic (modifiers surface in the trace but do not block matching).
- Determinism constraint preserved: same `PatientContext` + same graph version + same evaluator version produces a byte-identical trace, even across multiple guidelines. This means guideline traversal order must be deterministic (alphabetical by guideline id).

### API

- `/api/evaluate` returns multi-guideline rec list plus full trace.
- New endpoint: `GET /context/{fixture_id}` returns the subgraph relevant to a fixture, formatted for LLM context injection (Arm C input). Shape defined alongside the harness build.
- Contracts (`docs/contracts/`) updated in the same PR as the schema change.

### UI

- **Explore tab:** domain filter control (multi-select: USPSTF / ACC/AHA / KDIGO). Default all-on. Filtering hides nodes without the selected domain labels; shared entity nodes always visible.
- **Eval tab:** preemption visualization. Preempted Rec rendered dimmed with a visible `PREEMPTED_BY` edge to the winning Rec. Modifier edges rendered as annotations on affected Recs. Trace stepper shows preemption and modifier events inline.
- **Eval tab:** recommendation output pane handles multi-guideline list with per-Rec guideline badge.

## Eval harness

### Braintrust free tier

Recommendation: **use Braintrust free tier**. Features we need and expect to find in free tier at v1 scale:

- Datasets (fixture registry, versioned).
- Experiments with multiple scorers per run.
- Side-by-side run comparison for the three arms.
- Logging for LLM calls with cost/token tracking.

Before building against it, verify current free tier limits (events per month, seat count, retention). v1 scale estimate: ~20 fixtures × 3 arms × ~5 iterations during development = ~300 runs. Comfortably under any free-tier cap I've seen, but worth confirming.

**Fallback if Braintrust free tier doesn't work:** local scoring with results exported to a jsonl log; comparison via a simple diff script. Less polished, no worse for the thesis. Do not gate v1 on Braintrust specifically.

### Three arms

| Arm | Context supplied to LLM |
|-----|-------------------------|
| A   | `PatientContext` only. No guideline material. Tests what the LLM knows from training. |
| B   | `PatientContext` + top-k chunks from guideline prose (flat RAG over `docs/reference/guidelines/*.md` and raw guideline PDFs/text). |
| C   | `PatientContext` + graph-retrieved context: the `EvalTrace` summary + the subgraph rooted at matched Recs, serialized. |

All three arms call the same LLM with the same system prompt asking for a structured next-best-action list. Only the context input varies. Same LLM, same temperature (0 or low), same max tokens.

### Scoring

- **Deterministic structural checks** per fixture: does the output include expected Rec IDs? Does it avoid contraindicated recommendations? Binary pass/fail, scored independently of the LLM judge.
- **Rubric-based LLM judge** per fixture: completeness, clinical appropriateness, correct prioritization, correctly handles preemption/modifiers. 1-5 per dimension. Use a separate LLM from the one being evaluated to reduce self-preference bias.
- **Final score:** composite per arm per fixture, plus aggregate per arm.

Rubric lives in `evals/rubric.md` and gets versioned. Rubric changes trigger re-scoring; do not compare scores across rubric versions.

### Fixture structure

Per-fixture dir grows:

```
evals/fixtures/<guideline>/<fixture_id>/
  patient-context.json
  expected-trace.json              # v0
  expected-actions.json            # NEW: curated NBA list, rationale per action
  arms/
    a/output.json
    b/output.json
    c/output.json
  scores.json                      # NEW: per-arm composite score
```

Arm outputs cached so eval runs are reproducible. Cache invalidated when the arm's input (context, prompt, model) changes.

### Target fixture count for v1

- USPSTF statins: existing 5 + 2 new (secondary prevention exit refined, statin-intolerant case).
- ACC/AHA Cholesterol: 4 (familial hypercholesterolemia, secondary prevention with LDL still elevated, statin-naive with LDL ≥190, statin-naive with diabetes).
- KDIGO CKD: 3 (CKD 3a, CKD 3b with albuminuria, CKD 4).
- Cross-domain: 4 (statin + cholesterol preemption; CKD 3b modifies statin intensity; CKD + cholesterol combined; post-MI on statin with CKD 3a).

Total: ~18 fixtures. Enough to show signal; small enough to hand-curate action lists.

## Phasing and feature breakdown

Three phases, sequenced so each phase validates before the next builds on it. Features numbered in the 20s to stay clear of v0's build range.

### Phase 1: Foundation (shared entities, multi-guideline evaluator, harness skeleton)

Must ship before any guideline content.

- **F20: Shared clinical entity layer refactor.** New `clinical-entities.cypher` seed; statin seed updated to `MERGE` against it; backfill existing graph. `graph/`, `docs/specs/schema.md`, `docs/contracts/`.
- **F21: Multi-guideline evaluator + trace extension.** Evaluator traverses forest; trace events carry `guideline_id`; new event types stubbed. `api/`, `docs/specs/eval-trace.md`, `docs/contracts/eval-trace.schema.json`.
- **F22: Eval harness skeleton.** Braintrust integration, fixture format extension, three-arm runner, rubric v1, Arm A + Arm B + Arm C running against existing v0 fixtures (no new guidelines yet). Baseline numbers for statins-only captured. `evals/harness/`, `evals/rubric.md`.

### Phase 2: Independent guideline graphs

Build each guideline standalone, validate with single-guideline eval run, before wiring cross-edges.

- **F23: ACC/AHA 2018 Cholesterol subgraph.** `graph/seeds/cholesterol.cypher`, `docs/reference/guidelines/cholesterol.md`, 4 fixtures, single-guideline eval run. No cross-edges to USPSTF yet.
- **F24: KDIGO 2024 CKD subgraph.** `graph/seeds/kdigo-ckd.cypher`, `docs/reference/guidelines/kdigo-ckd.md`, 3 fixtures, single-guideline eval run.

Gate: before moving to Phase 3, each subgraph's Arm C should match `expected-actions.json` on its own fixtures. If a subgraph can't correctly recommend against single-domain patients, adding cross-edges won't fix it.

### Phase 3: Connection and cross-domain validation

- **F25: Preemption precedence + cross-edges USPSTF ↔ ACC/AHA.** ADR on precedence rules; `PREEMPTED_BY` edges authored; evaluator resolves preemption; 2 new cross-domain fixtures.
- **F26: Cross-edges KDIGO → USPSTF and KDIGO → ACC/AHA.** `MODIFIES` edges; evaluator emits modifier events; 2 new cross-domain fixtures.
- **F27: Full harness run + thesis test.** All 18 fixtures; all three arms; Braintrust experiment; scorecard. This is the feature that proves or disproves the thesis.

### Phase 4: UI polish

Low-risk, parallelizable with Phase 3.

- **F28: Domain filter on Explore tab.**
- **F29: Preemption and modifier visualization on Eval tab.**
- **F30: Multi-guideline rec list rendering.**

## Success criteria

v1 ships when all of the following hold:

1. All three arms run end-to-end on the full 18-fixture set without manual intervention.
2. Trace determinism preserved across multi-guideline traversal: re-running any fixture produces a byte-identical trace.
3. Each standalone guideline graph passes its single-guideline eval gate in Phase 2 before Phase 3 starts.
4. **Arm C beats Arm B on the aggregate rubric score on the cross-domain fixture subset by a preregistered margin.** Margin to be set when rubric v1 is finalized; suggested floor is 0.5 points on a 5-point composite. If Arm C doesn't beat Arm B, v1 has surfaced a real finding; do not ship the UI polish phase until the gap is investigated.
5. Preemption and modifier events render correctly in the Eval UI.
6. Backlog row in `docs/reference/build-status.md` updated for every shipped feature.
7. ADRs written and accepted for preemption precedence, shared clinical entity layer, and three-arm eval methodology.

## Risks and mitigations

- **Arm C doesn't beat Arm B.** Most likely causes: graph context serialization is too terse; fixtures don't genuinely require cross-guideline reasoning; rubric under-weights integration. Mitigation: Phase 2's single-guideline eval gate catches the "graph is broken" version of this. If the gap remains after that gate, rubric and context-serialization tuning in Phase 3 rather than accepting the null result.
- **Braintrust free tier limits hit mid-v1.** Mitigation: the fallback jsonl+diff path described above. Do not architect anything Braintrust-specific that can't be ripped out.
- **Schema harmonization pass destabilizes v0 statin model.** Mitigation: F20 includes regression against v0 fixtures before the shared-entity refactor is merged. Existing fixtures must still pass their expected traces.
- **LLM-judge score drift.** Different judge model versions produce different rubric scores. Mitigation: pin the judge model and version in `evals/rubric.md`. Re-score only when rubric changes, not when dev work happens.
- **Preemption precedence rules under-specified.** Mitigation: the ADR is a hard gate on F25. No implementation until the rules are concrete.
- **Graph-context serialization for Arm C is the single biggest design variable.** Too terse and Arm C underperforms; too verbose and it looks like we're cheating. Mitigation: the contract for Arm C context lives in `docs/contracts/` and is reviewable. Document the exact serialization in the thesis write-up.

## Open questions requiring ADRs

1. **Shared clinical entity coding (ADR 0017).** Resolved: standard codes as primary keys, with `Condition` using multi-coding (SNOMED + ICD-10-CM as a `codings` list per FHIR `CodeableConcept`); Medication / Observation / Procedure use single-system primary keys (RxNorm / LOINC / CPT). ADR formalizes the decision and documents the seed-time uniqueness check. Paired with F20.
2. **Preemption precedence (ADR 0018).** Resolved: explicit `priority` integer on the `PREEMPTED_BY` edge; higher wins; tie-break on `published_at`. Default priorities: USPSTF 100, ACC/AHA 200, KDIGO 200. No transitive preemption. Paired with F25.
3. **MODIFIES edge semantics (ADR 0019).** Defines `MODIFIES` as additive cross-guideline annotation distinct from `PREEMPTED_BY`; covers the preemption-wins-over-modification rule. Paired with F26.
4. **Three-arm eval methodology (ADR 0020).** Rubric structure (4 dimensions 1-5, composite = mean), judge model pinning (Opus 4.6), cache invalidation rules, preregistered margin for success criterion #4 (≥ 0.5 composite points, Arm C over Arm B on the cross-domain subset), self-consistency check (3x judge runs, SD reporting). Paired with F27.

ADRs are drafted in short-lived branches alongside their paired feature and merged first; the feature PR references the merged ADR.

## Glossary additions

- **Arm A / B / C.** The three conditions of the v1 eval harness (vanilla LLM / flat RAG / graph-context LLM).
- **Shared clinical entity.** A `Medication`, `Condition`, `Observation`, or `Procedure` node that resolves to a single canonical instance across guideline seeds.
- **Modifier edge.** A `MODIFIES` edge from a clinical entity node to a Rec or Strategy in a different guideline; annotates but does not gate.
- **Preemption.** An active `PREEMPTED_BY` edge that removes a Rec from the evaluated result set in favor of a higher-priority Rec from another guideline.
