# 32: UI cross-guideline interactions view

**Status**: pending
**Depends on**: 25, 26, 28, 29, 31
**Components touched**: ui / api / docs
**Branch**: `feat/ui-cross-guideline-interactions`

## Context

F31 scoped `/explore` to one guideline at a time, which is the right default for validating encodings. But it intentionally drops cross-guideline edges (`PREEMPTED_BY`, `MODIFIES`) out of the scoped view — a Rec dimmed as "preempted" with no visible arrow to the winner is incomplete. This feature is the other half: a dedicated view that renders *only* the cross-guideline interactions, with each guideline collapsed to a single parent node so the preemption/modifier structure is front and center.

Concretely, this is where a clinician or reviewer asks: "Which guidelines conflict with which?" "What does ACC/AHA override from USPSTF?" "Which shared clinical entities does KDIGO annotate across other guidelines' Recs?" Today those questions require turning on all three domains in the whole-forest view and scanning hundreds of nodes. This view answers them in one screen.

## Required reading

- `docs/build/25-preemption-uspstf-accaha.md` — preemption edge semantics, edge_priority, reason.
- `docs/build/26-modifies-edges-kdigo.md` — MODIFIES edge semantics, nature, note, suppression rules.
- `docs/build/28-ui-domain-filter.md` — the whole-forest canvas primitives this view reuses.
- `docs/build/29-ui-preemption-modifier-viz.md` — visual styling for preempted Recs, PREEMPTED_BY and MODIFIES edges; fully reused here.
- `docs/build/31-ui-guideline-first-navigation.md` — sibling view; this feature links to/from it.
- `docs/specs/ui.md` — overall UI structure; this feature extends it.
- `docs/reference/guidelines/cross-guideline-map.md`, `preemption-map.md` — existing authoring-time maps of cross-guideline edges. Reference for verification.
- `docs/contracts/api.openapi.yaml` — current API surface; adds one endpoint.
- `ui/components/GraphCanvas.tsx` — shared canvas, reused here with different input shape.
- `ui/CLAUDE.md` — UI conventions.

## Scope

### UI

- `ui/app/interactions/page.tsx` — **new**. Top-level route `/interactions`. Renders the cross-guideline interactions canvas plus filter/legend sidebar and a details panel. Query params: `?type=preemption|modifier|both` (default `both`), `?focus=<node_id>`, `?guidelines=uspstf,acc-aha,kdigo` (default all).
- `ui/components/InteractionsCanvas.tsx` — **new**. Wraps `GraphCanvas` but feeds it a **collapsed** graph: each guideline is a single compound node containing only the Recs with at least one incoming or outgoing cross-guideline edge; each shared clinical entity referenced by `MODIFIES` targets is rendered inline. Within-guideline edges (`OFFERS`, `INCLUDES_ACTION`, `TARGETS`) are **not** rendered. Only `PREEMPTED_BY` and `MODIFIES` edges are rendered. F29 styling applies unchanged.
- `ui/components/InteractionsLegend.tsx` — **new**. Left sidebar. Sections:
  - Edge type filter (Preemptions / Modifiers / Both).
  - Guideline-pair filter chips (e.g., "USPSTF ↔ ACC/AHA", "KDIGO → ACC/AHA"). Toggles hide/show edges by endpoint pair.
  - Legend: color and style key for PREEMPTED_BY vs MODIFIES.
  - Summary counts: "5 preemptions · 3 modifiers · 2 shared entities referenced."
- `ui/components/InteractionDetail.tsx` — **new**. Right-side panel rendering the selected edge's full detail:
  - For `PREEMPTED_BY`: preempted Rec, winner Rec, `edge_priority`, `reason`, source guideline of winner, provenance citations for both endpoints, "Open preempted Rec in Explore" and "Open winner Rec in Explore" links back to `/explore/<guideline>?focus=<node_id>` (F31).
  - For `MODIFIES`: source Rec (the modifier), target Rec, `nature`, `note`, whether the modifier is currently suppressed by a preemption, links to both endpoints.
  - Selecting a collapsed guideline node instead shows a roll-up: count of outgoing preemptions, incoming preemptions, modifiers authored, modifiers received.
