# 09: docker-compose for full stack

**Status**: pending
**Depends on**: 07, 08
**Branch**: `feat/compose`

## Context

Single `docker-compose up` brings up Neo4j + API + UI wired together. This is the shipping artifact for v0: anyone can clone the repo, run one command, hit `http://localhost:3000`, and see the Eval tab work end to end.

## Required reading

- `graph/README.md` — seeding instructions.
- `api/README.md`
- `ui/README.md`
- `docs/workflow.md` — how developers currently run things locally.

## Scope

- `docker-compose.yml` at repo root — three services: `neo4j`, `api`, `ui`.
- `scripts/seed.sh` — wait for Neo4j, apply `graph/constraints.cypher` + `graph/seeds/statins.cypher`, assert node/edge counts, exit 0 on success.
- Update root `README.md` with "Quickstart: `docker compose up`".
- Update `docs/workflow.md` if the developer loop changes.

## Constraints

- Services start in dependency order via healthchecks (API waits for Neo4j `healthy`; UI waits for API `healthy`).
- Neo4j password stays `password123` for dev only; documented as such.
- Named volume for Neo4j data (`ckg-neo4j-data`); data survives `docker compose down` but not `down -v`.
- Seeding runs once on first start (idempotent: re-running is a no-op or re-applies cleanly).
- All three images build from local Dockerfiles; no pulled pre-built images beyond the Neo4j base.

## Verification targets

- `docker compose up --build` — all three services reach `healthy` state.
- `docker compose exec neo4j cypher-shell -u neo4j -p password123 "MATCH (n) RETURN count(n)"` — returns the expected v0 node count (1 + 3 + 2 + 7 + 5 + 4 + 1 = 23).
- `curl http://localhost:8000/healthz` → `{"status":"ok","neo4j":"ok"}`.
- `http://localhost:3000` loads, Explore tab shows the graph, Eval tab runs fixture 01 and produces the Grade B recommendation.
- `docker compose down && docker compose up` — comes back up cleanly; data persists.
- `docker compose down -v && docker compose up` — comes back up cleanly with fresh seed.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` backlog row updated.
- Root `README.md` has a working Quickstart.
- PR opened with Scope / Manual Test Steps / Manual Test Output (include the output of `docker compose ps` showing all healthy).
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Production compose (TLS, secrets management, resource limits).
- CI/CD integration.
- Multi-environment configs (dev/staging/prod overlays).
- Kubernetes / Helm.
