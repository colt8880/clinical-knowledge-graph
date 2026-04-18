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

## Explore tab (`/app/explore`)

### Goal

Whole-forest graph canvas showing all guideline subgraphs simultaneously. A domain filter toggles which guidelines are visible. Shared clinical entities (Medications, Conditions, etc.) always render. Clicking any node opens a detail panel with provenance, codes, and domain badge.

This replaced the v0 hierarchical column navigator (F05) as of F28. The column model didn't scale to multiple guidelines or cross-guideline edges.

### Surfaces

- **Domain filter** (left sidebar). Multi-select chip control for USPSTF / ACC-AHA / KDIGO. Toggling a domain hides/shows the relevant guideline-scoped nodes via Cytoscape `.style("display")` — no re-fetch. Shared entities remain visible even when all guidelines are hidden.
- **`GraphCanvas` view** (center). Renders the full forest using cose-bilkent layout with compound nodes (one per guideline cluster). Shared entities sit outside compound nodes. Domain coloring: USPSTF blue, ACC/AHA purple, KDIGO green. Shared entities use neutral type-based colors (Medication pink, Condition red, etc.). Rec/Strategy nodes display a domain label in the node body.
- **Detail panel** (right). When a node is selected:
  - `labels` (node types), `id`, human-readable `name` / `title`.
  - Domain badge for guideline-scoped nodes.
  - Full codes list (RxNorm / SNOMED / ICD-10-CM / LOINC / CPT) for shared entities.
  - Properties in a flat key/value list. `structured_eligibility` rendered as a predicate tree.
  - Provenance block — always visible, never behind a click.
- **URL state.** `?domains=uspstf,acc-aha,kdigo&focus=<node_id>`. Default (no params) = all three domains. URL updates are push (back button navigates filter history). Filter state also persisted to localStorage; URL wins on conflict.

### Data flow

Explore fetches the entire forest via `GET /subgraph` (one bulk call, no pagination). The client filters visibility client-side using Cytoscape's `.style("display", "none")` / `.style("display", "element")`. Re-toggling a domain is instant (< 100ms).

### Layout

**Algorithm:** cose-bilkent with compound nodes. Each guideline domain gets a compound parent node; guideline-scoped nodes are children of their domain's compound. Shared entities sit outside all compounds and are positioned centrally by the layout engine. This produces tree-ish clusters per guideline with shared entities bridging them.

**Choice rationale:** cose-bilkent handles compound nodes well and was already a dependency. Preferred over dagre-per-cluster (too rigid with shared entities) and plain fcose (less structured).

### Interactions

- Click a node → opens detail panel, syncs URL `?focus=<id>`, focus ring on node, pan/zoom to center it.
- Click background → closes detail panel, clears focus.
- Toggle domain chip → hides/shows that domain's nodes and edges. No re-fetch.
- Escape key → closes detail panel.
- URL-driven: loading `/explore?focus=X` selects and centers that node.
- Loading `/explore?domains=kdigo` shows only KDIGO + shared entities.
- Loading `/explore?domains=` shows only shared entities.

### Legacy URL handling

v0's `?g=&r=&s=` params are deprecated. If detected, a console warning is logged and the page loads with all guidelines visible and no focus. No redirect.

### Accessibility

- DomainFilter is a group of checkboxes with keyboard navigation (Space/Enter to toggle, arrow keys to move).
- Node detail panel closes with Escape, is keyboard-navigable via Tab.
- Cytoscape canvas has known a11y limitations (no screen reader support for graph nodes). Documented as v2 item.
- Domain badges use sufficient color contrast.

### Performance targets

- Initial render: < 2s for ~400–600 nodes (full v1 graph).
- Filter toggle: < 100ms.
- Node click to detail panel: < 50ms.
- Bulk subgraph fetch: < 500ms server-side.

### Out of scope

- Search / find-by-name (deferred to v2).
- Editing nodes or edges.
- Flagging or commenting.
- Diff view between graph versions.
- Alternative layout toggle.
- Mobile / narrow viewport.
- Keyboard-driven canvas navigation.
- Export as PNG/SVG.

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

## Related

- `docs/contracts/api.openapi.yaml`
- `docs/specs/eval-trace.md`
- `docs/decisions/0004-nextjs-cytoscape-review-tool.md`
- `docs/decisions/0014-v0-scope-and-structure.md`
