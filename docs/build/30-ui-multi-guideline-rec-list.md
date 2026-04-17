# 30: UI multi-guideline recommendation list

**Status**: pending
**Depends on**: 21, 25, 26, 29
**Components touched**: ui
**Branch**: `feat/ui-multi-guideline-rec-list`

## Context

Eval tab's recommendation output pane currently renders a flat list of matched Recs from a single guideline. With three guidelines and cross-guideline interactions, the pane needs to show: which guideline each Rec came from, preemption status, modifier annotations, and a sensible ordering. This is pure presentation; the underlying data is already emitted by the evaluator after F21/F25/F26.

## Required reading

- `docs/build/v1-spec.md` — UI additions.
- `docs/specs/ui.md` — Eval tab spec.
- `ui/CLAUDE.md`.
- `docs/build/29-ui-preemption-modifier-viz.md` — visual language consistency.
- `docs/specs/eval-trace.md` — events drive the list.

## Scope

- `ui/components/Eval/RecList.tsx` — refactor/replace existing list component to handle multi-guideline output.
- `ui/components/Eval/RecCard.tsx` — new; represents a single Rec with guideline badge, preemption state, modifier count, evidence grade, action summary.
- `ui/components/Eval/GuidelineBadge.tsx` — shared guideline-label chip reused across Explore and Eval; extracts current ad-hoc rendering.
- `ui/lib/recListBuilder.ts` — new; takes `EvalTrace` + matched Rec data and produces ordered Rec cards with annotations.
- `ui/pages/eval.tsx` — wire new components.
- `ui/tests/RecList.test.tsx` — unit tests for ordering, preemption display, modifier count.
- `ui/tests/RecCard.test.tsx` — unit test.
- `docs/specs/ui.md` — document the list's ordering rules and visual states.

## Constraints

- **Ordering:** primary sort by guideline priority (descending); secondary by evidence grade (higher wins); tertiary by rec id for determinism. Preempted Recs sort to the bottom of their guideline group with an explicit separator. Document the rule; users should be able to predict ordering.
- **Preempted Rec display:** rendered with strikethrough on the Rec title, dimmed card background, and a "superseded by [winning Rec name]" caption linking to the winning card. Clicking the link scrolls to the winning card and highlights it briefly.
- **Modifier display:** inline annotation under the Rec title: "Modified by KDIGO: intensity reduced due to CKD G3b". Multiple modifiers stack vertically. Tooltips on each for full `note`.
- **Guideline badge:** uses the shared component from scope; color matches F28 palette (USPSTF blue, ACC/AHA purple, KDIGO green).
- **Evidence grade pill:** ACC/AHA grades shown as `COR I / LOE A`; USPSTF as `B`; KDIGO as `1B` etc. Source-accurate formatting per guideline.
- **Action summary:** each card shows the top-level action (e.g., "Start moderate-intensity statin") derived from the Rec's primary Strategy. Click expands to show full Strategy fan-out.
- **Preempted Recs are still in the list.** Filtering them out would hide evaluator reasoning. Filter toggle "show preempted" is available; default ON.
- **No API changes.** All data comes from the existing `/api/evaluate` response; if the UI needs derived fields, compute them in `recListBuilder.ts`.
- **Deterministic UI state.** Same trace + same filters produces the same ordering. No randomness or async reordering.
- **Consistency with F29 visual language.** Preemption dimming matches; modifier icons match; colors match.

## Verification targets

- `cd ui && npm test` — unit tests pass.
- Manual: load cross-domain case-01 (clinical ASCVD); confirm ACC/AHA secondary-prevention Rec at top, USPSTF Recs shown as preempted with link to the winner.
- Manual: load cross-domain case-03 (CKD + secondary prevention); confirm ACC/AHA high-intensity Rec with a KDIGO modifier annotation displayed.
- Manual: toggle "show preempted" off; confirm preempted cards hide; toggle on; they return.
- Screenshots captured for PR body covering: single-guideline, preemption, modifier, all-three-guidelines-matched cases.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Screenshots in PR body.
- `docs/specs/ui.md` updated.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Export to PDF / printable report. Deferred.
- Grouping by patient-context trigger (e.g., "because of your LDL..."). Deferred.
- Inline editing. Read-only.
- Rec diff mode (compare runs against different graph versions). v2 historical replay territory.
- Collapsing/expanding sections by guideline. Keep flat list ordered by priority; a section/accordion is a v2 UX choice if the list gets long.

## Design notes (not blocking, worth review)

- **Why guideline-priority ordering rather than clinical priority.** Clinical priority (what should be done first) is subjective and would require a separate priority model. Guideline priority is a property already in the graph (from F25 ADR). Ordering by it gives clinicians a consistent structure; they can re-prioritize mentally.
- **"Superseded by" link UX.** In dense fixtures, preempted Recs can outnumber winners. The link prevents users from having to scan back up the list to find the winner. Keep it inline rather than as a separate "preemption map" modal; the inline form reads closer to a chart note.
- **Action summary derivation.** For most Recs there's one primary Strategy. Where multiple Strategies exist (e.g., Grade C with SDM + moderate statin), show the top strategy by position in the seed; expand button reveals both. Document the tiebreaker.
- **Preempted Recs in the action summary count.** Success criterion in the rubric is completeness — does the LLM include expected actions? Preempted Recs are not expected actions; they should NOT appear in the LLM output. The UI displays them to show evaluator reasoning, not as recommendations to the clinician.
- **Shared GuidelineBadge component.** Extract this now (rather than in F28's chip) because F30 needs the same visual language and splitting the definitions means drift. Small refactor; pays for itself immediately.
