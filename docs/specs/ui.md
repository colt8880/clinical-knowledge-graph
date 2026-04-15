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

A curator or clinician reviewer can find any node in the graph, see its properties, and walk outward through its edges. Port of the existing `crc-graph.html` sensibilities into React.

### Surfaces

- **Search bar** (top). Calls `GET /search` with free-text `q` and optional `node_types` chips. Debounced.
- **Result list** (left panel). Clicking a result loads the center-node view.
- **`GraphCanvas` view** (center). Shows the center node and its 1-hop neighbors from `GET /nodes/{id}/neighbors`.
- **Detail panel** (right). When a node is selected, renders:
  - `labels` (node type), `id`, human-readable `name` / `title`.
  - Properties in a flat key/value list. `structured_eligibility` JSON pretty-printed; no in-place English-ification in v0 (defer the DSL→English render).
  - Code list.
  - Provenance block (`source_guideline_id`, `source_section`, `effective_date`) — always visible, never behind a click.
- **URL state.** The selected node id lives in the URL (`/explore?node=rec:statin-initiate-grade-b`). Refresh reloads the same view. Links are copy-pasteable.

### Interactions

- Click a neighbor in the graph → it becomes the new center node (pushes a history entry).
- Browser back returns to previous center node.
- Clicking an edge selects the edge and shows edge properties in the detail panel. Edge provenance is required.

### Out of scope in v0

- Editing nodes or edges.
- Flagging or commenting.
- Diff view between graph versions.

## Eval tab (`/app/eval`)

### Goal

Given a `PatientContext`, produce a recommendation set by running the evaluator, and let the user step through every event in the trace — with the current step visually located in a graph view and its inputs shown in a side panel. This is the "determinism made visible" demo.

### Surfaces

- **Case picker** (top). Dropdown of the 5 v0 patient fixtures (sourced from `evals/statins/<case>/patient.json` — shipped into the UI as static JSON for v0). Optional file-upload of a custom `PatientContext` JSON.
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
