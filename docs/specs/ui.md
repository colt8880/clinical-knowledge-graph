# UI

**v0 (ADR 0013, 0014).** Next.js app at `/ui`. One application, two tabs:

- **Eval** (`/app/eval`) — step-through replay of an `EvalTrace`. The primary demo surface.
- **Explore** (`/app/explore`) — manual graph traversal. Clinician-style lookup: pick a node, expand neighbors, inspect provenance.

Both tabs share one graph-render component so the Eval tab can highlight current-step nodes using the same visual as the Explore tab.

This file replaces the former `review-workflow.md`. Review-workflow features (flagging, curator queue, proposed-edit workflow) are deferred post-v0; see ADR 0014.

## Load before working here

1. `docs/contracts/api.openapi.yaml` — the full API surface. The UI only talks to this API.
2. `docs/contracts/eval-trace.schema.json` — the Eval tab consumes this.
3. `docs/specs/eval-trace.md` — event semantics the stepper renders.
4. `docs/specs/schema.md` — node/edge types rendered in both tabs.
5. `docs/decisions/0004-nextjs-cytoscape-review-tool.md` — tech choice (still applies).

## Stack

- Next.js 14 (App Router), TypeScript.
- Cytoscape.js for graph rendering. Single `<GraphCanvas>` component used by both tabs.
- OpenAPI-generated TS client (`openapi-typescript-codegen` or equivalent) for the `/api` surface. Regenerated in CI whenever `api.openapi.yaml` changes.
- No server state management library in v0. React Query for API data, plain `useState` for UI state.
- No auth in v0. Single-team use.

## Shared component: `GraphCanvas`

One Cytoscape instance. Accepts:
- `nodes: GraphNode[]`, `edges: GraphEdge[]` (from `/nodes/{id}/neighbors` or an in-memory subgraph computed from a trace).
- `highlight: { nodeIds?: string[], edgeIds?: string[] }` — styling overlay for "current step" in the Eval tab or "selected node" in Explore.
- `onNodeClick`, `onNodeHover` — callbacks.
- Layout: `breadthfirst` for small neighborhoods, `cose` for dense ones. Don't auto-switch — keep it predictable.

Node labels must render the human-readable `name` or `title`, not the id. This is a core principle (clinician-reviewable) and the component should fail a render check if a node lacks one.

## Explore — guideline-first navigation (`/app/explore`)

### Goal

Clinician-oriented guideline inspection. The primary flow: land on the guideline index, pick a guideline, inspect its encoded logic in isolation, check coverage, verify provenance. The whole-forest view is preserved at `/explore/all` for engineers.

### Structure (F31)

Two-level hierarchy:

1. **Guideline index** (`/explore`) — landing page. Cards for each guideline + one "All guidelines (forest view)" card linking to `/explore/all`.
2. **Per-guideline detail** (`/explore/<slug>`) — three tabs: Logic, Coverage, Provenance.
3. **Whole-forest view** (`/explore/all`) — preserved F28 canvas with domain filter. Not the default.

### Guideline index (`/explore`)

- Fetches `GET /guidelines` for metadata.
- Renders `GuidelineIndex` → `GuidelineCard` grid.
- Each card shows: domain badge, title, version, rec count, coverage summary (modeled count, deferred list).
- Clicking a card navigates to `/explore/<slug>`.
- "All guidelines" card navigates to `/explore/all`.
- Backward compatibility: `/explore?domains=X` redirects to `/explore/all?domains=X`.

### Per-guideline detail (`/explore/<slug>`)

Three tabs, URL-synced via `?tab=logic|coverage|provenance`. Default: `logic`.

#### Logic tab

Wraps `GraphCanvas` in scoped mode. Shows only the target guideline's nodes + shared clinical entities reachable from its strategies. No domain filter sidebar (implicitly one domain).

