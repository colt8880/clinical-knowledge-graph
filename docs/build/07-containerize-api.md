# 07: Containerize /api

**Status**: pending
**Depends on**: 04
**Branch**: `feat/api-dockerfile`

## Context

Package the FastAPI app as a container so it can be run alongside Neo4j via compose. Keep the image small and the build reproducible.

## Required reading

- `api/CLAUDE.md`
- `api/README.md` (local-run instructions — containerize should match the contract)

## Scope

- `api/Dockerfile` — multi-stage (builder → slim runtime).
- `api/.dockerignore`
- `api/docker-entrypoint.sh` — optional; wait-for-Neo4j loop if needed.
- `api/README.md` — section: "Running in Docker".

## Constraints

- Base image: `python:3.12-slim`.
- Non-root user in the final image.
- Image size under ~250MB.
- No secrets baked in; everything via env vars (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).
- Healthcheck wired to `GET /healthz`.

## Verification targets

- `docker build -t ckg-api api/` — exits 0.
- `docker run --rm -e NEO4J_URI=bolt://host.docker.internal:7687 -e NEO4J_USER=neo4j -e NEO4J_PASSWORD=password123 -p 8000:8000 ckg-api` — starts, `curl http://localhost:8000/healthz` returns `{"status":"ok","neo4j":"ok"}`.
- Container runs as non-root (`docker exec ... id` shows non-zero uid).
- Image size: `docker images ckg-api --format '{{.Size}}'` under 250MB.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Multi-arch builds.
- Image publishing to a registry.
- CI/CD image build pipeline.
- `docker-compose.yml` — feature 09.
