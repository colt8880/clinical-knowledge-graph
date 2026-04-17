# 29: UI preemption and modifier visualization on Eval tab

**Status**: pending
**Depends on**: 25, 26, 28
**Components touched**: ui / api
**Branch**: `feat/ui-preemption-modifier-viz`

## Context

Once preemption (F25) and modifier (F26) edges exist and the evaluator emits their events, the Eval tab needs to render the semantics. A preempted Rec is rendered dimmed with a visible `PREEMPTED_BY` arrow to its winner. Modifier edges render as annotations attached to the target Rec. The trace stepper shows `preemption_resolved` and `cross_guideline_match` events inline so users can step through the reasoning.

## Required reading

- `docs/build/v1-spec.md` — UI additions for v1.
- `docs/specs/ui.md` — Eval tab spec.
- `ui/CLAUDE.md` — UI conventions.
- `docs/build/25-preemption-uspstf-accaha.md` — preemption semantics.
- `docs/build/26-modifies-edges-kdigo.md` — modifier semantics.
- `docs/specs/eval-trace.md` — event types to render.

## Scope

- `ui/components/Eval/GraphCanvas.tsx` (or equivalent) — add rendering modes for preempted nodes and modifier annotations.
- `ui/components/Eval/TraceStepper.tsx` — render `preemption_resolved` and `cross_guideline_match` events with distinct visual treatment.
- `ui/components/Eval/PreemptionArrow.tsx` — new; renders a thick arrow from preempted Rec to winner with edge priority label.
- `ui/components/Eval/ModifierBadge.tsx` — new; small icon/badge attached to a Rec indicating "modified by [source guideline]" with tooltip showing `nature` and `note`.
- `ui/pages/eval.tsx` — wire new components.
- `ui/lib/traceRenderer.ts` — extend to handle the new event types in stepper.
- `ui/tests/PreemptionArrow.test.tsx` — unit test.
- `ui/tests/ModifierBadge.test.tsx` — unit test.
- `ui/tests/TraceStepper.test.tsx` — amend; assert new events render.
- `docs/specs/ui.md` — document the visual language for preemption and modifiers.

## Constraints

- **Preempted Rec visual:** node opacity 0.4 (tunable via `ui.md`); outline stroke-dashed; label suffix `(preempted)`.
- **Preemption arrow:** thicker than normal edges; distinct color (recommend desaturated red or neutral gray); arrowhead points from preempted to winner; hover reveals priority values and `reason` from the event.
- **Modifier badge:** small icon next to Rec label; hover reveals the modifier's `nature`, `note`, and source guideline. If a Rec has multiple modifiers, badge shows a count.
- **Trace stepper event styling:** `preemption_resolved` events render with a strikethrough-style icon; clicking navigates the canvas to highlight both preempted and winner nodes. `cross_guideline_match` events render with a link icon; clicking highlights target Rec and pulses the modifier badge.
- **Stepper playback:** existing behavior preserved. New event types are regular stoppable steps.
- **No change to trace event semantics.** UI consumes what F21/F25/F26 emit; UI does not reinterpret.
- **Domain filter interaction:** if the domain filter (F28) hides the source of a preemption or modifier edge, the UI hides the edge too and marks the target node with a small indicator "hidden by filter" so users understand why a Rec shows no preemption when one exists in the graph.
- **Performance:** re-render on event step must remain snappy at current graph sizes. No layout recalculation on step; visual state only.

## Verification targets

- `cd ui && npm test` — unit tests pass.
- Manual: load a cross-domain fixture in Eval; step through trace; confirm preemption arrow appears at the correct step and the preempted Rec dims.
- Manual: load a KDIGO-modifier fixture; confirm modifier badge appears on the target Rec; hover reveals correct text.
- Manual: toggle domain filter to hide the source of an active preemption; confirm target Rec shows the "hidden by filter" indicator.
- Screenshots captured for PR body covering: (1) preemption in trace, (2) modifier in trace, (3) filter interaction with cross-edge.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Screenshots included in PR body.
- `docs/specs/ui.md` updated with visual language reference.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Animation of the trace stepper beyond existing behavior.
- Customizable visual theming. Colors picked in this feature are baseline; no settings UI.
- Editing preemption/modifier edges from the UI. Read-only rendering.
- Visualization of `modifier_suppressed` sub-field from F26. The trace stepper shows it as plain text in the event details; no custom treatment in v1.
- Rec list rendering (F30) — separate feature.

## Design notes (not blocking, worth review)

- **Why dim rather than hide preempted Recs.** Hiding would mislead the user into thinking a Rec didn't apply. Dimming communicates "this was evaluated and consciously suppressed," which matches the trace-first philosophy (nothing is silently discarded).
- **Arrow thickness vs. edge volume.** At 18 fixtures and typical graph density, preemption arrows will be sparse (2-6 per fixture). Thick weighting is fine. If v2 adds many more, revisit.
- **Mobile/narrow viewport:** not a v1 concern per `ui.md`. Desktop only.
- **Counter-argument to dual treatments (arrow for preemption, badge for modifier):** could unify as two edge visualizations. Separate treatments signal that preemption (removes) and modification (annotates) are semantically distinct. Keeping them visually distinct reinforces the mental model. Worth the minor code duplication.
- **What if a Rec is both preempted by one edge and modified by another?** Preemption wins per F26 constraints; modifier event is suppressed; UI renders preemption only. Tooltip on the dimmed Rec mentions "modifier suppressed: see trace" with a link to the event.
