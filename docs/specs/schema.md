# Schema

**Read this before modifying node types, edge types, or the shape of the graph.**

The schema is split into a **knowledge layer** (Guideline, Recommendation, Strategy) and a **clinical entity layer** (FHIR-aligned reference nodes that the knowledge layer points at). Clinical entity nodes are reference data: one shared `Medication: atorvastatin` node is referenced by every Strategy that includes it.

> **v0 scope (ADR 0013, 0014): USPSTF Statin Primary Prevention 2022 only.** Several schema features defined below (cascade triggers, cross-guideline preemption, procedure-level result expectations, pregnancy top-level record) are retained in the schema but **not exercised** in v0. Keep them in the schema; do not implement evaluator branches for them in v0 unless a patient fixture needs them.

## Node types

### Knowledge layer

- **`Guideline`** — source document. Attrs: `publisher`, `version`, `effective_date`, `url`, `status`.
- **`Recommendation`** — the actionable unit. Attrs:
  - `evidence_grade` (enum: A/B/C/D/I for USPSTF; GRADE equivalents for others)
  - `intent` (enum: screening, diagnostic, treatment, surveillance, shared_decision, counseling, primary_prevention)
  - `trigger` (enum: patient_state [default], observation_result, condition_onset, medication_start) + `trigger_criteria` for non-default triggers
  - `structured_eligibility` — JSON predicate tree (authoritative) with AND/OR/NOT composition over patient state
  - `clinical_nuance` — freeform text capturing judgment-dependent guidance the LLM reasons over
  - `source_section` — string reference into the Guideline document
  - `provenance` — ingestion metadata (model version, prompt, reviewer identity, review date)
- **`Strategy`** — a coherent way of satisfying a Recommendation. Every Rec offers one or more Strategies. A Strategy aggregates one or more actions (clinical entity references) that must all be completed within their respective lookback windows for the Strategy to count as satisfied. Attrs:
  - `id` (stable, e.g., `strategy:statin-moderate-intensity`)
  - `name` — human-readable label
  - `evidence_note` — optional text specific to this combination
  - `source_section` — where in the Guideline this strategy is described
  - Rationale for nodehood: strategies are reusable, carry their own attributes beyond the sum of their actions, and "all actions together" semantics can't be expressed cleanly as edge attributes on a flat action list.

### Clinical entity layer (FHIR-aligned reference nodes)

Clinical entity nodes are **shared reference data** — one canonical node per concept, referenced by every guideline that needs it. They live in `graph/seeds/clinical-entities.cypher`, loaded before any guideline seed. Guideline seeds reference them via `MERGE` on `id`; a `CREATE` on a shared entity is a bug. Shared entities carry **no domain labels** (no `:USPSTF`, `:ACC_AHA`, etc.); they are global.

Each clinical entity node is a **semantic concept**, not a single code. Code attributes are **lists** so one node can match any surface form the concept appears as in an EHR.

- **`Condition`** — FHIR Condition; `snomed_codes[]` + `icd10_codes[]` + `codings[]` (multi-coding per ADR 0017)
- **`Observation`** — FHIR Observation; `loinc_codes[]` + `snomed_codes[]` + primary key `code` / `code_system`
- **`Medication`** — FHIR Medication; `rxnorm_codes[]` + primary key `code` / `code_system`
- **`Procedure`** — FHIR Procedure; `cpt_codes[]` + `snomed_codes[]` + primary key `code` / `code_system`

#### Primary-key conventions (ADR 0017)

Medication, Observation, and Procedure each carry a **single-system primary key** stored as `code` (string) + `code_system` (string). A Neo4j uniqueness constraint enforces `(code, code_system)` per label.

| Entity type | `code_system` | `code` value |
|-------------|---------------|--------------|
| Medication  | `RxNorm`      | RxCUI (class-level) |
| Observation | `LOINC`       | Primary LOINC code |
| Procedure   | `CPT`         | Most representative CPT code |

