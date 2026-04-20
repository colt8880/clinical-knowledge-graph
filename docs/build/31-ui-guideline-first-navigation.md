# 31: UI guideline-first navigation (index + single-guideline detail)

**Status**: shipped
**Depends on**: 28, 29
**Components touched**: ui / api / docs
**Branch**: `feat/ui-guideline-first-nav`

## Context

The current `/explore` surface (shipped in F28) puts the whole-forest graph first: land on `/explore`, see every guideline at once, filter domains off to narrow down. That's the right view for engineers debugging the graph, but it's the wrong primary surface for a clinician validating a single guideline's encoding. Clinicians work one guideline at a time. They want: pick a guideline, inspect its logic in isolation, check coverage, verify provenance.

This feature reshapes `/explore` into a two-level structure: a guideline **index** as the landing page and a per-guideline **detail view** that scopes the graph to one guideline plus the shared entities it touches. Cross-guideline edges are intentionally not surfaced here — that's F32's job. The whole-forest view stays reachable via an "All guidelines" entry on the index (same canvas F28 built), so we don't lose the debugging surface, but it stops being the default.

Motivation: clinician review of encoded guidelines is the primary production use case for this app. The UI architecture should optimize for that flow, not for the multi-guideline demo shot. Colton validated the split (single-guideline detail ≠ cross-guideline edges) directly.

## Required reading

- `docs/build/28-ui-domain-filter.md` — the whole-forest canvas this refactor reorganizes around. Understand how `GraphCanvas` already consumes `nodes`/`edges` and `visibleDomains`.
- `docs/build/29-ui-preemption-modifier-viz.md` — visual language for preempted nodes and modifier badges that carry over into the scoped view.
- `docs/specs/ui.md` — current Explore spec; will be rewritten in this feature.
- `docs/specs/predicate-dsl.md` — predicate signatures that drive the natural-language rendering.
- `docs/contracts/predicate-catalog.yaml` — catalog to map predicates to their human-readable templates.
- `docs/contracts/api.openapi.yaml` — current endpoints; adds a guidelines-list endpoint.
- `docs/reference/guidelines/statins.md`, `cholesterol.md`, `kdigo-ckd.md` — per-guideline modeling docs; Coverage panel renders from these.
- `ui/CLAUDE.md` — UI scope and conventions.
- `ui/app/explore/page.tsx` — current whole-forest implementation being refactored.
- `ui/components/GraphCanvas.tsx` — shared canvas; this feature uses it in scoped mode.

## Scope

### UI