- **Nodes included:** Guideline, Recommendation, Strategy nodes with the target domain + shared entities (Medication, Condition, Observation, Procedure) reachable via edges from the guideline's nodes.
- **Edges included:** all edges where both endpoints are in scope. `PREEMPTED_BY` and `MODIFIES` edges excluded from rendering (other endpoint out of scope).
- **Cross-guideline badge:** nodes with incoming cross-guideline edges show an amber badge linking to `/interactions?focus=<node_id>` (F32).
- **Layout:** column-based (Guideline → Recs → Strategies → Actions). Reads cleaner than cose-bilkent for single-domain view.
- **Node detail panel:** right sidebar with NL predicate rendering by default, JSON toggle.

#### Coverage tab

Renders `Guideline.coverage` from the graph. Author-declared, not inferred.

- Modeled Recs table: label + rec_id, with grade badges where applicable.
- Deferred areas: bulleted list.
- Exit-only areas: bulleted list.
- HTML table — fully accessible.

#### Provenance tab

Guideline-level provenance: domain, title, version, publication date, citation URL, seed hash (SHA-256), last-updated-in-graph timestamp, rec count. HTML table — fully accessible.

### Whole-forest view (`/explore/all`)

Preserved F28 behavior. Same domain filter, same cose-bilkent layout, same interactions. URL params `?domains=` and `?focus=` work as before. Filter state persisted to localStorage.

### Predicate natural-language rendering (F31)

- Default on in NodeDetail. JSON is a toggle ("Show JSON" / "Show Natural Language").
- Catalog-driven: `nl_template` field on each predicate in `predicate-catalog.yaml`.
- Composite handling: `all_of` → AND, `any_of` → OR, `none_of` → NOT. Nested composites parenthesized.
- Fallback: missing template → render raw `predicate_name(args)` + `console.warn`.
- Pure function: `predicateToNaturalLanguage(tree) → string`.

### URL state

- `/explore` — index.
- `/explore/all` — full forest (F28). `?domains=` and `?focus=` preserved.
- `/explore/<slug>?tab=logic|coverage|provenance&focus=<node_id>` — per-guideline detail.

### Accessibility

- Guideline cards are keyboard-navigable; Enter opens detail.
- Tabs use ARIA tab role; arrow keys switch.
- NodeDetail predicate tree is readable by screen readers (plain text, not canvas-rendered).
- Coverage and Provenance views are HTML tables, not canvas; fully accessible.
- DomainFilter on `/explore/all` is a group of checkboxes with keyboard navigation.

### Performance targets

- Index load: < 300ms.
- Scoped Logic view initial render: < 1s.
- Tab switch: < 100ms (no re-fetch).
- Full forest render: < 2s.

### Out of scope

- Source-alongside-encoding view (F33).
- Scenario / patient builder (F34).
- Annotations / sign-off workflow.
- Editing guidelines from the UI.
- Search / fuzzy node finder across guidelines.
- Exporting as PDF/PNG.
- Mobile / narrow viewport.

## Eval tab (`/app/eval`)

### Goal

Given a `PatientContext`, produce a recommendation set by running the evaluator, and let the user step through every event in the trace — with the current step visually located in a graph view and its inputs shown in a side panel. This is the "determinism made visible" demo.

### Surfaces

- **Case picker** (top). Dropdown of the 5 v0 patient fixtures (sourced from `evals/fixtures/statins/<case>/patient.json` — shipped into the UI as static JSON for v0). Optional file-upload of a custom `PatientContext` JSON.
- **Run button**. Calls `POST /evaluate` with the selected patient context. Response is the full `EvalTrace`.
- **Event stepper** (left panel). Ordered list of events with `seq` and `type`. Current step is highlighted. Controls:
  - Prev / Next buttons.
  - Jump-to-step input.
  - Filter toggles: show/hide `predicate_evaluated` (the verbose ones), show/hide `composite_resolved`.
  - Keyboard: `j`/`k` or arrow keys for prev/next. Space for play.
- **`GraphCanvas` view** (center). Shows the subgraph relevant to the current step:
  - For `recommendation_considered`, `eligibility_evaluation_*`, `predicate_evaluated`: the Recommendation node + the clinical entity nodes the predicate reads (via node-id refs in `args`). Highlight the Rec node.
  - For `strategy_considered`, `action_checked`, `strategy_resolved`: the Rec → Strategy → clinical entity actions. Highlight the current Strategy and the most recently checked action.
  - For `risk_score_lookup`: a pseudo-node for the score + edges to the patient-context inputs read. Rendered inline with `pooled_cohort_equations_2013_goff` as the subtitle.
  - For `exit_condition_triggered` / `recommendation_emitted`: highlight the terminal Rec node with the outcome badge.
