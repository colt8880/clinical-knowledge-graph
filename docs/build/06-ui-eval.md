# 06: UI Eval tab

**Status**: pending
**Depends on**: 04, 05
**Branch**: `feat/ui-eval`

## Context

Second tab of the UI: pick a fixture, run it through `/evaluate`, step through the resulting trace event-by-event, highlight the current node on the GraphCanvas. This is the money demo — it turns the deterministic trace into something a clinician reviewer can actually follow.

## Required reading

- `ui/CLAUDE.md`
- `docs/specs/ui.md` — Eval tab spec.
- `docs/specs/eval-trace.md` — event shapes; the stepper renders these directly.
- `docs/contracts/eval-trace.schema.json`
- `evals/statins/README.md` — fixture list shown in the fixture picker.

## Scope

- `ui/app/eval/page.tsx` — Eval tab.
- `ui/components/FixturePicker.tsx` — dropdown of available fixtures.
- `ui/components/TraceStepper.tsx` — prev/next controls, current event index, keyboard shortcuts (←/→).
- `ui/components/TraceEventList.tsx` — scrollable event list with active highlight.
- `ui/components/RecommendationStrip.tsx` — derived recommendations shown beneath the graph.
- `ui/lib/eval/` — client-side trace navigation state (pure, unit-testable).
- `ui/tests/eval.spec.ts` — Playwright test: pick fixture 01, step through, assert terminal event is Grade B recommendation and the current-node highlight moves as expected.
- Reuse `GraphCanvas` from feature 05; extend it to accept a `highlightedNodeId` prop.

## Constraints

- The stepper is a pure function of `(trace, currentIndex)`. No hidden state.
- Event list and graph highlight stay in sync — one source of truth for `currentIndex`.
- When a predicate evaluates against a specific node (e.g., a Condition), the graph highlight moves to that node.
- Recommendations strip is derived from the trace (filter for `recommendation_emitted` events); never fetched separately.
- Exits appear in the trace but not in the recommendations strip (per `docs/ISSUES.md`).

## Verification targets

- `cd ui && npm run build` — exits 0.
- `cd ui && npm run test` — all tests pass.
- Manual: Eval tab, select `01-high-risk-55m`, press `→` repeatedly; each event highlights the relevant node on the graph; terminal event is `recommendation_emitted(rec:statin-initiate-grade-b, due)`; the recommendations strip shows exactly one Grade B rec.
- Repeat for fixtures 02–05; terminal events match `docs/reference/statin-model.md#patient-path-summary`.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md`: `Eval tab` → `tested`.
- PR opened with Scope / Manual Test Steps / Manual Test Output (screenshots or short GIF).
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Editing fixtures in the UI.
- Diffing two traces side by side.
- Exporting trace to file (user can copy from network panel for now).
- Auth / multi-user.