- `ui/lib/api/client.ts` — **extend**. Add `fetchInteractions()` calling the new `/interactions` endpoint.
- `ui/lib/interactions/collapse.ts` — **new**. Pure function: takes the `/interactions` response and produces the Cytoscape nodes/edges for the collapsed view. Logic: for each `PREEMPTED_BY` or `MODIFIES` edge, include both endpoints as nodes; group Recs under their guideline's compound parent; include shared entities referenced by any `MODIFIES` target (if any exist in v1 semantics; otherwise the set is empty and logic handles it). Unit-tested.
- `ui/lib/interactions/layout.ts` — **new**. Cytoscape layout config for this view. Three fixed guideline clusters (compound nodes) arranged in a triangle; shared-entity row below; cross-edges render between cluster children. `fcose` with strong compound-node constraints, no cluster drift between renders (seeded).
- `ui/tests/components/InteractionsCanvas.test.tsx`, `ui/tests/components/InteractionsLegend.test.tsx`, `ui/tests/components/InteractionDetail.test.tsx` — unit tests.
- `ui/tests/lib/collapse.test.ts` — unit tests. Cover: Recs with no cross-edges are excluded; compound parents always render their guideline id even if no Recs match; `MODIFIES` edges whose target is in a filtered-out guideline are dropped; edge-type filter (preemption vs modifier vs both) correctly subsets edges.
- `ui/tests/e2e/interactions.spec.ts` — Playwright. Load `/interactions`; verify three compound guideline clusters render; verify at least one `PREEMPTED_BY` arrow between USPSTF and ACC/AHA clusters; verify at least one `MODIFIES` edge originating from KDIGO; click the preemption arrow; verify detail panel shows `edge_priority` and both endpoint links; click "Open preempted Rec in Explore"; verify navigation to `/explore/uspstf-statin-2022?focus=<rec_id>`. Toggle edge-type filter to Modifiers only; verify preemption arrows hide. Toggle guideline-pair filter to exclude USPSTF↔ACC-AHA; verify those preemptions hide while KDIGO modifiers remain.
- `ui/app/explore/[guideline]/page.tsx` (from F31) — **extend**. The "cross-guideline interactions" badge placeholder from F31 now routes to `/interactions?focus=<node_id>`, where the view opens zoomed to that node with its connected edges highlighted.

### API

- `api/app/routes/interactions.py` — **new**. `GET /interactions?type=preemption|modifier|both&guidelines=uspstf,acc-aha,kdigo` returns the minimal cross-guideline structure:
  ```
  {
    "guidelines": [
      {"id": "uspstf-statin-2022", "domain": "USPSTF", "title": "..."}
    ],
    "recommendations": [
      {"id": "...", "title": "...", "domain": "USPSTF", "evidence_grade": "B", "has_preemption_in": bool, "has_preemption_out": bool, "modifier_count": int}
    ],
    "shared_entities": [
      {"id": "...", "type": "Medication", "title": "Atorvastatin"}
    ],
    "edges": [
      {"type": "PREEMPTED_BY", "source": "<rec_id>", "target": "<rec_id>", "edge_priority": ..., "reason": "..."},
      {"type": "MODIFIES", "source": "<rec_id>", "target": "<rec_id>", "nature": "...", "note": "...", "suppressed_by_preemption": bool}
    ]
  }
  ```
  Only Recs that participate in at least one edge in the response set are included. Empty `shared_entities` is valid.
- `api/app/queries/interactions_query.py` — **new**. Cypher that matches `PREEMPTED_BY` and `MODIFIES` edges filtered by type and guideline; returns edges and their participating Recs + involved shared entities. One round-trip preferred.
- `api/app/main.py` — wire the new route.
- `docs/contracts/api.openapi.yaml` — document `GET /interactions`.
- `api/tests/routes/test_interactions.py` — integration tests. Assert: (a) full response returns all v1 cross-guideline edges, (b) `type=preemption` filters correctly, (c) `type=modifier` filters correctly, (d) `guidelines=uspstf,acc-aha` excludes KDIGO modifier edges, (e) suppressed-modifier flag matches evaluator semantics, (f) response shape matches OpenAPI, (g) determinism: same query returns same ordering.
- `api/tests/queries/test_interactions_query.py` — unit tests.

### Docs

- `docs/specs/ui.md` — **extend**. Add a new "Interactions view" section covering layout, filters, collapsed-guideline rendering, deep-links to/from Explore.
- `docs/reference/build-status.md` — backlog row.

## Constraints

### Data and semantics

