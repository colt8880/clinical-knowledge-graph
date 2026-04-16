# /ui

Next.js 14 (App Router) app for the v0 slice. One deployment, two tabs sharing a graph canvas:

- **Explore** (`/explore`): manual graph traversal. Search nodes, click to pin, render neighbors via the API, inspect provenance. Spiritual successor to `diagrams/crc-graph.html`, but live against `/api`.
- **Eval** (`/eval`): pick a fixture from `evals/fixtures/statins/`, run it via `POST /evaluate`, step through the returned `EvalTrace` event-by-event with keyboard (j/k), highlight the node(s) involved in the current event on the shared graph canvas, render the derived recommendation list.

## Stack

- Next.js 14 (App Router), TypeScript strict
- Cytoscape.js for graph rendering (shared `GraphCanvas` component)
- `@tanstack/react-query` for data fetching
- `openapi-typescript` codegen against `../docs/contracts/api.openapi.yaml` in CI; do not hand-write types for API responses

## Load before working here

1. `../docs/specs/ui.md` — product spec for both tabs
2. `../docs/contracts/api.openapi.yaml` — the API surface
3. `../docs/contracts/eval-trace.schema.json` — the Eval tab's entire data model
4. `../docs/specs/schema.md` (for rendering node/edge attributes)
5. `../docs/reference/guidelines/statins.md` (what the user is looking at)
6. `../docs/decisions/0004-nextjs-cytoscape-review-tool.md`
7. `../docs/decisions/0005-internal-rest-api.md`
8. `../docs/decisions/0014-v0-scope-and-structure.md`

## Scope

- Explore tab: search, result list, canvas, detail panel, URL-encoded state (shareable deep links).
- Eval tab: fixture picker, Run button, event stepper (list + keyboard nav), current-step highlighting on canvas, event detail panel, recommendations strip.
- Shared `GraphCanvas` component: same layout, styling, interaction model in both tabs.

## Not in scope (v0)

- Editing the graph. Read-only.
- Flag / proposed-edit / curator-queue workflow (deferred from the old review-tool design; see archived `docs/archive/review-workflow.md`).
- Auth, multi-tenant, mobile.

## Build conventions

- No direct Cypher. Everything goes through `/api`.
- API types come from codegen. If the type doesn't exist, the OpenAPI spec is wrong — fix the contract first.
- Provenance is visible without navigation. A reviewer should never have to ask "where did this edge come from."
- Predicate expressions render as English; the UI does not re-implement DSL semantics.
- No system-level design system yet; Tailwind + shadcn components.

## Definition of done

Explore tab:

1. Renders the seed graph from `/api` without errors.
2. Search finds any node by id or label.
3. Clicking a node expands neighbors with correct edge labels and provenance visible.
4. Deep links (URL state) restore pinned node + expansion.

Eval tab:

1. Fixture picker lists every directory under `evals/fixtures/statins/`.
2. Running a fixture renders the full `EvalTrace` event list within one step of the API returning.
3. j/k keyboard nav steps through events; current event highlights associated node(s) on the canvas.
4. Derived recommendations strip matches the expected-outcome.json for every seed fixture.