- `ui/app/explore/page.tsx` — **rewrite**. New behavior: renders the guideline index (not the whole-forest canvas). Lists each guideline as a card with title, version, domain badge, evidence-body source, Rec count, coverage status. Includes one "All guidelines (forest view)" card that routes to the existing whole-forest canvas, preserved at `/explore/all`.
- `ui/app/explore/all/page.tsx` — **new**. Hosts the whole-forest canvas that `/explore` used to render. Copy the existing page's logic verbatim; no behavioral change. URL params preserved (`?domains=`, `?focus=`).
- `ui/app/explore/[guideline]/page.tsx` — **new**. Per-guideline detail view. Param `guideline` is the domain slug (`uspstf-statin-2022`, `acc-aha-cholesterol-2018`, `kdigo-ckd-2024`). Renders a three-pane layout: tab bar (Logic | Coverage | Provenance) + main panel + node detail panel. Default tab: Logic.
- `ui/components/GuidelineIndex.tsx` — **new**. Index card grid. Consumes the new `/guidelines` endpoint response.
- `ui/components/GuidelineCard.tsx` — **new**. Single card: domain-colored header, title, version/citation line, Rec count, coverage status (e.g., "Modeled: 3 grades · Deferred: secondary prevention, pregnancy"), click navigates to `/explore/[guideline]`.
- `ui/components/GuidelineDetailTabs.tsx` — **new**. Tab bar for the detail page. Tabs: Logic, Coverage, Provenance. URL-synced via `?tab=`.
- `ui/components/LogicView.tsx` — **new**. Wraps `GraphCanvas` in scoped mode: passes only the selected guideline's nodes + the shared clinical entities it references. No domain filter sidebar here (it's implicitly one domain). F29's preempted-node styling still applies when `preempted_by` is set, but `PREEMPTED_BY` and `MODIFIES` edges are **not rendered** because their other endpoint is out of scope — instead, any node with an incoming cross-guideline edge shows a small "has cross-guideline interactions" badge that deep-links to `/interactions?focus=<node_id>` (F32).
- `ui/components/CoverageView.tsx` — **new**. Renders the guideline's coverage summary: modeled Recs (with grade), deferred areas, exit-only areas. Sources from a new `coverage` block on the guideline metadata (see API scope below). Rendered as a plain structured table; no graph.
- `ui/components/ProvenanceView.tsx` — **new**. Guideline-level provenance panel: source organization, publication date, version, citation URL, hash of the seed cypher, last-updated-in-graph timestamp. Per-Rec provenance stays in `NodeDetail`; this is the roll-up.
- `ui/components/NodeDetail.tsx` — **extend**. Add predicate-tree rendering in natural-language mode by default, with a "Show JSON" toggle for the raw predicate tree. The NL rendering walks the predicate catalog to build the sentence (e.g., `age_in_range(40, 75) AND any_of([...]) AND ascvd_10yr_gte(0.10)` → "Patient is age 40–75 AND has at least one of [dyslipidemia, diabetes, hypertension, smoker] AND 10-year ASCVD risk ≥ 10%").
- `ui/lib/predicates/naturalLanguage.ts` — **new**. Pure function: predicate tree + catalog → string. Handles `and`/`or`/`not` with proper grouping; numeric comparisons use inclusive/exclusive bounds from the catalog; unknown predicates fall back to `<predicate_name>(<args>)` with a warning in the console.
- `ui/lib/explore/scopedSubgraph.ts` — **new**. Given the `/subgraph?domains=X` response and a target guideline slug, returns just that guideline's guideline-scoped nodes + the shared entities with at least one incoming edge from that set. Pure function; unit-tested.
- `ui/lib/api/client.ts` — **extend**. Add `fetchGuidelines()` calling the new `/guidelines` endpoint. `fetchSubgraph({ domains })` is reused for scoped mode by passing a single-domain array.
- `ui/tests/components/GuidelineIndex.test.tsx`, `ui/tests/components/GuidelineCard.test.tsx`, `ui/tests/components/LogicView.test.tsx`, `ui/tests/components/CoverageView.test.tsx`, `ui/tests/components/ProvenanceView.test.tsx` — unit tests.
- `ui/tests/lib/naturalLanguage.test.ts` — unit tests for predicate rendering. Cover: nested and/or, numeric comparison bounds, unknown predicate fallback, single-predicate vs composite.
- `ui/tests/lib/scopedSubgraph.test.ts` — unit test. Cover: shared entities with edges from target guideline are kept; shared entities referenced only by other guidelines are dropped; cross-guideline edges are dropped.
- `ui/tests/e2e/guideline-detail.spec.ts` — Playwright. Load `/explore`, verify three guideline cards + one "All guidelines" card. Click USPSTF card; verify Logic tab renders only USPSTF nodes + shared entities; verify a Rec node with a known preemption shows the "cross-guideline interactions" badge; switch to Coverage; verify modeled/deferred lists render; switch to Provenance; verify citation is visible. Reload with `?tab=coverage`; verify tab state restored.

### API

- `api/app/routes/guidelines.py` — **new**. `GET /guidelines` returns a list of guideline metadata:
  ```
  [
    {
      "id": "uspstf-statin-2022",
      "domain": "USPSTF",
      "title": "Statin Use for the Primary Prevention of Cardiovascular Disease in Adults",
      "version": "2022",
      "publication_date": "2022-08-23",
      "citation_url": "https://www.uspreventiveservicestaskforce.org/...",
      "rec_count": 3,
      "coverage": {
        "modeled": [{"label": "Grade B", "rec_id": "..."}, ...],
        "deferred": ["pregnancy", "secondary prevention"],
        "exit_only": ["age < 40", "age > 75"]
      },
      "seed_hash": "<sha256 of the seed cypher>",
      "last_updated_in_graph": "2026-04-18T14:22:00Z"
    }
  ]
  ```
  `coverage` sourced from a new top-level property on the `Guideline` node (see graph scope). `seed_hash` and `last_updated_in_graph` sourced from graph metadata.
- `api/app/queries/guidelines_query.py` — **new**. Cypher for the metadata list.
- `api/app/main.py` — wire the new route.
- `docs/contracts/api.openapi.yaml` — document `GET /guidelines` with request/response schemas.
- `api/tests/routes/test_guidelines.py` — integration tests. Assert: three guidelines returned; coverage block present; response shape matches OpenAPI.
- `api/tests/queries/test_guidelines_query.py` — unit tests for the query.

### Graph

- `graph/seeds/statins.cypher`, `graph/seeds/accaha-cholesterol.cypher`, `graph/seeds/kdigo-ckd.cypher` — **extend** each `Guideline` node with a `coverage` JSON property containing `{modeled, deferred, exit_only}`. Author fills these from the existing guideline modeling docs under `docs/reference/guidelines/`. Keep the property as a JSON string if Neo4j Community doesn't support map properties natively; document the serialization in `docs/specs/schema.md`.
- `docs/specs/schema.md` — **extend**. Document the new `coverage` property on `Guideline`.

