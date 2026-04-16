# /ui — Clinical Knowledge Graph

Next.js 14 (App Router) app for browsing and evaluating the clinical knowledge graph.

## Tabs

- **Explore** (`/explore`) — manual graph traversal. Click nodes to expand their neighborhoods, inspect provenance and properties. Default entry point: the USPSTF 2022 statin guideline.
- **Eval** (`/eval`) — trace stepper (feature 06, not yet implemented).

## Stack

- Next.js 14 (App Router), TypeScript strict
- Cytoscape.js with column-based preset layout
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

The Explore tab encodes the selection path in the URL for shareable deep links:

```
/explore?g=<guideline-id>&r=<recommendation-id>&s=<strategy-id>
```

- `g` — selected guideline (default: `guideline:uspstf-statin-2022`)
- `r` — selected recommendation (shows Strategies column when set)
- `s` — selected strategy (shows Actions column when set)

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL |
