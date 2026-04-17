# 0018. Preemption precedence rules

Status: Accepted
Date: 2026-04-17
Supersedes: None
Paired with: F25 (preemption, USPSTF ↔ ACC/AHA)

## Context

The graph schema has carried a `PREEMPTED_BY` edge type since v0, but no guideline exercised it (v0 was single-guideline). With ACC/AHA 2018 Cholesterol now in the graph alongside USPSTF 2022 Statins, overlapping recommendations exist: both guidelines address primary prevention statin therapy for adults 40-75 with cardiovascular risk factors. The evaluator needs a deterministic rule for resolving which recommendation takes precedence when both match a patient.

Three candidate approaches:

1. **Specificity-based.** The more specific recommendation wins. Hard to formalize — "specific to what?" differs by domain.
2. **Publication recency.** Newer guideline wins. Simple but clinically incorrect when an older specialty society guideline is more authoritative for its domain than a newer general screening recommendation.
3. **Explicit priority integer per edge.** Authors assign a numeric priority when creating `PREEMPTED_BY` edges. Higher wins. Tie-break on guideline `published_at`. No automatic inference.

## Decision

**Option 3: explicit `priority` integer on every `PREEMPTED_BY` edge, with `published_at` tie-break.**

### Priority property

Every `PREEMPTED_BY` edge carries:

| Property | Type | Description |
|----------|------|-------------|
| `priority` | integer | Higher value wins. Assigned at seed time by the edge author. |
| `rationale` | string | Human-readable explanation of why this preemption exists. |

### Default priority assignments

| Guideline | Default priority | Rationale |
|-----------|-----------------|-----------|
| USPSTF 2022 Statins | 100 | Federal task force; broad population-level screening recommendations. |
| ACC/AHA 2018 Cholesterol | 200 | Specialty society (cardiology); more granular statin benefit groups, intensity tiers, and LDL targets within the cardiovascular domain. |
| KDIGO 2024 CKD | 200 | Specialty society (nephrology); domain authority on CKD-related medication adjustments. |

The principle: within a clinical domain, a specialty society guideline that provides more granular, domain-specific guidance takes precedence over a federal task force guideline that provides broader population-level screening recommendations. This mirrors clinical practice — a cardiologist's statin recommendation supersedes the USPSTF screening recommendation for the same patient.

Priority integers are per-edge, not per-guideline. An edge author may deviate from the default if a specific Rec pair warrants it (e.g., a USPSTF recommendation with stronger evidence on a narrow population). Document the deviation in the edge's `rationale`.

### Tie-break rule

When two `PREEMPTED_BY` edges resolve to the same priority:

1. The Rec from the guideline with the more recent `published_at` (i.e., `Guideline.effective_date`) wins.
2. If `published_at` is also identical (same date): deterministic but arbitrary — lexicographic order of `recommendation_id`. This should never happen in practice; if it does, the edge author should assign distinct priorities.

### No transitive preemption

If Rec A is preempted by Rec B, and Rec B is preempted by Rec C, Rec A is **not** automatically preempted by Rec C. Authors must explicitly create an A → C edge if that preemption is intended. The evaluator detects transitive chains (A preempted by B, B preempted by C, no direct A → C edge) and logs a warning. This prevents silent precedence cascades that are hard to audit.

### Activation rule

A `PREEMPTED_BY` edge only activates when **both** the preempted Rec and the winning Rec match the patient (i.e., both have `recommendation_emitted` events in the trace). An unmatched winner does not preempt. This prevents a guideline from suppressing another guideline's Rec for patients the winning guideline doesn't address.

### Preempted Recs stay in the trace

Preempted Recs are not removed from the trace. The evaluator appends `preemption_resolved` events after the guideline loop completes. The derived recommendation list includes a `preempted_by` field (null if not preempted, winning `recommendation_id` if preempted). Consumers (UI, harness) can filter or dim preempted Recs. This keeps the trace auditable — a reviewer can see what the evaluator considered and why it was overridden.

## Consequences

- **Edge authors carry the precedence decision.** No automatic inference. This is intentional: preemption is a clinical judgment call, not a mechanical rule. The `rationale` property forces authors to document the reasoning.
- **Priority integers are interpolatable.** If a future guideline needs to sit between USPSTF (100) and ACC/AHA (200), it can use 150. Labels ("high", "medium", "low") would not support this.
- **Single-edge-per-Rec-pair rule.** At most one `PREEMPTED_BY` edge between any two Recommendation nodes. Enforced by a seed-time uniqueness check (Neo4j cannot natively constrain relationship uniqueness).
- **Cross-edge seed files.** `PREEMPTED_BY` edges live in dedicated seed files (`graph/seeds/cross-edges-*.cypher`), not in guideline-specific seeds. This keeps guideline authoring independent and makes cross-edges reviewable as a unit.

## Alternatives considered

- **Specificity-based (option 1).** Rejected because "specificity" is subjective and domain-dependent. Formalizing it would require a specificity taxonomy that doesn't exist in the clinical guideline literature.
- **Publication recency (option 2).** Rejected because it produces clinically incorrect results: USPSTF 2022 is newer than ACC/AHA 2018, but ACC/AHA provides more authoritative cardiovascular-specific guidance. Recency is a useful tie-break but not a primary rule.
- **No preemption; let consumers resolve.** Rejected because the thesis requires the graph to encode cross-guideline reasoning. Pushing resolution to consumers (LLM, UI) undermines the deterministic reasoning substrate.