- **This view is edge-first.** Nodes that aren't endpoints of a cross-guideline edge are not rendered. Collapsed guideline clusters are always rendered (even if empty of participating Recs), so the view is visibly consistent across different graph states.
- **No within-guideline edges rendered.** `OFFERS`, `INCLUDES_ACTION`, `TARGETS` are omitted. A user who wants to see what a Rec does deep-links back to F31's Logic view.
- **Suppression is visible.** A `MODIFIES` edge with `suppressed_by_preemption = true` renders with an additional "suppressed" styling layer (e.g., diagonal stripe or greyed stroke) and the detail panel explicitly states "This modifier was suppressed by a preemption on the target Rec." Don't hide suppressed modifiers; hiding reasoning is anti-trace-first.
- **Determinism.** Response and rendering are deterministic. Same graph + same filter state = same rendered layout (seeded `fcose`).
- **Bulk fetch.** One API call loads the view.

### Visual language

- **Preemption arrows:** F29's styling reused verbatim — 3px desaturated red, arrowhead preempted → winner.
- **Modifier edges:** F29's styling reused — 2px dotted amber.
- **Suppressed modifier:** same amber dotted stroke with a diagonal-stripe overlay or a `.suppressed` class that drops opacity to 0.5. Documented in `ui.md`.
- **Collapsed guideline clusters:** each guideline is a compound Cytoscape node with the guideline title as a header, domain-colored border (blue/purple/green per F28 palette), and participating Recs as children. Clusters have fixed positions (triangle: USPSTF top, ACC/AHA right, KDIGO left) to preserve muscle memory across loads. Shared entities row along the bottom.
- **Cluster badges:** top-right of each cluster header shows outgoing preemption count and modifier count. Hover reveals the full breakdown.
- **Dimming preempted Recs:** carried over from F29 (opacity 0.4, dashed outline) so the visual language is consistent.

### Interactions

- Click an edge → detail panel opens; URL syncs `?focus=<edge_id>`.
- Click a Rec node → detail panel shows that Rec's participation (incoming preemptions, outgoing preemptions, modifiers) plus "Open in Explore" link.
- Click a cluster header → detail panel shows the cluster roll-up.
- Click background → closes panel.
- Edge-type filter: toggles edge visibility via Cytoscape `.hide()` / `.show()`; no re-fetch.
- Guideline-pair filter: multi-select chips; toggle off to hide edges where either endpoint is in an excluded guideline.
- URL state: `?type=`, `?guidelines=`, `?focus=` all round-trippable.

### Navigation

- **From Explore:** F31's "cross-guideline interactions" badge on a scoped Rec deep-links to `/interactions?focus=<node_id>`. View opens with the full canvas, the referenced node highlighted and pan/zoomed to.
- **To Explore:** every Rec and every edge endpoint has an "Open in Explore" link that navigates to `/explore/<guideline_id>?focus=<rec_id>`.
- **Top-level nav:** add a link to `/interactions` in the app header alongside Explore and Eval.

### Performance

- Initial render: < 1s for v1 cross-guideline edge counts (expected ~5–15 total across preemption + modifier edges).
- Filter toggle: < 100ms.
- Layout stability: seeded; no jitter on re-render.
- API fetch: < 300ms server-side.

### Accessibility

- Legend controls are keyboard-navigable.
- Detail panel is screen-reader accessible (HTML, not canvas-rendered).
- Cross-edges within the canvas inherit Cytoscape's known a11y limits; documented in `ui.md` alongside F28's note.

## Verification targets

