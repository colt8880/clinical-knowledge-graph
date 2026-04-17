# 28: Explore tab refactor — whole-forest Cytoscape canvas with domain filter

**Status**: pending
**Depends on**: 20 (domain labels must exist), 23, 24
**Components touched**: ui / api / docs
**Branch**: `feat/ui-whole-forest-explore`

## Context

v0's Explore tab is a hierarchical column navigator: URL picks one guideline, user drills Guideline → Rec → Strategy → Action with per-hop `fetchNeighbors` calls. That model doesn't scale to three guidelines and makes it impossible to see cross-guideline structure (which is the entire point of v1). This feature rebuilds Explore as a whole-forest graph canvas: all selected guideline subgraphs rendered simultaneously in a Cytoscape canvas, with a domain filter to toggle which guidelines are visible. Shared clinical entities always render.

This is also the groundwork F29 builds on: preemption arrows and modifier badges need a whole-graph canvas to render against, and having that canvas live in v1 Phase 4 means F29 is purely additive.

This feature is larger than it looks. Read the Required reading and Constraints sections carefully; the refactor touches the UI data model, adds a new API endpoint, migrates URL state, and replaces the column layout with a real graph canvas. There is no "small version" of this feature — either Option A (separate, smaller guideline-selector feature) or this Option B rebuild. Option B is chosen.

## Required reading

- `docs/build/v1-spec.md` — UI additions for v1.
- `docs/specs/ui.md` — Explore tab spec; will be rewritten as part of this feature.
- `ui/CLAUDE.md` — UI scope and conventions.
- `ui/app/explore/page.tsx` — current implementation; understand the column navigation + URL state model before replacing it.
- `ui/lib/api/client.ts` — current `fetchNeighbors` signature.
- `docs/decisions/0004-*.md` — chose Cytoscape.js for UI graph rendering; this feature finally uses it for Explore.
- `docs/build/20-shared-clinical-entity-layer.md` — domain label scheme (`:USPSTF`, `:ACC_AHA`, `:KDIGO`) and shared entity handling.
- `docs/contracts/api.openapi.yaml` — current API; will be extended with a new endpoint.

## Scope

### UI

- `ui/app/explore/page.tsx` — rewrite. Replace column layout with Cytoscape canvas and sidebar controls. Keep the node detail panel (reused from v0) triggered by canvas clicks.
- `ui/components/Explore/GraphCanvas.tsx` — new; Cytoscape wrapper. Props: `nodes`, `edges`, `visibleDomains`, `focusedNodeId`, `onNodeClick`. Handles layout, rendering, visibility toggling.
- `ui/components/Explore/DomainFilter.tsx` — new; multi-select chip control for USPSTF / ACC-AHA / KDIGO. Emits `visibleDomains: string[]`.
- `ui/components/Explore/NodeDetailPanel.tsx` — refactor existing v0 detail panel into a standalone component if not already. Triggered by canvas click, not column click.
- `ui/lib/api/client.ts` — add `fetchSubgraph({ domains: string[] })` calling the new API endpoint. Keep existing `fetchNeighbors` (still used by Eval tab).
- `ui/lib/explore/urlState.ts` — new; centralizes URL state logic for Explore. New params: `?domains=uspstf,acc-aha,kdigo&focus=<node_id>`. Deprecates v0's `?g=&r=&s=` column-navigation params.
- `ui/lib/explore/layout.ts` — new; Cytoscape layout configuration. Per-guideline `dagre` clustering, with shared entities positioned centrally between clusters. Document the choice.
- `ui/styles/explore.css` (or Tailwind config additions) — domain color palette: USPSTF blue, ACC/AHA purple, KDIGO green, shared entities neutral gray. Defined as CSS variables so F29 can reuse.
- `ui/tests/components/DomainFilter.test.tsx` — unit test.
- `ui/tests/components/GraphCanvas.test.tsx` — unit test (nodes/edges render, click handlers fire, visibility respects `visibleDomains`).
- `ui/tests/e2e/explore.spec.ts` — Playwright: load /explore, verify all three guidelines render, toggle a domain off, verify hidden, click a node, verify detail panel opens, verify URL reflects state.

### API

- `api/app/routes/subgraph.py` — new route. `GET /subgraph?domains=USPSTF,ACC_AHA,KDIGO` returns `{nodes: [...], edges: [...]}` covering all guideline-scoped nodes with the requested domain labels PLUS all shared entity nodes referenced by any of them. Default (no `domains` param) returns all guidelines. Empty `domains=` returns only shared entities.
- `api/app/db.py` or a new `api/app/queries/subgraph_query.py` — Cypher for the bulk subgraph fetch. One round-trip preferred; two round-trips (nodes, then edges) acceptable if performance is better.
- `api/app/main.py` — wire the new route.
- `docs/contracts/api.openapi.yaml` — document `GET /subgraph` with request/response schemas.
- `api/tests/routes/test_subgraph.py` — new; integration tests. Assert: (a) no `domains` returns full forest, (b) single domain returns that guideline + shared entities only, (c) two domains returns union, (d) shared entities never duplicated, (e) response shape matches OpenAPI.
- `api/tests/queries/test_subgraph_query.py` — unit tests for the query logic.

