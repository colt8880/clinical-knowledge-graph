# 30: UI multi-guideline recommendation list

**Status**: pending
**Depends on**: 21, 29
**Components touched**: ui
**Branch**: `feat/ui-multi-guideline-rec-list`

## Context

Eval tab's recommendation output pane currently renders a flat list of matched Recs from a single guideline. With three guidelines, the pane needs to show: which guideline each Rec came from, evidence grade, and — critically — where multiple guidelines converge on the same therapeutic action. This convergence visibility is the UI counterpart to F33's serialization.

### Simplification (2026-04-20)

Cross-guideline edges (PREEMPTED_BY, MODIFIES) were removed pending clinician review. The original F30 spec included preemption display ("superseded by" links), modifier annotations, and related verification targets. Those are deferred until clinician-reviewed edges return. This version focuses on multi-guideline grouping and convergence indicators.

## Required reading

- `docs/build/v1-spec.md` — UI additions.
- `docs/specs/ui.md` — Eval tab spec.
- `ui/CLAUDE.md`.
- `docs/build/29-ui-preemption-modifier-viz.md` — visual language consistency (colors, domain badges).
- `docs/specs/eval-trace.md` — events drive the list.
- `docs/build/33-arm-c-convergence-serialization.md` — the convergence model this UI reflects.

## Scope

- `ui/components/Eval/RecList.tsx` — refactor/replace existing list component to handle multi-guideline output.
- `ui/components/Eval/RecCard.tsx` — new; represents a single Rec with guideline badge, evidence grade, action summary, and convergence indicator.
- `ui/lib/recListBuilder.ts` — new; takes `EvalTrace` + matched Rec data and produces ordered Rec cards with convergence annotations. Identifies shared therapeutic actions by checking which Recs from different guidelines target the same clinical entity nodes.
- `ui/pages/eval.tsx` — wire new components.
- `ui/tests/RecList.test.tsx` — unit tests for ordering, convergence display.
- `ui/tests/RecCard.test.tsx` — unit test.
- `docs/specs/ui.md` — document the list's ordering rules and visual states.

## Constraints

- **Ordering:** primary sort by guideline priority (descending); secondary by evidence grade (higher wins); tertiary by rec id for determinism. Document the rule; users should be able to predict ordering.
- **Guideline badge:** uses F28 palette (USPSTF blue, ACC/AHA purple, KDIGO green).
- **Evidence grade pill:** ACC/AHA grades shown as `COR I / LOE A`; USPSTF as `B`; KDIGO as `1B` etc. Source-accurate formatting per guideline.
- **Convergence indicator:** When multiple guidelines emit Recs whose strategies target the same shared clinical entity (e.g., both USPSTF and ACC/AHA recommend statins via `med:atorvastatin`), show a convergence badge on each related Rec card: "Also recommended by: USPSTF, KDIGO" with domain-colored dots. Clicking the badge highlights the related cards.
- **Action summary:** each card shows the top-level action (e.g., "Start moderate-intensity statin") derived from the Rec's primary Strategy. Click expands to show full Strategy fan-out.
- **No API changes.** All data comes from the existing `/api/evaluate` response; convergence is computed client-side in `recListBuilder.ts` by matching shared entity IDs across guidelines' action chains.
- **Deterministic UI state.** Same trace + same filters produces the same ordering.
- **Consistency with F29 visual language.** Colors match; domain badges match.

### Deferred (pending clinician-reviewed cross-guideline edges)

- **Preempted Rec display:** strikethrough, dimmed card, "superseded by" link. Returns when PREEMPTED_BY edges are re-added.
- **Modifier annotations:** "Modified by KDIGO: intensity reduced due to CKD." Returns when MODIFIES edges are re-added.
- **"Show preempted" toggle.** No preempted recs to toggle.

## Verification targets

- `cd ui && npm run test:unit` — unit tests pass.
- Manual: load a multi-guideline fixture where USPSTF + ACC/AHA both fire statin recs; confirm both Rec cards appear with their domain badges and a convergence indicator linking them.
- Manual: load a single-guideline fixture; confirm no convergence indicators (only one guideline).
- Manual: verify ordering follows the documented rule (guideline priority → grade → id).
- Manual: click a convergence badge; confirm related cards are highlighted.
- Screenshots in PR body: single-guideline list, multi-guideline list with convergence indicators.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Screenshots in PR body.
- `docs/specs/ui.md` updated.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Preemption display (deferred — no edges).
- Modifier annotations (deferred — no edges).
- Export to PDF / printable report.
- Grouping by patient-context trigger.
- Inline editing. Read-only.
- Rec diff mode. v2.
- Collapsible sections by guideline.

## Design notes (not blocking, worth review)

- **Why convergence indicators instead of preemption links.** With edges removed, the highest-value cross-guideline signal in the UI is "these three guidelines agree on this action." That's convergence — derived from the shared entity layer, not from curated edges. When edges return, preemption display layers on top of convergence, not instead of it.
- **Convergence detection is client-side, not API-side.** The evaluate response already includes strategy/action data. `recListBuilder.ts` walks the trace to find shared entities. No new endpoint needed.
- **What if no convergence exists.** For patients matching only one guideline, or matching multiple guidelines with no overlapping actions, the convergence indicator simply doesn't appear. Absence of convergence is not an error.