- `cd ui && npm test` — unit tests pass.
- `cd ui && npx playwright test tests/e2e/interactions.spec.ts` — e2e passes.
- `cd api && uv run pytest api/tests/routes/test_interactions.py api/tests/queries/test_interactions_query.py` — exits 0.
- Manual: load `/interactions`; verify three collapsed guideline clusters plus all v1 cross-guideline edges render; verify counts in the legend match the graph's actual edge count.
- Manual: click a `PREEMPTED_BY` arrow; verify detail panel shows preempted Rec, winner Rec, `edge_priority`, `reason`, and two "Open in Explore" links that both navigate correctly.
- Manual: click a `MODIFIES` edge; verify detail panel shows `nature`, `note`, and the suppression flag state.
- Manual: find a suppressed-modifier case in the fixture set; verify it renders with the suppressed styling and the detail panel explicitly calls it out.
- Manual: toggle edge-type filter to Preemptions only; verify modifier edges hide; toggle to Modifiers only; verify preemption edges hide; toggle to Both; verify all return.
- Manual: toggle guideline-pair filter to exclude KDIGO; verify all KDIGO-origin modifier edges hide; counts in legend update.
- Manual: from F31's USPSTF detail view, click the "cross-guideline interactions" badge on a preempted Rec; verify `/interactions?focus=<rec_id>` loads with the Rec highlighted.
- Manual: reload with `?type=preemption&focus=<edge_id>`; verify filter and focus state restored.
- Screenshots in PR body: (1) full interactions canvas with three clusters and all edges, (2) filtered to preemptions only, (3) a preemption edge selected with detail panel, (4) a modifier edge selected, (5) a suppressed modifier, (6) deep-link from F31's Explore view.
- Performance numbers in PR body.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/specs/ui.md` extended with the Interactions view section.
- `docs/contracts/api.openapi.yaml` updated.
- `docs/reference/build-status.md` backlog row updated.
- Screenshots and performance numbers in PR body.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- **Cascade visualization** (e.g., preemption A → B that then modifies C). v1 has no cascading semantics and the evaluator doesn't emit them.
- **Explain-this-conflict text generation** (LLM-rendered prose explaining why a preemption exists). The graph data is the authority; prose is deferred.
- **Editing preemption or modifier edges from the UI.** Read-only.
- **Timeline or version-diff view** of how cross-guideline edges have changed across graph versions. Historical replay is a v2 concern.
- **Heat map / matrix view** (e.g., an NxN guideline-pair matrix showing edge counts). Interesting but different UX; separate follow-up if users ask for it.
- **Exporting** the interactions view.
- **Inline fixture preview** (pick a fixture and see how cross-guideline edges activate for that patient). That's the Eval tab's job; this view is structure-only.
- **Mobile / narrow viewport.**

## Design notes (not blocking, worth review)

- **Why collapse guidelines instead of rendering everything.** The whole-forest canvas (F28) already renders everything and gets visually noisy at v1's ~500 nodes. The value of this view is the signal-to-noise ratio: at v1, maybe 5–15 edges matter for cross-guideline reasoning. Rendering only those edges plus their endpoints, with guideline clusters as anchors, makes the conflict structure a single-glance surface.
- **Fixed triangle layout vs organic force-directed.** Fixed cluster positions are a concession to usability. Clinicians building mental models benefit from "USPSTF is always in the top position." Force-directed layouts drift between renders and erode that. The tradeoff is less visual optimization; worth it.
- **Why render suppressed modifiers at all.** A modifier edge that's currently suppressed by a preemption still exists in the graph and still has clinical meaning ("KDIGO would normally modify this, but ACC/AHA preempted the whole Rec first"). Hiding suppressed modifiers would hide evaluator reasoning. Trace-first principle applies here too.
- **Cluster-header detail vs drill-in.** Showing cluster roll-up counts (preemption in/out, modifier counts) in the header badge plus the detail panel gives two levels of read without requiring a separate drill-in route. Keeps the interaction shallow.
- **Bidirectional deep-link with F31.** F31 surfaces "go see this interaction" via a badge; F32 surfaces "go read this Rec in context" via detail panel links. Each view pushes users toward the other for the question that view can't answer. The alternative (one merged view that tries to do both) is what F28 is, and the motivation for this whole refactor is that F28 doesn't do either job well.
- **What if a future guideline has no cross-guideline edges at all.** Cluster still renders (empty of participating Recs), with badge counts at zero. Visible absence is useful information ("this guideline is currently isolated").
- **Scaling to more guidelines.** Triangle layout works up to ~5–6 guidelines (pentagon/hexagon). Beyond that, the view needs a different layout strategy (concentric rings, force-directed with pinned anchors, or on-demand cluster loading). Revisit post-v1 when a fourth guideline lands.
- **Shared entities section.** In v1, `MODIFIES` targets are Recs, not shared entities, so the shared-entities row is likely empty. Keeping the row in the schema+layout so v2 modifier semantics (if they target shared entities like "Atorvastatin dosing is modified in CKD") don't require a view redesign.
- **Why a separate route `/interactions` vs a tab within `/explore`.** Semantically distinct surface. `/explore` is guideline-first validation; `/interactions` is edge-first reasoning. Making it a sibling route (with top-nav presence) signals this. Nesting it under `/explore` would imply it's just another view of the same thing, which undersells it.
