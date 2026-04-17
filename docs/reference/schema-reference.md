# Schema Reference

Quick-reference companion to `schema.md`. `schema.md` has the rationale and conventions; this doc is the lookup table for node types, edge types, and every attribute on each.

## Nodes

### Knowledge layer

#### `Guideline`

The source document. Every Recommendation traces back to exactly one.

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable identifier, e.g., `uspstf-crc-2021`. Used in edge provenance. |
| `publisher` | string | Issuing body (USPSTF, ACS, USMSTF, NICE, CDC, etc.). |
| `version` | string | Guideline version label as published (e.g., `"2021"`). |
| `effective_date` | date | Publication / effective date of this version. |
| `url` | string | Canonical URL for the source document. |
| `status` | enum | `active` / `superseded` / `withdrawn`. Superseded guidelines are retained; supersession is also modeled via the `SUPERSEDES` edge. |

#### `Recommendation`

The actionable unit. Projects to FHIR PlanDefinition for external APIs.

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable identifier, e.g., `uspstf-crc-screen-avgrisk-50-75`. |
| `evidence_grade` | enum | `A` / `B` / `C` / `D` / `I` for USPSTF; GRADE equivalents for other guideline systems. |
| `intent` | enum | `screening` / `diagnostic` / `treatment` / `surveillance` / `shared_decision` / `counseling`. |
| `trigger` | enum | How the Rec fires. `patient_state` (default, evaluated on sweep), `observation_result`, `condition_onset`, `medication_start`. |
| `trigger_criteria` | JSON | Present only for non-default triggers. Describes the qualifying event (e.g., `{observation: fit, value: positive, window: P30D}`). Uses the predicate DSL. |
| `structured_eligibility` | JSON | Authoritative predicate tree over patient state, using AND / OR / NOT composition. Coarse-to-fine filter for candidate match. See `predicate-dsl.md`. |
| `clinical_nuance` | text | Free-form guidance that requires clinical judgment and can't be reduced to predicates. The LLM agent reasons over this. |
| `source_section` | string | Where in the parent Guideline this Rec lives (e.g., `"Recommendation Summary, Grade A"`). Not a node. |
| `provenance` | JSON | Ingestion metadata: model version, prompt id, reviewer identity, review date, any conflict notes. |

#### `Strategy`

A coherent way to satisfy a Recommendation. All component actions must be completed (conjunction semantics) for the Strategy to count as satisfied.

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable identifier, e.g., `strategy:crc-colonoscopy-alone`, `strategy:crc-flex-sig-plus-fit`. |
| `name` | string | Human-readable label surfaced in the review tool and audit logs. |
| `evidence_note` | text | Optional. Notes specific to this combination (sensitivity/specificity, patient burden, clinical context). |
| `source_section` | string | Where in the parent Guideline this Strategy is described; may differ from the parent Rec's section. |

### Clinical entity layer (FHIR-aligned reference nodes)

Shared reference data. Canonical nodes live in `graph/seeds/clinical-entities.cypher`, loaded before guideline seeds. One node per concept, referenced by every guideline that needs it. Guideline seeds reference entities via `MERGE` on `id`. Clinical entity nodes carry **no domain labels** — they are global.