- **Event detail panel** (right). For the current event, renders:
  - Event type and `seq`.
  - Full payload, pretty-printed.
  - `inputs_read` as a readable table: source, locator, value, present.
  - For `predicate_evaluated`: predicate signature (from the catalog), args, result, and any `missing_data_policy_applied`.
  - For `risk_score_lookup` computed from inputs: a sub-panel that shows the ASCVD inputs, method, and output, in that order.
- **Recommendations strip** (bottom). Compact read of `trace.recommendations` (the derived view). Each item shows status badge, grade, and reason.

### Interactions

- Selecting a node in the graph while in Eval tab does NOT change the current step. The stepper is the source of truth.
- "Open in Explore" button on any highlighted node → navigates to Explore tab with that node selected.
- URL state: `/eval?case=<case_id>&seq=<n>`. Step number in the URL so specific events can be linked.

### Out of scope in v0

- Editing or replaying against a modified `PatientContext` in-place (user uploads a new JSON instead).
- Animated transitions between steps.
- Side-by-side trace diff (for comparing two runs).

## Visual language: preemption and modifiers (F29)

Cross-guideline semantics are rendered via Cytoscape style rules keyed off node/edge data, not eval-mode flags. Both Explore and Eval tabs share these styles.

### Preempted Rec nodes

- **Opacity:** 0.4 (dimmed, not hidden — dimming communicates "evaluated and consciously suppressed").
- **Outline:** dashed border.
- **Label suffix:** `(preempted by <winner_short_id>)` appended to the node label.
- **Class:** `.preempted` applied via `recState.preemptedBy`.

### PREEMPTED_BY edges

- **Stroke:** 3px width (thicker than normal edges), solid line.
- **Color:** desaturated red (`#991b1b`).
- **Arrow:** from preempted → winner, scale 1.2.
- **Hover tooltip:** shows `edge_priority` and `reason`.

### MODIFIES edges

- **Stroke:** 2px width, dotted line.
- **Color:** amber (`#d97706`).
- **Hover tooltip:** shows `nature`, `note`, and source guideline.

### Modifier badge on target Recs

- **Visual:** amber border highlight (`.has-modifiers` class) + `[mod: N]` label suffix.
- **Hover tooltip:** shows count of active modifiers.
- **Multiple modifiers:** stack in the tooltip, not on the badge.

### Domain filter interaction

When a domain filter hides the source of a `PREEMPTED_BY` or `MODIFIES` edge:
- The edge is hidden.
- The target Rec shows a `.cross-edge-filtered` indicator (dotted gray border) so users understand why preemption/modification is not visible when one exists in the graph.

### Trace stepper event icons

- `preemption_resolved`: strikethrough `Rec` + "Preempted" label (red background). Clicking navigates the canvas to highlight both preempted and winner nodes.
- `cross_guideline_match`: bidirectional arrow + "Modifier" label (orange background). Clicking highlights the target Rec.

## Styling and copy

- Grade badges: B → filled green, C → outlined amber, I → outlined gray, `not_applicable` / exit → muted neutral. Colors are accessible (WCAG AA); never encode meaning in color alone — always pair with text.
- Event-type icons are nice-to-have, not required. If added, pair with a visible text label.
- No marketing copy. The app is a tool, not a product landing page.

## Definition of done

The Eval tab is done when:
1. The 5 v0 patient fixtures each render a complete, navigable trace end-to-end.
2. Every event type in `eval-trace.schema.json` has a dedicated rendering in the detail panel (no "raw JSON" fallback for v0 event types).
3. The current-step highlight in `GraphCanvas` is deterministic and survives step navigation.
4. URL state is round-trippable.

The Explore tab is done when:
1. `/search` results load in under 200ms on the seeded graph.
2. Every node rendered shows its human-readable label, code list, and provenance in the detail panel.
3. Neighbor expansion works for all node types in the v0 seed.

