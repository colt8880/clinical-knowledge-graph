# /ui — Clinical Knowledge Graph

Next.js 14 (App Router) app for browsing and evaluating the clinical knowledge graph.

## Tabs

- **Explore** (`/explore`) — manual graph traversal. Click nodes to expand their neighborhoods, inspect provenance and properties. Default entry point: the USPSTF 2022 statin guideline.
- **Eval** (`/eval`) — trace stepper (feature 06, not yet implemented).

## Stack

- Next.js 14 (App Router), TypeScript strict
- Cytoscape.js with cose-bilkent layout (seeded for determinism)
- TanStack React Query for data fetching
- Tailwind CSS
- OpenAPI-generated types from `docs/contracts/api.openapi.yaml`

## Prerequisites

- Node.js 20+
- API running at `http://localhost:8000` (see `/api`)
- Neo4j with the statin seed loaded

## Development

```sh
npm install
npm run dev          # http://localhost:3000
npm run build        # production build
npm run test         # Playwright e2e tests (requires API + Neo4j)
npm run generate-api # regenerate TS types from OpenAPI spec
```

## URL state

The Explore tab encodes state in the URL for shareable deep links:

```
/explore?pinned=<node-id>&expanded=<id1>,<id2>
```

- `pinned` — center node whose neighbors are rendered (default: `guideline:uspstf-statin-2022`)
- `expanded` — additional nodes whose neighbors are also loaded (comma-separated)

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL |
