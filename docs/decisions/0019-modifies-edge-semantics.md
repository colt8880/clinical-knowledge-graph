# 0019. MODIFIES edge semantics

Status: Accepted
Date: 2026-04-17
Supersedes: None
Paired with: F26 (MODIFIES edges from KDIGO)

## Context

The graph needs a way to express "guideline X modifies guideline Y's recommendation without replacing it." CKD doesn't cancel a statin recommendation — it adjusts the intensity. This is fundamentally different from preemption (`PREEMPTED_BY`), which removes a Rec from the active set. A modifier annotates a Rec that still fires.

Three candidate approaches:

1. **Reuse `PREEMPTED_BY` with a "partial" flag.** Overloads the semantics; consumers must distinguish "replaced" from "adjusted." Fragile.
2. **Embed modifications in the target Rec's `clinical_nuance`.** Works for prose but invisible to the evaluator and trace — no structured audit trail.
3. **New `MODIFIES` edge class with a controlled `nature` enum.** Clean separation from preemption. Evaluator emits structured events. Trace is auditable.

## Decision

**Option 3: new `MODIFIES` edge class.**

### Edge definition

```
(source:Recommendation)-[:MODIFIES {nature, note}]->(target:Recommendation|Strategy)
```

| Property | Type | Description |
|----------|------|-------------|
| `nature` | enum: `intensity_reduction`, `dose_adjustment`, `monitoring`, `contraindication_warning` | What kind of modification. Controlled vocabulary; new values require an ADR + schema update. |
| `note` | string | Human-readable explanation of the modification. |
| `provenance_source` | string | Seed file that authored this edge. |
| `provenance_date` | string | ISO 8601 date the edge was authored. |

### Cross-guideline only

`MODIFIES` edges must connect nodes from different guidelines (`source.guideline_id ≠ target.guideline_id`). Same-guideline modifications are handled within the guideline's own Rec/Strategy structure. Enforced at seed time; the evaluator does not check this (the seed is authoritative).

### Additive, not gating

The target Rec still fires. The modifier annotates — it does not suppress, replace, or gate the target. Consumers (UI, harness, LLM context) use the modifier to adjust their interpretation of the target Rec's output.

### Nature enum

| Value | Meaning | v1 usage |
|-------|---------|----------|
| `intensity_reduction` | Strategy-level change: high → moderate intensity. | KDIGO statin-for-CKD modifies ACC/AHA high-intensity strategies. |
| `dose_adjustment` | Medication-level change within a chosen intensity. | Reserved; not authored in v1. |
| `monitoring` | Additional monitoring required when the target Rec fires. | Reserved; not authored in v1. |
| `contraindication_warning` | The source condition creates a relative contraindication for the target action. | Reserved; not authored in v1. |

### Trace emission

Modifier resolution runs as a post-traversal step in `evaluate()`:
1. **After** preemption resolution (F25).
2. **Before** `evaluation_completed` and before `flat_recommendations` / `recommendations_by_guideline` are derived.

For each matched (non-preempted) target Rec with active `MODIFIES` edges where the source Rec was also emitted, the evaluator appends a `cross_guideline_match` event to `trace.events` (continuing the monotonic `seq`). Payload:

```json
{
  "type": "cross_guideline_match",
  "guideline_id": null,
  "source_rec_id": "rec:kdigo-statin-for-ckd",
  "target_rec_id": "rec:accaha-statin-secondary-prevention",
  "nature": "intensity_reduction",
  "note": "KDIGO recommends moderate-intensity statin in CKD G3-G5...",
  "source_guideline_id": "guideline:kdigo-ckd-2024",
  "target_guideline_id": "guideline:acc-aha-cholesterol-2018"
}
```

Events are append-only (F21 convention). Prior events are not mutated.

### Derivation enhancement

`flat_recommendations` and `recommendations_by_guideline` include a `modifiers` field per Rec — a list of `{source_rec_id, source_guideline_id, nature, note}` objects computed by scanning `cross_guideline_match` events where this Rec is the target. Empty list if no modifiers.

### Preemption takes precedence over modification

If a Rec is preempted, its modifiers are not emitted. A preempted Rec is already overridden; annotating it with modifiers would be noise. The `preemption_resolved` event in the trace documents why the Rec was suppressed; no modifier event is needed.

### Deterministic ordering

Modifier events are emitted in ascending order by `(source_guideline_id, source_rec_id, target_rec_id)`. This is a contract, not an implementation detail.

### Source-side pattern

v1 uses Rec-sourced modifiers only: the `MODIFIES` edge originates from a KDIGO Recommendation node. Observation-sourced modifiers (e.g., eGFR Observation → Strategy) are a v2 consideration if purely observation-driven modifiers are needed without a guideline Rec wrapping them.

## Consequences

- **Modifier authors carry the annotation decision.** Like preemption, this is a clinical judgment call documented in the edge's `note`.
- **Nature enum is extensible but gated.** New values require an ADR + schema update. This prevents free-form string drift.
- **Modifier events are structured and auditable.** The trace captures every modifier that fired, with full provenance. The Eval UI can render them (F29).
- **Cross-edge seed files.** `MODIFIES` edges live in dedicated seed files alongside `PREEMPTED_BY` edges (e.g., `graph/seeds/cross-edges-kdigo.cypher`).
- **No cascading.** A `MODIFIES` edge does not trigger another `MODIFIES` edge. v1 is non-cascading.

## Alternatives considered

- **Option 1 (partial preemption).** Rejected because it overloads `PREEMPTED_BY` semantics. Consumers would need `if edge.partial then annotate else replace`, which is error-prone and makes the trace harder to audit.
- **Option 2 (clinical_nuance embedding).** Rejected because it's invisible to the evaluator. No structured trace event, no deterministic audit, no programmatic access for the harness or UI.
- **Inline modifier on INCLUDES_ACTION edges.** Rejected because it couples the modifier to a specific Strategy's action graph rather than expressing a cross-guideline relationship. The modifier is about the relationship between two guidelines' Recs, not about a single action edge.
