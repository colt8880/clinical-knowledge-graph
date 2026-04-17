# 20: Shared clinical entity layer

**Status**: pending
**Depends on**: v0 shipped (all v0 features merged)
**Components touched**: graph / api / docs
**Branch**: `feat/shared-clinical-entities`

## Context

Today, `Medication`, `Condition`, `Observation`, and `Procedure` nodes are created per-guideline inside each seed file. In v1, multiple guidelines will reference the same entities (atorvastatin appears in both USPSTF and ACC/AHA; diabetes type 2 appears in USPSTF risk factors and will appear in KDIGO albuminuria triggers). Each clinical entity must resolve to a single canonical node regardless of which seed authored it.

This is the foundation feature for v1. Every subsequent feature assumes shared entities exist. Ship this first and do not break v0 determinism.

## Required reading

- `docs/build/v1-spec.md` — v1 macro spec; sets the shared-entity requirement.
- `docs/specs/schema.md` — current node/edge spec; will be amended in this feature.
- `docs/decisions/0002-*.md` — FHIR + standard code alignment decision; primary-key strategy derives from this.
- `graph/seeds/statins.cypher` — existing seed that will be refactored.
- `evals/fixtures/statins/` — regression target; all 5 v0 fixtures must still pass their expected traces.
- **`docs/decisions/0017-shared-clinical-entity-coding.md`** — NEW ADR authored as part of this feature. Formalizes the code-system strategy: single-system primary keys for Medication (RxNorm) / Observation (LOINC) / Procedure (CPT); multi-coding per FHIR `CodeableConcept` for Condition (SNOMED + ICD-10-CM). Documents why Condition is treated specially. MUST be merged before this feature's PR opens. Draft it on a short-lived branch, review, merge, then open the F20 PR.

## Scope

- `docs/decisions/0017-shared-clinical-entity-coding.md` — NEW ADR; documents the code-system strategy per entity type (single-system for Medication/Observation/Procedure, multi-coding for Condition), the rationale (FHIR alignment, EHR reality), and the seed-time uniqueness check design. Merged on its own branch before the rest of this feature's PR opens.
- `graph/seeds/clinical-entities.cypher` — new; canonical registry of shared clinical entities used by v0 + v1 guidelines. Loaded first by the seed runner.
- `graph/seeds/statins.cypher` — refactor to `MERGE` against canonical entities instead of `CREATE`. Keep Rec and Strategy nodes in this seed.
- `graph/constraints.cypher` — add uniqueness constraints on primary keys for each entity type.
- `scripts/seed.sh` (or equivalent) — updated order: constraints → clinical-entities → guideline seeds.
- `docs/specs/schema.md` — document the primary-key convention and the "shared entity vs. guideline-scoped" split.
- `docs/contracts/schema.json` (if exists) or equivalent contract file — reflect the new uniqueness constraints.
- `docs/reference/schema-reference.md` — list canonical entity primary keys.
- `api/app/db.py` or node resolvers — handle the new label scheme if anything currently assumes a single label per node.
- `api/tests/test_entities.py` — new; asserts canonical entities exist and match expected codes after seed.
- `evals/fixtures/statins/*/` — re-run expected traces; if any diff, investigate before accepting.

## Constraints

- **Primary keys (single-coding):** `Medication` keyed on RxNorm RxCUI, `Observation` on LOINC code, `Procedure` on CPT code. Stored as string properties `code` + `code_system` per node. Uniqueness constraint on (`code`, `code_system`) per label.
- **`Condition` uses multi-coding.** Mirrors FHIR `CodeableConcept`. Each `Condition` node carries a `codings` list of `{system, code}` objects. Author SNOMED CT AND ICD-10-CM on every Condition used in v1 fixtures where both exist. MERGE semantics: `MATCH (c:Condition) WHERE ANY(coding IN c.codings WHERE coding.system = $sys AND coding.code = $code)`. Uniqueness enforced per-coding via a seed-time check: no two Condition nodes may share any `(system, code)` pair. This supports matching against patient data that arrives with either coding system without requiring a downstream crosswalk lookup.
- **Domain labels:** add `:USPSTF` to all existing v0 guideline-scoped nodes (Guideline, Recommendation, Strategy). Shared entity nodes do **not** get domain labels; they are global.
- **MERGE semantics:** guideline seeds MUST use `MERGE` with `ON CREATE SET ... ON MATCH SET ...` when referencing shared entities. `CREATE` on a shared entity is a bug.
- **Backwards compat:** v0 fixtures must produce byte-identical traces after this refactor. If they don't, stop and investigate before merging.
- **No evaluator changes in this feature.** The evaluator still runs single-guideline. F21 adds multi-guideline traversal.
- **Deterministic seed order.** Constraints first (idempotent), then clinical entities (MERGE by code), then guideline seeds (MERGE entities, CREATE Rec/Strategy).
- **Code coverage:** every shared entity must have a real code. No placeholder ids. If an entity lacks a standard code in v1 scope, push it back to guideline-scoped until a code is assigned.