**Each node is a semantic concept, not a single code.** Code attributes are **lists** so a single node can match every surface form the concept appears as in an EHR (e.g., `cond:ibd` matches both K50 Crohn's and K51 ulcerative colitis).

#### `Condition` — FHIR Condition

Multi-coding per ADR 0017. Uses `codings` list for cross-system matching.

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable internal identifier. |
| `display_name` | string | Human-readable label (e.g., `"Established atherosclerotic cardiovascular disease"`). |
| `codings` | list[string] | Multi-coding list in `SYSTEM:CODE` format (e.g., `['SNOMED:394659003', 'ICD10:I25']`). Both SNOMED and ICD-10-CM populated for US-based conditions. Uniqueness enforced by seed-time check. |
| `snomed_codes` | list[string] | SNOMED CT codes. Retained for evaluator backward compatibility. |
| `icd10_codes` | list[string] | ICD-10-CM codes. Retained for evaluator backward compatibility. |
| `fhir_profile` | string | Optional. Reference to a specific FHIR Condition profile if the project uses one. |

#### `Observation` — FHIR Observation

Single-system primary key: LOINC (ADR 0017).

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable internal identifier. |
| `display_name` | string | Human-readable label (e.g., `"LDL cholesterol"`). |
| `code` | string | **Primary key.** Primary LOINC code for the concept (e.g., `"2089-1"`). Uniqueness constraint with `code_system`. |
| `code_system` | string | Always `"LOINC"` for Observation nodes. |
| `loinc_codes` | list[string] | LOINC codes that map to this concept. May include alternates beyond the primary key. |
| `snomed_codes` | list[string] | Optional SNOMED codes for findings. |
| `fhir_profile` | string | Optional FHIR Observation profile. |

#### `Medication` — FHIR Medication

Single-system primary key: RxNorm (ADR 0017).

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable internal identifier. |
| `display_name` | string | Human-readable label. |
| `code` | string | **Primary key.** RxCUI at class (ingredient) level (e.g., `"83367"`). Uniqueness constraint with `code_system`. |
| `code_system` | string | Always `"RxNorm"` for Medication nodes. |
| `rxnorm_codes` | list[string] | RxNorm codes. May include alternates beyond the primary key. |
| `fhir_profile` | string | Optional FHIR Medication profile. |

#### `Procedure` — FHIR Procedure

Single-system primary key: CPT (ADR 0017). Also used for counseling / shared-decision actions (coded with SNOMED counseling codes).

| Attribute | Type | Description |
|---|---|---|
| `id` | string | Stable internal identifier. |
| `display_name` | string | Human-readable label (e.g., `"Shared decision-making discussion about statin therapy"`). |
| `code` | string | **Primary key.** Most representative CPT code (e.g., `"99401"`). Uniqueness constraint with `code_system`. |
| `code_system` | string | Always `"CPT"` for Procedure nodes. |
| `cpt_codes` | list[string] | CPT codes that map to this procedure concept. |
| `snomed_codes` | list[string] | SNOMED codes. Required for counseling/shared-decision procedures where CPT may not apply cleanly. |
| `fhir_profile` | string | Optional FHIR Procedure profile. |

## Edges

### Global edge attributes

Every edge carries these, regardless of type:

| Attribute | Type | Description |
|---|---|---|
| `source_guideline_id` | string | Which Guideline this edge was written from. |
| `source_section` | string | Section within that guideline. |
| `effective_date` | date | When this edge became valid (usually the guideline's effective_date). |

### Edge types

| Edge | From → To | Description |
|---|---|---|
| `FROM_GUIDELINE` | Recommendation → Guideline | Provenance anchor. Exactly one per Rec. |
| `SUPERSEDES` | Guideline → Guideline | New version supersedes prior. Old Guideline and its Recs remain in place. |
| `FOR_CONDITION` | Recommendation → Condition | What clinical state the Rec is about. |
| `OFFERS_STRATEGY` | Recommendation → Strategy | A way to satisfy this Rec. Multiple edges = interchangeable alternatives. Rec is satisfied when *any* offered Strategy is satisfied. |
| `INCLUDES_ACTION` | Strategy → Procedure / Medication / Observation | Component action of a Strategy. Strategy is satisfied only when *all* of its INCLUDES_ACTIONs are satisfied (conjunction). |
| `TRIGGERED_BY` | Recommendation → Observation / Condition / Medication | Event trigger for non-default Recs (observation_result, condition_onset, medication_start). |
| `EXCLUDED_BY` | Recommendation → Condition / Procedure / Medication | Hard exclusions materialized from `structured_eligibility`. Regenerated from JSON on ingestion. |
| `TRIGGERS_FOLLOWUP` | Recommendation → Recommendation | Cascade chain (e.g., screening → FIT+ diagnostic → post-polypectomy surveillance). |
| `PREEMPTED_BY` | Recommendation → Recommendation | Conditional cross-guideline conflict resolution. Evaluated against patient state at query time. |
| `MODIFIES` | Recommendation → Recommendation / Strategy | Cross-guideline additive annotation. Target still fires; modifier annotates (e.g., intensity reduction). Per ADR 0019. |

### Edge-specific attributes

Only edge types with attributes beyond the global set are listed.

#### `INCLUDES_ACTION` (Strategy → clinical entity)

| Attribute | Type | Description |
|---|---|---|
| `cadence` | ISO 8601 duration | How often the action should recur (e.g., `P10Y`). Null for one-shot actions. |
| `lookback` | ISO 8601 duration | Window the API uses to check patient history for a matching prior action. Usually equal to `cadence`. |
| `priority` | enum | Urgency tier for the agent / trust framework: `routine` / `urgent` / `stat`. |
| `intent` | enum | `screening` / `diagnostic` / `treatment` / `surveillance` / `counseling` / `shared_decision`. |
| `expects` | string \| null | Optional result label (e.g., `"negative"`) the matched patient record must carry for this action to count as satisfied. Null = any result satisfies (default; preserves behavior for procedures without a meaningful result dimension). Labels resolve to coded value-sets via the external registry keyed by `(clinical_entity_id, label)`. Shares vocabulary with `TRIGGERED_BY.criteria.value`. See `schema.md` → Result-conditional satisfaction. v0: set on stool observations only. |
| `intensity` | enum \| null | Statin intensity tier: `"high"` / `"moderate"`. Used by ACC/AHA cholesterol strategies. Null on USPSTF v0 actions. v1 models at class level; dose verification deferred. |

#### `TRIGGERED_BY` (Recommendation → clinical entity)

| Attribute | Type | Description |
|---|---|---|
| `criteria` | JSON | Predicate describing the qualifying event shape. Uses the predicate DSL. Example: `{value: positive, window: P30D}` for a positive FIT result. |

#### `TRIGGERS_FOLLOWUP` (Recommendation → Recommendation)

| Attribute | Type | Description |
|---|---|---|
| `on` | string | Short label describing the triggering event (e.g., `"fit_positive"`, `"adenoma_found"`). Semantic pointer; the actual firing is handled by the downstream Rec's own `TRIGGERED_BY`. |

#### `PREEMPTED_BY` (Recommendation → Recommendation)

| Attribute | Type | Description |
|---|---|---|
| `priority` | integer | Higher priority wins when multiple preemption edges match. Default: USPSTF=100, ACC/AHA=200, KDIGO=200 per ADR 0018. |
| `rationale` | string | Human-readable audit string surfaced in the review tool and logs. |

#### `MODIFIES` (Recommendation → Recommendation / Strategy)

| Attribute | Type | Description |
|---|---|---|
| `nature` | enum | Controlled vocabulary: `intensity_reduction`, `dose_adjustment`, `monitoring`, `contraindication_warning`. New values require ADR + schema update. Per ADR 0019. |
| `note` | string | Human-readable explanation of the modification. |

## Quick visual: traversal shape

```
                 ┌──────────────┐
                 │  Guideline   │ ◄──── SUPERSEDES ──── (prior Guideline)
                 └──────▲───────┘
                        │ FROM_GUIDELINE
                        │
                 ┌──────┴──────────┐
 FOR_CONDITION   │                 │   TRIGGERS_FOLLOWUP
 ◄───────────────┤ Recommendation  ├──────────────────▶ (Recommendation)
 (Condition)     │                 │
                 │ - eligibility   │   PREEMPTED_BY
                 │ - nuance        │◄────────────────── (Recommendation)
                 │ - trigger       │
                 └──┬───────────┬──┘
                    │           │
    OFFERS_STRATEGY │           │ EXCLUDED_BY / TRIGGERED_BY
                    │           │
                    ▼           ▼
               ┌─────────┐   (Condition / Procedure /
               │Strategy │    Medication / Observation)
               └────┬────┘
                    │
                    │ INCLUDES_ACTION
                    ▼
           (Procedure / Medication / Observation)
```

Note the flow: **actions live one layer below Strategy**. A Recommendation never points directly at a Procedure/Medication/Observation as an action — it always goes through a Strategy, even when the Strategy has only one included action. The only direct Rec → clinical-entity edges are `FOR_CONDITION` (what the rec is about), `EXCLUDED_BY` (hard exclusions), and `TRIGGERED_BY` (event triggers). Those are not actions.
