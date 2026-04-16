# 08: Containerize /ui

**Status**: pending
**Depends on**: 06
**Branch**: `feat/ui-dockerfile`

## Context

Package the Next.js app as a container. Use Next's standalone output to keep the runtime image tight.

## Required reading

- `ui/CLAUDE.md`
- `ui/README.md`

## Scope

- `ui/Dockerfile` — multi-stage (deps → builder → runner) using Next's `output: "standalone"`.
- `ui/.dockerignore`
- `ui/next.config.js` — set `output: "standalone"` if not already.
- `ui/README.md` — section: "Running in Docker".

## Constraints

- Base image: `node:20-alpine` (or `node:20-slim` if alpine causes issues with Cytoscape deps).
- Non-root user in the final image.
- Image size under ~300MB.
- `API_BASE_URL` configurable via env var at runtime, not bake time.
- Healthcheck wired to a simple `/` GET.

## Verification targets

- `docker build -t ckg-ui ui/` — exits 0.
- `docker run --rm -e API_BASE_URL=http://host.docker.internal:8000 -p 3000:3000 ckg-ui` — starts, browser loads `http://localhost:3000`, Explore tab renders against live API.
- Container runs as non-root.
- Image size under 300MB.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- SSR-specific optimizations beyond standalone output.
- CDN / asset hosting strategy.
- Multi-arch builds.
- Compose wiring — feature 09.