Condition uses **multi-coding**: a `codings` list of `SYSTEM:CODE` concatenated strings (e.g., `['SNOMED:394659003', 'ICD10:I25']`). Neo4j cannot store lists of maps, so the concatenated-string format provides native Cypher queryability (`'SNOMED:X' IN c.codings`). Uniqueness is enforced by a seed-time check rather than a native constraint (Neo4j constraints can't enforce list-element uniqueness). See ADR 0017.

Existing code-array properties (`rxnorm_codes`, `snomed_codes`, `icd10_codes`, `loinc_codes`, `cpt_codes`) are retained alongside primary keys for evaluator backward compatibility.

#### Domain labels

Guideline-scoped nodes (`Guideline`, `Recommendation`, `Strategy`) carry a domain label identifying their source: `:USPSTF`, `:ACC_AHA`, `:KDIGO`. This enables UI filtering and evaluator scoping. Shared entity nodes are global and do not carry domain labels.

If a future guideline requires distinguishing sub-types, add separate nodes of the same type and connect them with `IS_A` edges for hierarchy traversal. Do not introduce aggregate/group node types; the entity node already *is* the semantic grouping.

### Types that are explicitly NOT nodes (and why)

- `Section` — document organization artifact; captured as `source_section` string on Recommendation
- `Population` — encoded inside `structured_eligibility`
- `Criterion` — captured as `structured_eligibility` JSON + materialized edges
- `Action` — captured as `INCLUDES_ACTION` edges from Strategy to clinical entity nodes
- `EvidenceGrade` — enum attribute, not a node
- `Intervention` — redundant with Procedure/Medication/Observation

## Edge types

### From Recommendation (outbound)

- `-[:FROM_GUIDELINE]->` `(Guideline)` — provenance anchor
- `-[:FOR_CONDITION]->` `(Condition)` — what the rec is about (e.g., CVD primary prevention points to an atherosclerotic cardiovascular disease `Condition` node)
- `-[:OFFERS_STRATEGY]->` `(Strategy)` — a way to satisfy this rec. Multiple edges = interchangeable alternatives; the Rec is satisfied when *any* offered Strategy is satisfied.
- `-[:TRIGGERED_BY {criteria}]->` `(Observation | Condition | Medication)` — event trigger for non-default (non-patient_state) recs. **Not exercised in v0** (statins is patient-state only).
- `-[:EXCLUDED_BY]->` `(Condition | Procedure | Medication)` — hard exclusions materialized from `structured_eligibility` for graph traversability.
- `-[:TRIGGERS_FOLLOWUP {on}]->` `(Recommendation)` — cascade chains. **Not exercised in v0.**
- `-[:PREEMPTED_BY {condition, priority, rationale}]->` `(Recommendation)` — cross-guideline conflict resolution. **Not exercised in v0** (single guideline). Attrs remain specified for future use: `condition` (predicate to evaluate against patient state), `priority` (integer tie-breaker), `rationale` (human-readable string).

### From Strategy (outbound)

- `-[:INCLUDES_ACTION {cadence, lookback, priority, intent, expects}]->` `(Procedure | Medication | Observation)` — the component actions of the strategy. Strategy semantics are **conjunction**: *all* included actions must be satisfied within their respective lookback windows for the strategy to count as satisfied. Attrs:
  - `cadence` — ISO 8601 interval for recurrence, null for one-shot. For medications, null (initiate-and-continue is the default; re-evaluation is event-driven, not time-driven, in v0).
  - `lookback` — ISO 8601 window used to check patient history for a matching prior action. For medication actions, "has an active prescription" is the default check; lookback is used when a dated exposure window matters.
  - `priority` — urgency tier for the agent (routine, urgent, stat).
  - `intent` — screening, diagnostic, treatment, surveillance, counseling, shared_decision, primary_prevention.
  - `expects` — optional result label the matched patient record must carry for this action to count as satisfied. **Not used in v0** (statin actions are presence-based).

### Between Guidelines

- `-[:SUPERSEDES]->` `(Guideline)` — versioning; never delete superseded guidelines.

## Conventions

- **Every edge carries `source_guideline_id`, `source_section`, `effective_date`.** Edges are provenanced, not just nodes.
- **Directional reasoning.** Prefer directed relationships; avoid symmetric relations.
- **Supersession, not deletion.** When a guideline updates, add the new Guideline + new Recommendations and a `SUPERSEDES` edge. Old nodes stay in place so historical reasoning traces remain valid.
- **`structured_eligibility` is authoritative; edges are materialized.** Curation edits JSON; ingestion emits `EXCLUDED_BY` / `TRIGGERED_BY` edges for clinical entities referenced by the predicate tree. If they diverge, JSON wins and the edges get regenerated.
- **Structured vs. nuance split rule.** Hard gates (age, sex, presence/absence of a coded condition, threshold on a computed score, time-since-X) go in `structured_eligibility`. Anything requiring judgment ("individualize based on life expectancy", "shared decision making") goes in `clinical_nuance`.
- **Actions flow through Strategies.** A Recommendation never points directly at a Procedure/Medication/Observation. It points at one or more `Strategy` nodes. Single-action strategies are still Strategy nodes (with one `INCLUDES_ACTION` edge) — uniform traversal beats special cases.
- **Class-level medications are the default for v0.** USPSTF statins recommends "moderate-intensity statin therapy" without naming an agent. Model this as a Strategy that includes one `INCLUDES_ACTION` edge per acceptable class member (atorvastatin, rosuvastatin, etc.). The Strategy is satisfied when the patient is on any included member. This is a natural generalization: when a future guideline requires a specific drug, that Strategy includes only that one Medication node.
- **Counseling and shared-decision actions use `Procedure` nodes.** When a guideline prescribes a conversation or shared decision-making step (e.g., Grade C statin discussion), model it as a Strategy with one `INCLUDES_ACTION` edge (`intent: shared_decision`) pointing at a `Procedure` node coded with the appropriate SNOMED counseling/education code.

## Cadence semantics (time-based recurrence)

Time-based recurrence is modeled as state on `INCLUDES_ACTION` edges, evaluated during normal `patient_state` traversal.

**Edge attributes on `INCLUDES_ACTION`:**
- `cadence` — ISO 8601 interval (e.g., `P10Y` for colonoscopy). Null for one-shot or for medication actions whose satisfaction is "currently active."
- `lookback` — ISO 8601 duration used by the API to check patient history. For medications in v0: null (active prescription is the satisfaction check). For observations/procedures: usually equal to `cadence`.

**Evaluation rule (lives in the API, see `api-primitives.md`):**
1. Rec fires as a candidate when `trigger: patient_state` and `structured_eligibility` matches.
2. For each `Strategy` offered by the Rec:
   - For each `INCLUDES_ACTION` edge, check patient state for a matching record. Semantics differ by entity type:
     - **Medication**: satisfied when the patient has an active medication whose `rxnorm_codes` intersect the Medication node's codes. Lookback defaults to "currently active."
     - **Procedure / Observation**: satisfied when a matching record (codes intersect) exists within `lookback` from `evaluation_time`.
   - The Strategy is **satisfied** only if *every* one of its included actions is satisfied (conjunction).
3. The Rec is **up to date** if any offered Strategy is satisfied. Otherwise the Rec is **due**.
4. When a Rec is due, the API returns *all* offered Strategies so the agent can reason over them with clinical context and patient preference.

## Result-conditional satisfaction (deferred in v0)

The `expects` attribute on `INCLUDES_ACTION` is defined in the schema but not used in v0. Statin actions are presence-based: on-therapy satisfies, off-therapy does not. Result-conditional satisfaction re-activates when a guideline requires it (e.g., a negative FIT satisfying CRC screening).

The vocabulary and registry design was worked out in the CRC archive: see `docs/archive/crc-model.md` § "Result-conditional satisfaction" for prior art when this re-enters scope.

## Related docs

- Predicate DSL used in `structured_eligibility`, `trigger_criteria`, and `PREEMPTED_BY.condition`: see `predicate-dsl.md`
- API primitives that traverse this schema: see `api-primitives.md`
- Eval trace events emitted during traversal: see `eval-trace.md`
- Concrete v0 instantiation: see `docs/reference/guidelines/statins.md`
