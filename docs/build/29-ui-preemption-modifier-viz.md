# 29: UI preemption and modifier visualization on Eval tab

**Status**: shipped
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

This feature extends the shared `GraphCanvas` (refactored in F28 into a whole-forest Cytoscape canvas) with preemption and modifier styling. It does NOT create a parallel Eval canvas. Preemption arrows and modifier badges are Cytoscape style rules keyed off node/edge data properties, not standalone React components.

- `ui/components/GraphCanvas.tsx` — **extend** the shared canvas. Add Cytoscape style rules:
  - Preempted node styling: dimmed opacity (0.4), dashed outline, label suffix `(preempted)`. Triggered when node data has a non-null `preempted_by` field (the derivation field F25 adds to `flat_recommendations`).
  - `PREEMPTED_BY` edge styling: thicker stroke, distinct color (desaturated red or neutral gray), arrowhead from preempted → winner. Triggered by edge type.
  - `MODIFIES` edge styling: subtle dotted line with a small modifier-icon marker near the target node. Triggered by edge type.
  - Modifier badge on target Recs: small counter badge rendered via Cytoscape node metadata (or overlay icon) when `modifiers.length > 0` on node data.
  - Visibility respects F28's `visibleDomains`: a `PREEMPTED_BY` edge is hidden if its source domain is filtered out; target Rec shows a small "hidden by filter" indicator so users understand why a Rec shows no preemption when one exists in the graph.
- `ui/components/GraphTooltips.tsx` — new; hover tooltip content for preemption (shows `edge_priority`, `reason`) and modifiers (shows `nature`, `note`, source guideline). Renders via `cytoscape-popper` + React or similar. Small; just the hover content.
- `ui/components/TraceStepper.tsx` — **extend** existing component. Render `preemption_resolved` events with a strikethrough-style icon; clicking navigates the canvas to highlight both preempted and winner nodes. Render `cross_guideline_match` events with a link icon; clicking highlights target Rec and pulses its modifier badge.
- `ui/app/eval/page.tsx` — wire the tooltip integration and stepper-driven canvas highlights. The canvas itself is reused from the shared component; Eval passes trace-derived state (e.g., `highlightedNodeIds`) as it already does.
- `ui/lib/eval/traceNavigator.ts` (or equivalent existing helper) — extend to resolve `preemption_resolved` and `cross_guideline_match` events into canvas highlight targets.
- `ui/tests/components/GraphCanvas.test.tsx` — amend. Assert: preempted-state styling applies when `preempted_by` is set; modifier-edge rendering; hover tooltip integration fires.
- `ui/tests/components/TraceStepper.test.tsx` — amend; assert new event types render with correct icon and click-to-highlight behavior.
- `docs/specs/ui.md` — document the visual language for preemption and modifiers; update the Eval tab section.

## Constraints

- **Shared canvas, not parallel.** All visual changes land in the single `ui/components/GraphCanvas.tsx` refactored by F28. No Eval-specific canvas is introduced.
- **Styles key off node/edge data, not eval-mode flags.** F25 and F26 populate `preempted_by` on recs and `modifiers` list on recs, and add `PREEMPTED_BY` / `MODIFIES` edges. The canvas's Cytoscape stylesheet uses selectors like `node[preempted_by]` and `edge[type = "PREEMPTED_BY"]` so the styling activates automatically whenever the data is present. Explore tab will show the same styling once F23+F25 graphs are loaded; that's a feature, not a bug.
- **Preempted Rec visual:** node opacity 0.4 (tunable via `ui.md`); outline stroke-dashed; label suffix `(preempted)`.
- **Preemption edge:** thicker stroke than normal edges; distinct color (desaturated red or neutral gray, documented); arrowhead from preempted → winner; hover tooltip reveals `edge_priority`, `reason`.
- **Modifier badge:** small counter icon on target Rec when `modifiers.length > 0`; hover tooltip reveals per-modifier `nature`, `note`, and source guideline. Multiple modifiers stack in the tooltip, not on the badge.
- **Trace stepper event styling:** `preemption_resolved` events render with a strikethrough-style icon; clicking navigates the canvas to highlight both preempted and winner nodes via `highlightedNodeIds`. `cross_guideline_match` events render with a link icon; clicking highlights target Rec.
- **Stepper playback:** existing behavior preserved. New event types are regular stoppable steps.
- **No change to trace event semantics.** UI consumes what F21/F25/F26 emit; UI does not reinterpret.
- **Domain filter interaction (inherited from F28):** if F28's filter hides the source of a preemption or modifier edge, the canvas hides the edge too. Target Rec shows a small "hidden by filter" indicator so users understand why a Rec shows no preemption when one exists in the graph.
- **Performance:** re-render on event step must remain snappy at current graph sizes. No layout recalculation on step; Cytoscape class toggles only.

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
- **Counter-argument to dual treatments (arrow for preemption, badge for modifier):** could unify as two edge visualizations. Separate treatments signal that preemption (removes) and modification (annotates) are semantically distinct. Keeping them visually distinct reinforces the mental model. Worth the minor style complexity.
- **Why styles key off data, not a mode flag.** A `eval-mode="true"` prop on GraphCanvas would work, but then the styling only activates in one tab. Keying off node/edge data means the Explore tab ALSO shows preemption arrows once the graph has them (post-F25). Good for demo ("look, the graph itself knows these interact"); the Eval tab layers trace-stepper highlighting on top. One code path, two presentations.
- **What if a Rec is both preempted by one edge and modified by another?** Preemption wins per F26 constraints; modifier event is suppressed; UI renders preemption only. Tooltip on the dimmed Rec mentions "modifier suppressed: see trace" with a link to the event.
