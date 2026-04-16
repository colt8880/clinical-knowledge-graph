# 05: UI Explore tab

**Status**: pending
**Depends on**: 02
**Branch**: `feat/ui-explore`

## Context

Stand up the Next.js app with the Explore tab: manual graph traversal backed by the live `/nodes/{id}` and `/nodes/{id}/neighbors` endpoints. This replaces the static `diagrams/crc-graph.html` demo with something that reflects the real Neo4j state. Eval tab (feature 06) will reuse the GraphCanvas component built here.

## Required reading

- `ui/CLAUDE.md`
- `docs/specs/ui.md` — Explore + Eval tab product spec.
- `docs/contracts/api.openapi.yaml` — source for the generated TS client.
- `diagrams/crc-graph.html` — visual reference for interaction model (pin, expand neighbors, provenance panel).

## Scope

- `ui/package.json` — Next.js 14 App Router, TypeScript, Cytoscape.js, cose-bilkent layout.
- `ui/app/layout.tsx`, `ui/app/page.tsx` — tab shell (Explore | Eval).
- `ui/app/explore/page.tsx` — Explore tab.
- `ui/components/GraphCanvas.tsx` — Cytoscape wrapper, seeded cose-bilkent layout (per `docs/ISSUES.md`).
- `ui/components/NodeDetail.tsx` — right-side panel showing node properties + provenance.
- `ui/lib/api/` — generated TS client from OpenAPI (commit the generated output).
- `ui/scripts/generate-api.ts` — codegen script (`openapi-typescript` or similar).
- `ui/tests/explore.spec.ts` — Playwright test: load page, click Guideline node, see 3 Recommendation neighbors render.
- `ui/README.md`.

## Constraints

- Next.js 14 App Router, TypeScript strict mode.
- Cytoscape.js with cose-bilkent layout, seeded (fixed random seed) so layouts don't jitter between renders.
- URL state for pinned / expanded nodes: `?pinned=<id>&expanded=<id1>,<id2>` (per `docs/ISSUES.md`).
- No API calls outside the generated client.
- No direct Neo4j access; everything goes through `/api`.

## Verification targets

- `cd ui && npm run build` — exits 0.
- `cd ui && npm run test` (Playwright) — all tests pass.
- Manual: load `http://localhost:3000`, Explore tab; click `guideline:uspstf-statin-2022`; the 3 Recommendation nodes expand; clicking one shows its structured eligibility in the detail panel.
- Deep link with `?pinned=...&expanded=...` restores the same visual state.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output (include a screenshot).
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Eval tab — feature 06.
- Auth, user accounts.
- Search / fuzzy node finder (can come later; not required for demo).
- Dockerfile — feature 08.