### Docs

- `docs/specs/ui.md` — **rewrite** the Explore section. Old single-page whole-forest canvas becomes a nested hierarchy: index → per-guideline detail (Logic | Coverage | Provenance) → shared-entity node detail. Whole-forest canvas moved to `/explore/all`. Cross-guideline interactions view (F32) documented as a cross-reference; full spec lives in F32.
- `docs/reference/build-status.md` — backlog row.

## Constraints

### Scope of the refactor

- **`/explore` becomes the index.** Old `/explore` behavior moves to `/explore/all` with no change. Links like `/explore?domains=kdigo` get a one-time redirect to `/explore/all?domains=kdigo` for backward compatibility; drop after one release.
- **No new graph-rendering library.** Everything reuses `GraphCanvas` from F28.
- **Visual language is preserved.** F29's preempted-node styling (opacity 0.4, dashed outline, `(preempted)` suffix) still applies on the scoped Logic view when a Rec has `preempted_by` set, even though the edge isn't rendered. Tooltip on the dimmed Rec says "Preempted by <winner>; see cross-guideline view" with a link to F32's view.

### Scoped Logic view

- **Nodes included:** the target guideline's `Guideline`, `Recommendation`, `Strategy` nodes plus all shared clinical entity nodes (`Medication`, `Condition`, `Observation`, `Procedure`) reachable via outgoing edges from the guideline's `Strategy` nodes.
- **Edges included:** all edges where both endpoints are in the included node set. `PREEMPTED_BY` and `MODIFIES` edges where the other endpoint is out of scope are **excluded from rendering** but **surfaced as a badge** on the in-scope node (clickable, deep-links to F32's view scoped to that node).
- **Layout:** dagre tree per guideline. Without cross-cluster noise, dagre reads cleaner than cose-bilkent here. Shared entities form a strip at the bottom where the action fan-out converges. Document this choice in `ui.md`.
- **Domain filter sidebar is removed on this view.** Implicit one-domain scope; the filter control would be inert.

### Predicate natural-language rendering

- **Default on.** The NodeDetail panel shows NL by default. JSON is a toggle, not the primary view.
- **Catalog-driven, not hand-written per Rec.** `docs/contracts/predicate-catalog.yaml` gets a new optional `nl_template` field per predicate (e.g., `age_in_range: "Patient is age {min}–{max}"`, `ascvd_10yr_gte: "10-year ASCVD risk ≥ {0:.0%}"`). The rendering function reads `nl_template` if present and falls back to `<name>(<args>)` otherwise.
- **Composite handling:** `and` joins with " AND "; `or` joins with " OR "; nested composites parenthesize. `not` prefixes with "NOT ". No fancy prose smoothing in v1 (no "and/or", no commas before the last term); readability is good enough without natural-language prose generation.
- **Fallback policy:** missing template → render raw and log a `console.warn` during dev. Never fail rendering.

### Coverage data

- Sourced from the `Guideline.coverage` property added in graph scope. Populated by the seed author when the seed is written.
- **No inference.** The Coverage view renders what the seed declares. If the seed says "deferred: secondary prevention," that's what shows. Keeping this author-declared rather than inferred avoids false assurance from the UI.

### URL state

- `/explore` — index.
- `/explore/all` — full forest (F28's canvas, preserved).
- `/explore/<guideline_id>?tab=logic|coverage|provenance&focus=<node_id>` — per-guideline detail.
- Default tab: `logic`. Default focus: none.
- Clicking a node in the Logic view syncs `?focus=`; deep links restore focus and pan/zoom.

### Performance

- Index load: < 300ms (small metadata payload).
- Scoped Logic view initial render: < 1s (one guideline's subgraph is ~100–200 nodes max).
- Tab switch: < 100ms (no re-fetch; components already hydrated).
- Predicate NL rendering: O(nodes in predicate tree); < 5ms per node.

### Accessibility

- Guideline cards are keyboard-navigable; Enter opens detail.
- Tabs use ARIA tab role; arrow keys switch.
- NodeDetail predicate tree is readable by screen readers (plain text, not canvas-rendered).
- Coverage and Provenance views are HTML tables, not canvas; fully accessible.

## Verification targets

- `cd ui && npm test` — unit tests pass, including new `naturalLanguage.test.ts` and `scopedSubgraph.test.ts`.
- `cd ui && npx playwright test tests/e2e/guideline-detail.spec.ts` — e2e passes.
- `cd api && uv run pytest api/tests/routes/test_guidelines.py api/tests/queries/test_guidelines_query.py` — exits 0.
- Manual: load `/explore`; verify three guideline cards + one "All guidelines" card render with correct coverage summaries.
- Manual: click the USPSTF card; verify Logic tab shows only USPSTF-scoped nodes + shared statin medications; verify the Rec with `preempted_by` set is dimmed and shows the cross-guideline badge; verify badge click navigates to `/interactions?focus=<node_id>` (expected 404 until F32; a placeholder route returning the node_id is acceptable).
- Manual: switch to Coverage; verify modeled Recs, deferred areas, and exit-only areas each render.
- Manual: switch to Provenance; verify citation URL, version, and seed hash render.
- Manual: click a Rec node; verify NodeDetail shows the predicate tree in NL form; click "Show JSON"; verify JSON toggle works.
- Manual: visit `/explore/all?domains=kdigo`; verify whole-forest canvas renders (F28 behavior preserved).
- Manual: visit `/explore?domains=kdigo`; verify redirect to `/explore/all?domains=kdigo`.
- Screenshots in PR body: (1) index page, (2) USPSTF detail Logic tab, (3) same Coverage tab, (4) Provenance tab, (5) NL predicate rendering, (6) preserved `/explore/all` view.
- Performance numbers documented in PR body.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/specs/ui.md` rewritten.
- `docs/specs/schema.md` updated with `Guideline.coverage`.
- `docs/contracts/api.openapi.yaml` updated.
- `docs/reference/build-status.md` backlog row updated.
- Screenshots and performance numbers in PR body.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- **Source-alongside-encoding view** (rendering the published guideline text next to its encoded Recs with anchored links). High-value but substantial; separate follow-up (F33).
- **Scenario / patient builder** on the detail view (sliders for age, labs, conditions; fast feedback loop). Separate follow-up (F34).
- **Annotations / sign-off workflow** (review comments per node, reviewed/unreviewed state). Separate follow-up; post-v1.
- **Editing guidelines from the UI.** Read-only.
- **Search / fuzzy node finder** across guidelines. Deferred.
- **Exporting** the scoped graph or coverage as PDF/PNG. Deferred.
- **Retiring the whole-forest view.** Preserved at `/explore/all`. Whether to eventually remove it is a post-F32 decision.
- **Mobile / narrow viewport.** Desktop only.
- **Per-Rec coverage status** beyond what `Guideline.coverage` declares. No inferred "fully covered" / "partial" per Rec in v1.

## Design notes (not blocking, worth review)

- **Why not collapse Logic + Coverage + Provenance into one scroll.** They answer different validation questions at different moments. Tabs keep each surface focused. Coverage especially needs to be one screen, not buried below a graph.
- **Why author-declared coverage rather than inferred.** The evaluator only knows what it evaluated; it can't tell you what the seed deliberately omitted versus what was an oversight. Author-declared is honest. Inferring would create a false "100% covered" when really it's "100% of what we encoded, which doesn't include secondary prevention."
- **Why NL predicates default-on.** The JSON predicate tree is illegible at review time. If a clinician has to mentally parse `{"op":"and","operands":[{"op":"in_range","args":["age",40,75]}...]}`, we've failed the clinician-reviewable-by-construction principle. NL is the default; JSON is the escape hatch for engineers.
- **Why keep `/explore/all`.** Two reasons. First, it's the existing implementation — removing it means breaking working behavior during a refactor. Second, the whole-forest view *is* useful for the "show off cross-guideline density" demo and for engineers who want to poke the whole graph. The right move is to demote it from default to opt-in, not delete it.
- **Cross-guideline badge on scoped Logic view.** The tradeoff: either surface cross-guideline interactions in the scoped view (risks confusion about what's in scope) or hide them entirely (loses important information — "this Rec is actually preempted by another guideline"). A badge + deep-link to F32 splits the difference: visible presence, full detail offloaded.
- **Predicate NL templates in the catalog.** The alternative was a per-predicate renderer function in TS. Catalog-driven keeps the catalog as the single source of truth (predicate signature + prose rendering in one place), makes adding a new predicate a single-file change, and is testable without UI code. The tradeoff is less flexibility for irregular predicates; acceptable given the current catalog is small.
- **`dagre` vs `fcose` on scoped view.** With one domain and no cross-cluster edges, dagre's top-down tree reads cleanly (Guideline → Recs → Strategies → Actions → Shared entities). `fcose`'s force-directed layout is overkill and less predictable. If a future guideline has many shared entities or recursive structures, revisit.
- **Index metadata as a graph query vs static file.** Graph query is correct — the seed is the source of truth and a new guideline showing up in the index should require zero app code. Slightly more expensive than a static file; negligible at v1 scale.
- **What about the whole-forest view's domain filter persistence?** F28 persists filter state in localStorage. Preserved as-is on `/explore/all`. The index doesn't need it.
