# 02: API skeleton

**Status**: pending
**Depends on**: 01
**Branch**: `feat/api-skeleton`

## Context

Stand up the FastAPI app with just enough surface area to prove the stack works end-to-end: health check, version endpoint, and a single read-only traversal primitive (`/nodes/{id}`). No evaluator yet. This unblocks both the UI (it can render from real API responses) and the evaluator feature (which will plug into the same app).

## Required reading

- `api/CLAUDE.md` — scope and DoD for `/api`.
- `docs/contracts/api.openapi.yaml` — the source of truth for endpoint shape. Match it exactly for the endpoints in scope.
- `docs/specs/api-primitives.md` — traversal primitives; `/nodes/{id}` is the minimum.
- `docs/reference/statin-model.md` — node ids the endpoint must resolve.

## Scope

- `api/pyproject.toml` — Python 3.12, FastAPI, Pydantic v2, neo4j driver, pytest.
- `api/app/main.py` — FastAPI app, CORS, startup/shutdown for Neo4j driver.
- `api/app/config.py` — settings from env vars (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`).
- `api/app/routes/health.py` — `GET /healthz` (app up + Neo4j reachable), `GET /version`.
- `api/app/routes/nodes.py` — `GET /nodes/{id}` returns node properties + one-hop neighbors.
- `api/app/db.py` — Neo4j driver wrapper, single read transaction helper.
- `api/tests/test_health.py` — unit + integration.
- `api/tests/test_nodes.py` — integration against seeded graph, asserts known ids resolve.
- `api/README.md` — how to run locally against `ckg-neo4j`.

## Constraints

- Python 3.12+, Pydantic v2, FastAPI.
- Neo4j driver only; no ORM. Cypher strings live in `app/db.py` or per-route modules.
- All endpoints return JSON matching `api.openapi.yaml`. If the contract is wrong, fix the contract on this branch and note it in the PR body.
- No evaluator imports. This feature is read-only traversal.
- Deterministic ordering on list fields (neighbors sorted by id).

## Verification targets

- `cd api && uv run pytest` (or `pytest`) — exits 0.
- `curl http://localhost:8000/healthz` returns `{"status":"ok","neo4j":"ok"}` with the seeded graph up.
- `curl http://localhost:8000/nodes/guideline:uspstf-statin-2022` returns the Guideline node with `CONTAINS` neighbors (3 Recommendations).
- OpenAPI contract matches implementation: `python -m app.tools.check_openapi` (or equivalent) exits 0. If no such tool exists, add a pytest that diffs the generated FastAPI schema against the committed contract.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- `docs/reference/build-status.md` row for `FastAPI skeleton` moves `spec-only` → `scaffolded` or `implemented` (whichever is accurate).
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Evaluator endpoints (`/evaluate`, trace streaming) — that's 03/04.
- Auth, rate limiting, multi-tenancy.
- Any Cypher write operations.
- Dockerfile (that's 07).