### Docs

- `docs/specs/ui.md` — rewrite Explore section. Old hierarchical navigation model is deprecated; Cytoscape whole-forest canvas is the new model. Document the color palette, layout choice, URL state, and domain-filter behavior.
- `docs/reference/build-status.md` — backlog row.

## Constraints

### Refactor scope

- **Hierarchical column navigation is removed.** v0's `?g=&r=&s=` URL state is deprecated. A legacy redirect is nice but not required (v0 has no external consumers). If a user hits an old URL, the page loads with all guidelines shown and `focus` unset.
- **Cytoscape is the renderer.** No HTML/Tailwind fallback layout. ADR 0004 committed to Cytoscape; this is where it lands.
- **No changes to the Eval tab in this feature.** Eval still uses its own rendering. F29 will align Eval with the same visual language.

### Data and API

- **Bulk fetch, not per-hop.** The new endpoint returns the entire requested subgraph in one call. The client does not paginate or stream for v1 graph sizes.
- **Shared entities never duplicated.** Returned exactly once regardless of how many guideline-scoped nodes reference them.
- **Edges included.** Response includes all edges where both endpoints are in the returned node set. Cross-guideline edges (`PREEMPTED_BY`, `MODIFIES`) that exist but whose other endpoint is filtered out: NOT returned. When F25/F26 ship those edges, filter behavior honors this (if USPSTF is off and ACC/AHA is on, a `PREEMPTED_BY` edge from a USPSTF Rec to an ACC/AHA Rec is not returned).
- **Response shape:**
  ```
  {
    "nodes": [
      {
        "id": "<neo4j node id or canonical id>",
        "labels": ["Recommendation", "USPSTF"],
        "properties": { ... },
        "domain": "USPSTF" | "ACC_AHA" | "KDIGO" | null  // null for shared entities
      }
    ],
    "edges": [
      {
        "id": "<neo4j rel id or synthetic>",
        "source": "<node_id>",
        "target": "<node_id>",
        "type": "OFFERS" | "INCLUDES_ACTION" | "TARGETS" | ...,
        "properties": { ... }
      }
    ]
  }
  ```
  Frozen in `api.openapi.yaml`; changes to shape require a contract update.
- **Determinism.** Node and edge ordering in the response is deterministic: nodes sorted by `id`, edges sorted by `(source, target, type)`. Matches v0 ordering conventions.

### Rendering and layout

- **Layout: per-guideline `dagre` clusters with shared entities positioned centrally.** Each guideline subgraph forms a tree-ish cluster (Guideline → Recs → Strategies → Actions). Shared entities (Medications, etc.) sit in a central zone where multiple guidelines point to them. Use Cytoscape's `fcose` or `cola` layout with compound nodes if `dagre`-per-cluster is too rigid; author picks the algorithm that reads best and documents the choice in `docs/specs/ui.md`.
- **Domain coloring.** Nodes styled by domain: USPSTF blue, ACC/AHA purple, KDIGO green. Shared entities neutral gray. Edges inherit color from source node's domain for intra-guideline edges; cross-guideline edges (post-F25/F26) get a distinct treatment deferred to F29.
- **Domain badges.** Rec and Strategy nodes display a small domain label (USPSTF/ACC-AHA/KDIGO text) in the node body. Shared entities do not.
- **Selection and focus.** Clicking a node: opens the detail panel, highlights the node with a focus ring, syncs URL `?focus=<node_id>`. Clicking background: closes detail panel, clears focus. URL-driven: loading a page with `?focus=X` selects that node and pans/zooms to it.
- **Filter interaction.** Toggling a domain off hides the relevant guideline-scoped nodes and edges; it does NOT re-fetch. The client hides via Cytoscape's `.hide()` rather than removing elements, so re-toggling is instant. Shared entities remain visible even if all referencing guidelines are hidden (documented in `ui.md`).
- **No animation on layout changes** beyond Cytoscape defaults. Fancy transitions are deferred.

### URL state

- `?domains=uspstf,acc-aha,kdigo` (lowercase, hyphenated; matches label scheme if lowercased). Default (no param) = all three.
- `?focus=<node_id>` selects and centers a node.
- Filter state persists to localStorage as a usability nicety; URL wins on page load conflict.
- URL updates are push, not replace, so back button navigates through filter states.

### Performance

- **Initial render target:** < 2s on a machine with the full v1 graph loaded (≈ 400-600 nodes after F23 and F24 land).
- **Filter toggle:** < 100ms to apply visibility change. No re-fetch.
- **Node click:** < 50ms to open detail panel.
- **Bulk subgraph fetch:** < 500ms server-side for the full forest in v1 scale.

