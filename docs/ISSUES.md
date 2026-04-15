# Known issues and deferred work

Snapshot of spec gaps, open questions, and intentional deferrals. Move items to GitHub issues once the build starts; keep this file as a summary and link out.

## v0 (statins) open questions

### Evaluator

- **`most_recent_observation_value` on missing data.** Three-valued logic returns `unknown`. The predicate then resolves per its `missing_data` policy. Need to pick the default for LDL / TC / HDL — lean `unknown_is_false` so a Rec without a lipid panel is `insufficient_evidence` rather than automatically emitted. Pin before first evaluator implementation.
- **Most-recent ordering tiebreaker when two observations share `effective_date`.** Proposed: deterministic lexicographic tiebreak by `id`. Pin in `predicate-dsl.md` before evaluator writes the first event.
- **Unit coercion for value quantities.** `mm[Hg]` vs `mmHg`, `mg/dL` casing. Lean evaluator-side normalization over strict adapter validation.
- **`risk_score_lookup` when supplied value is stale.** v0 has no freshness check; `risk_scores.ascvd_10yr` is trusted as-of `evaluation_time`. Document the assumption.

### Patient context

- **Error vs. abstain on `require`-policy failure.** Lean structured `evaluation_aborted` event inside the trace plus an HTTP 200 response over an HTTP 4xx. Eval tab can render the reason.
- **Clock-skew tolerance for `effective_date > evaluation_time`.** Lean no grace window for v0.
- **Ancestry coding.** `ancestry: ["non_hispanic_white" | "black_or_african_american" | "other"]` is v0 enough for ASCVD Black vs non-Black, but the code set is ad hoc. Map to OMB race/ethnicity or SNOMED ancestry codes before we ingest a second risk calculator.

### Trace + recommendations

- **Derived recommendation shape when a Rec is not emitted.** Current plan: the derived list only shows emitted Recs; exits show up in the trace but not in the list. Confirm this is what the Eval tab should render in the recommendations strip.
- **Stable `event_id` assignment.** Proposed: monotonic integer index within a trace. Good enough for v0 UI; document in `eval-trace.md`.

### UI

- **URL state format for the Explore tab.** Lean `?pinned=<id>&expanded=<id1>,<id2>`. Document once the first deep link lands.
- **Graph layout stability.** Cytoscape re-layouts on data change can move nodes around. Pin a seeded layout (cose-bilkent with a fixed random seed) or cache positions.

## v0 intentional deferrals

- **Live ASCVD / Pooled Cohort Equations calculation.** Fixtures supply `risk_scores.ascvd_10yr`. Un-defer when the PCE implementation lands; keep supplied-score path for test isolation.
- **Cross-guideline preemption.** Single guideline in v0.
- **Cascade (`TRIGGERS_FOLLOWUP`).** Schema supports it; evaluator doesn't exercise it.
- **`expects` result-conditional predicates.** Schema supports; evaluator doesn't exercise.
- **Historical replay across graph versions.** Single graph version in v0.
- **LLM-assisted ingestion.** Hand-authored for v0; un-archive `/ingestion` when this lands.
- **Review-and-flag workflow.** Old `review-workflow.md` archived. Re-introduce after v0 ships.

## Deferred predicates (post-v0)

- Trend primitives: rate-of-change, average-of-last-n, slope (HTN treatment targets, A1c trajectory, eGFR decline).
- Dosing predicates: `is_at_target_dose`, `dose_above` (HFrEF, diabetes treatment).
- Sequenced / ordered events: "obs X followed by obs Y within Z days" (LDCT follow-up).
- Encounter context: `seen_in_encounter_type`, `in_inpatient_setting`.
- Family history composites (removed from v0 catalog; restore for BRCA, Lynch).

## Deferred patient-context fields (post-v0)

- Family history (removed from v0 schema; statin Grade B doesn't need it).
- Pregnancy record (ADR 0008 accepted, deferred).
- Immunization, allergy, sexual history, IPV history, screening result, genetic finding, encounter, preference, prognosis, substance use, alcohol use.
- Dosage + cumulative exposure on medications.
- Care plans, goals, advance directives, code status.
- Adherence / refill-gap signals.

## Process and tooling

- Tag-cutting workflow for `spec/vN-YYYY-MM-DD`. Document when the first tag is cut.
- OpenAPI → TypeScript codegen wiring in CI for `/ui`.
- JSON Schema validation of `PatientContext` at API ingress.
- ADR numbering collisions prevented by convention only.

## Reviewer / provenance gaps

- Reviewer identity format (string vs. structured user record) unpinned in `specs/schema.md`. Pin before the first LLM-drafted node lands.
- Value-set registry storage decision: external to the graph per spec, but storage medium unpinned. Decide before seeding a second guideline.
