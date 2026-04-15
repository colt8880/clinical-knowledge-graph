# Review Workflow

**Status: stub — expand as the review tool gets built.**

## v0 behavior

Clinicians traverse the graph in the review tool and can **flag** nodes or edges with:
- A free-text comment
- A category (initial set below, expand with usage)

Flags are stored against the specific node/edge version (not the logical ID) so a flag against an obsolete node remains historically accurate after the graph updates.

## Flag categories (initial)

- `incorrect_criterion` — eligibility / trigger predicate is wrong
- `missing_recommendation` — a guideline statement not represented
- `stale_guideline` — source document has been superseded
- `wrong_action` — recommended action doesn't match the source
- `wrong_cadence` — interval/lookback is off
- `provenance_issue` — source citation is missing or incorrect
- `other` — catchall, must include comment

## Graph editing

**Out of scope for v0.** Flags go to a curator queue. Edits are made manually by the curation team via direct graph operations. Revisit building an in-app editor once flag volume justifies it.

## To be written

- Flag queue UI behavior (filtering, assignment, triage states)
- Curator resolution workflow (acknowledged / accepted / rejected / duplicate)
- How resolved flags link to the graph commit that addressed them
- Metrics: flag volume by category, time-to-resolution, recurrence
