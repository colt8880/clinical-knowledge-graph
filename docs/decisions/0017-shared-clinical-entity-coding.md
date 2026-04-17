# 0017. Shared clinical entity coding strategy

Status: Accepted
Date: 2026-04-17
Supersedes: None
Paired with: F20 (shared clinical entity layer)

## Context

v0 creates clinical entity nodes (`Medication`, `Condition`, `Observation`, `Procedure`) inline in each guideline seed file. In v1, multiple guidelines reference the same entities — atorvastatin appears in both USPSTF statins and ACC/AHA cholesterol; diabetes type 2 appears in USPSTF risk factors and will appear in KDIGO. Each entity must resolve to a single canonical node regardless of which seed authored it.

This requires a primary-key strategy per entity type: how do seeds `MERGE` against existing entities, and how does the evaluator match patient data against entity codes?

The coding landscape is not uniform across entity types. Medications have a single dominant US coding system (RxNorm). Observations have LOINC. Procedures have CPT. But Conditions genuinely straddle two major systems: SNOMED CT (FHIR-preferred) and ICD-10-CM (what EHRs carry from billing workflows). A uniform single-system strategy would force downstream crosswalk maintenance for Conditions; a uniform multi-system strategy would add unnecessary complexity to entity types where one system dominates.

## Decision

### Single-system primary keys: Medication, Observation, Procedure

Each node carries two new string properties that together form the primary key:

| Entity type | `code_system` | `code` | Source |
|-------------|---------------|--------|--------|
| Medication  | `RxNorm`      | RxCUI (class-level in v0/v1) | NLM RxNorm |
| Observation | `LOINC`       | LOINC code (panel code for composites) | Regenstrief LOINC |
| Procedure   | `CPT`         | CPT code (most representative for the concept) | AMA CPT |

A Neo4j uniqueness constraint enforces `(code, code_system)` per label. Seeds `MERGE` on `id` (the internal stable identifier) and set `code` + `code_system` via `ON CREATE SET`. The constraint prevents two nodes of the same type from sharing a primary code.

Existing code-array properties (`rxnorm_codes`, `loinc_codes`, `cpt_codes`, `snomed_codes`) are **retained** alongside the primary key. The evaluator uses these arrays for broad matching against patient data (a single concept node may match multiple surface codes in an EHR). The primary key is the canonical identity for seed-time deduplication; the code arrays are the matching surface.

### Multi-coding: Condition

`Condition` nodes carry a `codings` list property that encodes both SNOMED CT and ICD-10-CM codes in a single flat list. Each entry is a concatenated string in the format `SYSTEM:CODE`:

```
codings: ['SNOMED:394659003', 'SNOMED:429559004', 'ICD10:I20', 'ICD10:I21', 'ICD10:I25']
```

**Why concatenated strings instead of a list of maps?** Neo4j property values support lists of primitives (strings, integers, floats, booleans) but not lists of maps. Concatenated strings are queryable with standard Cypher list predicates (`IN`, `ANY()`) without requiring APOC or JSON parsing.

**MERGE semantics for Condition:**

```cypher
MATCH (c:Condition) WHERE 'SNOMED:394659003' IN c.codings
```

**Seed-time uniqueness check:** Neo4j cannot enforce native uniqueness constraints on list-element contents. Instead, `clinical-entities.cypher` runs a post-seed check:

```cypher
MATCH (a:Condition), (b:Condition)
WHERE a <> b AND ANY(c IN a.codings WHERE c IN b.codings)
RETURN count(*)
```

If the result is not 0, the seed script exits non-zero. This prevents two Condition nodes from sharing any `(system, code)` pair.

Existing code-array properties (`snomed_codes`, `icd10_codes`) are **retained** alongside `codings`. The evaluator's `_extract_codes()` reads these arrays; no evaluator changes are needed in F20.

### Domain labels

Guideline-scoped nodes (`Guideline`, `Recommendation`, `Strategy`) receive a domain label (`:USPSTF`, `:ACC_AHA`, `:KDIGO`) identifying their source guideline. Shared clinical entity nodes do **not** get domain labels — they are global reference data.

## Alternatives considered

### Uniform single-system for all entity types (including Condition)

Pick SNOMED as Condition's single primary key. Rejected: ICD-10-CM is ubiquitous in US EHR billing data. Requiring a SNOMED→ICD-10 crosswalk at patient-data ingestion adds a maintenance burden and a failure mode (unmapped codes). Multi-coding on Condition avoids this.

### Uniform multi-coding for all entity types

Give Medication, Observation, and Procedure the same `codings` list as Condition. Rejected: RxNorm has no serious competitor for US medication coding; LOINC has no serious competitor for US lab observations; CPT is the dominant US procedure billing code. Multi-coding adds complexity without value for these types.

### Store codings as JSON string property

`codings_json: '[{"system":"SNOMED","code":"394659003"}, ...]'` parsed with `apoc.convert.fromJsonList`. Rejected: requires APOC dependency; Cypher list operations (`IN`, `ANY()`) don't work on JSON strings natively; fragile to parse errors.

### Store codings as parallel arrays

`coding_systems: ["SNOMED", "SNOMED", "ICD10"]` and `coding_codes: ["394659003", "429559004", "I20"]`. Rejected: positional coupling is error-prone; harder to query than concatenated strings.

## Consequences

- Seeds `MERGE` clinical entities by `id` with `ON CREATE SET` / `ON MATCH SET`. Primary-key properties (`code`, `code_system` for single-coding; `codings` for Condition) are set on creation.
- `graph/seeds/clinical-entities.cypher` is the canonical registry, loaded before any guideline seed.
- Guideline seeds reference shared entities via `MERGE` on `id` (not `CREATE`). A `CREATE` on a shared entity is a bug.
- The evaluator continues to use existing code-array properties for patient-data matching. No evaluator changes in F20.
- Future guidelines (F23, F24) add their entities to `clinical-entities.cypher` and reference them from their guideline seeds.
- Domain labels enable UI filtering (F28) and evaluator scoping (F21) without modifying entity nodes.

## Related

- `docs/specs/schema.md` — updated with primary-key convention
- `docs/reference/schema-reference.md` — updated with new attributes
- ADR 0002 (FHIR-aligned clinical entities) — this ADR extends the coding strategy established there
- F20 spec (`docs/build/20-shared-clinical-entity-layer.md`)