## Verification targets

- `cypher-shell < graph/seeds/clinical-entities.cypher` runs clean twice in a row (idempotent).
- `MATCH (m:Medication) WHERE m.code_system = "RxNorm" AND m.code IS NULL RETURN count(m)` returns 0.
- `MATCH (c:Condition) WHERE c.codings IS NULL OR size(c.codings) = 0 RETURN count(c)` returns 0.
- `MATCH (c:Condition) WHERE NONE(coding IN c.codings WHERE coding.system = "SNOMED") RETURN c` returns only Conditions that legitimately lack SNOMED (documented exceptions); all Conditions referenced by US-based fixtures carry ICD-10-CM.
- Multi-coding uniqueness test: constructed test graph with two Condition nodes sharing an ICD-10-CM code raises at seed time.
- Constraint queries: `SHOW CONSTRAINTS` lists uniqueness constraints on Medication, Observation, and Procedure labels; Condition uniqueness enforced by the seed-time check rather than a Neo4j native constraint (native constraints don't support list-element uniqueness directly).
- Running v0 evaluator against all 5 statin fixtures produces expected traces (`cd api && uv run pytest evals/` exits 0).
- Every existing statin Rec/Strategy node has the `:USPSTF` label: `MATCH (r:Recommendation) WHERE NOT r:USPSTF RETURN count(r)` returns 0.
- Each shared medication node is referenced by at least one guideline seed (`MATCH (m:Medication) WHERE NOT (m)<-[:INCLUDES_ACTION|TARGETS]-() RETURN m` returns 0 — no orphans).

## Definition of done

- ADR 0017 written, reviewed, merged on its own branch before this feature's PR opens.
- All scope files exist and match constraints.
- All verification targets pass locally, including the constructed-duplicate Condition seed-time uniqueness failure case.
- Tests: unit for constraint assertions; unit for the Condition multi-coding uniqueness check (positive + negative); integration run of v0 statin fixtures confirms trace determinism preserved.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Multi-guideline evaluator traversal (F21).
- Cross-guideline edges (`PREEMPTED_BY`, `MODIFIES`) (F25, F26).
- New guideline content (F23, F24).
- UI filtering on domain labels (F28).
- Migrating the schema spec to support guidelines-as-first-class entities with versioning; v1 keeps the current approach.

## Design notes (not blocking, worth review)

- **Code-system ambiguity:** some statins have a class RxCUI and per-strength RxCUIs. v0 uses class-level. Keep class-level in v1; add a comment in `clinical-entities.cypher` documenting the choice.
- **Entity-layer scope:** this feature creates canonical nodes for entities referenced by the v0 statin model + entities known to be needed by ACC/AHA cholesterol and KDIGO (e.g., `ezetimibe`, `CKD stage 3a`). Pre-populating known v1 entities here avoids seed-order churn in F23/F24.
- **Condition vs. Observation for eGFR:** eGFR is an `Observation` (LOINC 48642-3 or similar). CKD stage is a `Condition` with both SNOMED and ICD-10-CM codings (e.g., SNOMED 433144002 + ICD-10-CM N18.30 for CKD 3a, unspecified). Both get nodes; the `MODIFIES` edge class in F26 operates on either.
- **Why multi-coding for Condition but not Medication/Observation/Procedure.** Condition is the one entity type where two major US coding systems (SNOMED and ICD-10-CM) genuinely compete in real patient data. SNOMED is FHIR-preferred; ICD-10-CM is what EHRs actually carry from billing workflows. Multi-coding avoids downstream crosswalk maintenance. RxNorm has no ICD-analog for meds; LOINC has no serious competitor for labs; CPT is the US billing code for procedures (SNOMED procedure coverage exists but is uneven). Treating Condition specially matches FHIR `CodeableConcept` semantics directly and costs little.
- **Seed-time uniqueness check for Condition.** Neo4j doesn't natively enforce uniqueness on list element contents. The seed runner runs a Cypher check at the end of `clinical-entities.cypher`: `MATCH (a:Condition), (b:Condition) WHERE a <> b AND ANY(c1 IN a.codings WHERE ANY(c2 IN b.codings WHERE c1.system = c2.system AND c1.code = c2.code)) RETURN count(*) = 0`. If it returns false, the seed script exits non-zero.
