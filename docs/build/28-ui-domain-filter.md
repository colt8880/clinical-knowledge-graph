# 28: UI domain filter on Explore tab

**Status**: pending
**Depends on**: 20 (domain labels must exist), 23, 24
**Components touched**: ui / api
**Branch**: `feat/ui-domain-filter`

## Context

Once the graph contains three guidelines, the Explore tab's current "render everything" approach becomes unreadable. Add a multi-select domain filter so users can toggle guidelines on and off. Shared clinical entity nodes stay visible at all times; only guideline-scoped nodes (Guideline, Recommendation, Strategy) respect the filter.

## Required reading

- `docs/build/v1-spec.md` — UI additions for v1.
- `docs/specs/ui.md` — Explore tab spec.
- `ui/CLAUDE.md` — UI scope and conventions.
- `docs/build/20-shared-clinical-entity-layer.md` — domain label scheme.
- `docs/contracts/api.openapi.yaml` — API endpoints; may need one new parameter.

## Scope

- `ui/components/DomainFilter.tsx` — new; multi-select chip control for USPSTF / ACC/AHA / KDIGO.
- `ui/pages/explore.tsx` (or equivalent route) — integrate the filter; pipe state into graph query.
- `ui/lib/graphQuery.ts` (or equivalent) — accepts a `domains: string[]` parameter; translates to API call with filter.
- `api/app/routes/nodes.py` or the traversal primitive route — accept optional `?domains=USPSTF,ACC_AHA,KDIGO` query param. When present, filter guideline-scoped nodes by label; shared entity nodes unaffected.
- `docs/contracts/api.openapi.yaml` — document the new query param.
- `api/tests/test_nodes_filter.py` — new; asserts filter behavior and that shared entities always return.
- `ui/tests/DomainFilter.test.tsx` — unit test for the control.
- `docs/specs/ui.md` — document the filter behavior.

## Constraints

- **Default state:** all domains selected. Fresh session shows everything.
- **Persistence:** filter state persists in URL as `?domains=uspstf,acc_aha,kdigo` so the view is shareable. Persist also in localStorage as a usability nicety; URL wins on conflict.
- **Shared entity visibility:** when a domain is deselected, its Recs/Strategies disappear. Shared entity nodes (Medication, Condition, etc.) remain. Dangling entities (referenced only by now-hidden Recs) still render; they just appear disconnected. Acceptable tradeoff; the alternative (hide unreferenced entities) adds graph traversal cost and surprises the user.
- **Visual indicator:** each Rec/Strategy node displays a small domain badge matching the filter chip color.
- **No new layout:** reuse the existing Cytoscape layout; filter changes node visibility, not structure.
- **Accessibility:** filter is a proper multi-select with keyboard navigation. Do not ship a custom control without basic a11y.
- **Performance:** filtering client-side is acceptable for v1 graph sizes (< 1000 nodes). If server-side filtering becomes necessary later, the API param is already in place.

## Verification targets

- `cd ui && npm test` — unit tests pass.
- `cd api && uv run pytest api/tests/test_nodes_filter.py` — exits 0.
- Manual: open Explore tab with all three guidelines loaded; toggle each domain off in turn; confirm guideline-scoped nodes disappear and shared entities remain.
- URL reflects state: deselecting USPSTF updates URL to `?domains=acc_aha,kdigo`.
- Navigate to `/explore?domains=kdigo` directly — only KDIGO nodes render (plus shared entities).

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Manual testing walkthrough included in PR body with screenshots.
- `docs/specs/ui.md` updated.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Filter by intent (`screening` vs. `treatment`). Deferred.
- Filter by evidence grade. Deferred.
- Search by node id or label. Deferred (exists or can be added independently).
- Node-level hide/show controls. Filter is domain-level in v1.
- Preemption/modifier visualization (F29).
- Rec list rendering (F30).

## Design notes (not blocking, worth review)

- **Chip colors:** use Cytoscape's style system for node badges, matching chip colors. Recommended palette: USPSTF blue, ACC/AHA purple, KDIGO green. Document in `docs/specs/ui.md` so F29's preemption arrows don't clash.
- **What about cross-guideline edges when one side is filtered out?** Example: ACC/AHA selected, USPSTF deselected, and there's a `PREEMPTED_BY` edge from USPSTF to ACC/AHA. The edge has no source node to render. v1 behavior: hide the edge too. Documented in ui.md.
- **Client-side vs. server-side filtering.** Client-side is simpler and fine at current graph sizes. The API parameter is defined so server-side filtering can be added without client changes; don't implement both in v1.
- **Dangling entity UX.** A Medication node with no visible connections looks broken. Option: dim the node. Option: leave as-is and let the user re-enable domains. Recommend: leave as-is for v1; dimming logic adds state that F29 will also want (preemption dim), and bundling both in F29 is cleaner than splitting.