## Interactions view (`/interactions`) (F32)

### Goal

Edge-first view of cross-guideline connections. Answers: "Which guidelines conflict?" "What does ACC/AHA override from USPSTF?" "Which modifiers does KDIGO apply?" One screen, no noise — only `PREEMPTED_BY` and `MODIFIES` edges rendered, with each guideline collapsed to a single compound cluster.

### Structure

Single-route view at `/interactions`. Three-panel layout:

1. **Left sidebar (`InteractionsLegend`):** edge-type filter (Preemptions / Modifiers / Both), guideline-pair filter chips, legend (color/style key), summary counts.
2. **Center canvas (`InteractionsCanvas`):** collapsed graph — each guideline is a compound Cytoscape node containing only Recs with cross-guideline edges. `PREEMPTED_BY` and `MODIFIES` edges rendered between cluster children. No within-guideline edges.
3. **Right panel (`InteractionDetail`):** selected edge or node detail. For `PREEMPTED_BY`: preempted Rec, winner Rec, priority, reason, "Open in Explore" links. For `MODIFIES`: source Rec, target Rec, nature, note, suppression flag. For clusters: roll-up counts. For Recs: participation summary + "Open in Explore."

### Visual language

- **Preemption arrows:** 3px desaturated red (`#991b1b`), solid, arrowhead preempted → winner. Reuses F29 styling.
- **Modifier edges:** 2px dotted amber (`#d97706`). Reuses F29 styling.
- **Suppressed modifier:** amber dotted stroke with opacity 0.5. Detail panel explicitly states "This modifier is suppressed by a preemption on the target Rec."
- **Collapsed guideline clusters:** compound Cytoscape nodes with guideline title header, domain-colored border (blue USPSTF, purple ACC/AHA, green KDIGO per F28 palette). Fixed triangle layout: USPSTF top, ACC/AHA bottom-right, KDIGO bottom-left.
- **Preempted Recs:** opacity 0.4, dashed outline (consistent with F29).

### Interactions

- Click edge → detail panel; URL syncs `?focus=<edge_id>`.
- Click Rec → detail panel with participation summary and "Open in Explore" link.
- Click cluster header → cluster roll-up.
- Click background → closes panel.
- Edge-type filter: toggles edge visibility; no re-fetch.
- Guideline-pair filter: multi-select chips; toggle to hide edges by endpoint pair.

### URL state

`?type=preemption|modifier|both`, `?guidelines=uspstf,acc-aha,kdigo`, `?focus=<node_or_edge_id>`. All round-trippable.

### Navigation

- **From Explore (F31):** cross-guideline badge on a scoped Rec deep-links to `/interactions?focus=<node_id>`.
- **To Explore:** every Rec and edge endpoint has "Open in Explore" link navigating to `/explore/<guideline>?focus=<rec_id>`.
- **Top-level nav:** "Interactions" link in app header alongside Explore and Eval.

### API

`GET /interactions?type=preemption|modifier|both&guidelines=uspstf,acc-aha,kdigo` returns the minimal cross-guideline structure: guidelines, recommendations (only those with cross-guideline edges), shared entities (empty in v1), and edges with full metadata.

### Accessibility

- Legend controls keyboard-navigable (radio group for edge type, checkboxes for pairs).
- Detail panel is HTML, not canvas-rendered — screen-reader accessible.
- Canvas inherits Cytoscape's known a11y limits (same as F28).

### Performance

- Initial render: < 1s for v1 edge counts (~15 edges).
- Filter toggle: < 100ms (no re-fetch).
- Layout: seeded cose-bilkent with compound constraints; deterministic across renders.

### Out of scope

- Cascade visualization.
- LLM-generated explanation text.
- Editing edges from UI. Read-only.
- Timeline / version-diff view.
- Heat map / matrix view.
- Export.
- Mobile / narrow viewport.

## Related

- `docs/contracts/api.openapi.yaml`
- `docs/specs/eval-trace.md`
- `docs/decisions/0004-nextjs-cytoscape-review-tool.md`
- `docs/decisions/0014-v0-scope-and-structure.md`