Performance not met: log in `docs/ISSUES.md` for v2 tuning. Do not ship a visibly-laggy Explore.

### Accessibility

- DomainFilter is a proper multi-select with keyboard navigation (Space/Enter to toggle, arrow keys to move).
- Cytoscape canvas is known to be weak on a11y. Acceptable for v1; log the limitation in `ui.md` as a v2 item.
- Node detail panel is keyboard-navigable (Escape closes, Tab cycles focus).
- Domain badges use sufficient color contrast.

## Verification targets

- `cd ui && npm test` — unit tests pass.
- `cd ui && npx playwright test tests/e2e/explore.spec.ts` — e2e tests pass.
- `cd api && uv run pytest api/tests/routes/test_subgraph.py api/tests/queries/test_subgraph_query.py` — exits 0.
- Manual: load `/explore` with all three guidelines seeded; verify all three render with correct coloring and layout.
- Manual: toggle each domain off in turn; verify nodes hide and shared entities remain; URL updates.
- Manual: click a node; detail panel opens; URL updates with `?focus=`; navigate via URL directly and confirm node re-focuses on reload.
- Manual: load `/explore?domains=kdigo`; only KDIGO + shared entities render.
- Manual: load `/explore?domains=`; only shared entities render.
- Manual: load an old v0 URL (`/explore?g=guideline:uspstf-statin-2022&r=...`); page loads with all guidelines visible and no crash.
- Screenshots captured for PR body: (1) full forest view, (2) single-domain filter, (3) node focused, (4) old URL redirect.
- Performance check (document in PR body): initial render time, filter toggle time, node click latency.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Playwright e2e test covers the core flow end to end.
- `docs/specs/ui.md` rewritten to reflect the new Explore model.
- `docs/contracts/api.openapi.yaml` updated with the new endpoint.
- `docs/reference/build-status.md` backlog row updated.
- Performance numbers documented in PR body.
- Screenshots in PR body.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Preemption visualization (F29).
- Modifier visualization (F29).
- Multi-guideline rec list on Eval tab (F30).
- Search / find-by-name in Explore (deferred to v2).
- Graph path-finding or shortest-path queries.
- Editing the graph from the UI. Read-only.
- Node grouping or collapsing clusters manually.
- Mobile / narrow viewport support.
- Keyboard-driven canvas navigation (pan/zoom via keys). Mouse/trackpad only for v1.
- Exporting the graph as PNG/SVG. Deferred.
- Alternative layouts toggle (force vs. hierarchical vs. circular). Pick one good layout; ship it.

## Design notes (not blocking, worth review)

- **Why abandon hierarchical column navigation.** It was v0 training wheels: one guideline, clear hierarchy, easy to implement. With cross-guideline edges coming in F25/F26, the hierarchy model breaks (a Rec in one column has an edge to a Rec in another column but there's no visual affordance for that edge). Whole-forest canvas is the right substrate for everything v1 needs to show.
- **Layout algorithm choice.** `dagre` is the cleanest for per-guideline tree rendering but awkward when shared entities (many incoming edges from different trees) need positioning. `fcose` handles this better but is less structured. Recommendation: start with `fcose` configured with cluster hints via compound nodes (one compound per guideline, shared entities outside). If that reads poorly, fall back to `dagre`-per-cluster with manual shared-entity positioning. Document whichever wins.
- **Focus-vs-filter.** Filter is domain-level (coarse). Focus is node-level (fine). Both live in URL so links are shareable. No third level of navigation in v1.
- **Cross-guideline edges.** These don't exist until F25/F26, but GraphCanvas should render them correctly once they do. Build in the domain-differentiated edge styling hook now (e.g., `edge.data('is_cross_guideline')` check); F29 lights it up with actual arrows and annotations.
- **Detail panel content.** Reuse whatever v0's panel showed for node properties. Add: codes list for shared entities (RxNorm/SNOMED/ICD-10-CM/LOINC/CPT), domain badge for guideline-scoped nodes. Don't design a new detail panel; preserve what works.
- **Backward compatibility with v0 URLs.** Technically a broken URL for anyone who bookmarked the column view. Since v0 was an internal demo with no real external users, accept the break. Log a console warning if legacy params are detected, to help developers notice during dev.
- **Why include shared entities when `domains=` is empty.** A forest view with zero guidelines selected could reasonably show nothing, but the shared entity registry is itself useful (it's where RxNorm codes live, it's navigable). Showing it on empty-filter is a mild UX choice; consider default-redirect to `domains=uspstf,acc-aha,kdigo` if the empty case is confusing in testing.
- **Why not stream.** v1 graph sizes are small enough that bulk fetch + client-side rendering is fine. Streaming or incremental loading is a v2 concern if graph sizes grow.
- **Test size.** e2e tests are slower than unit tests; limit Playwright to one "happy path" spec for this feature. Don't try to cover every filter combo via Playwright; cover those via GraphCanvas unit tests.
