# 11: CI skeleton (GitHub Actions)

**Status**: shipped
**Depends on**: 02
**Branch**: `chore/ci-skeleton`

## Context

CLAUDE.md says "CI is deliberately not wired yet. Add it in a separate PR after the first feature merges cleanly under this workflow." Feature 02 is that first feature. This spec wires up a minimal GitHub Actions workflow that runs the `/api` test suite against a real Neo4j service container and lints the contract files. The goal is a mechanical backstop for the drift that PR review caught manually on 02 (port mismatch, route shape disagreement, edge-type typo). CI is only useful if it blocks merge, so branch protection on `main` is part of this feature. Out of scope: `/ui` build, evaluator fixtures, contract-alignment tests (those live in feature 10).

## Required reading

- `CLAUDE.md` — "Build workflow" section; confirms CI is expected now.
- `docs/workflow.md` — current manual flow; CI complements, does not replace.
- `api/CLAUDE.md` — how `/api` tests are structured and how they expect Neo4j to be reachable.
- `api/pyproject.toml` — Python version and test runner. CI must match.
- `docs/contracts/api.openapi.yaml`, `docs/contracts/*.schema.json`, `docs/contracts/predicate-catalog.yaml` — files the contract-lint job validates.
- `graph/seed.cypher` — the seed the api-tests job loads before running pytest.
- `.claude/agents/pr-reviewer.md` — so the CI job list is consistent with what the reviewer already checks.

## Scope

- `.github/workflows/ci.yml` — single workflow, three jobs (see below).
- `.github/workflows/README.md` — one-page doc: what each job does, how to reproduce failures locally, how to add a new job.
- `docs/workflow.md` — add a short "CI" section pointing at the workflow file and listing required checks.
- `docs/reference/build-status.md` — add a row for `CI` moving from `—` to `implemented`.
- `docs/build/README.md` — flip feature 11 to `shipped` in the same PR.

No changes to `/api`, `/graph`, `/ui`, or `docs/contracts/` in this PR. If a job fails because the repo is actually broken, stop and surface it rather than patching around it.

### Jobs in `ci.yml`

1. **`api-tests`**
   - Trigger: `pull_request` and `push` to `main`.
   - Runs on `ubuntu-latest`.
   - `services: neo4j` — use the official `neo4j:5-community` image, expose 7687, set `NEO4J_AUTH=neo4j/password123` to match dev defaults.
   - Steps: checkout → set up Python (match `api/pyproject.toml`) → install deps → wait for Neo4j to be healthy → load `graph/seed.cypher` via `cypher-shell` → `pytest api/`.
   - Env vars for pytest: `NEO4J_URI=bolt://localhost:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=password123`.

2. **`contract-lint`**
   - Trigger: same.
   - Steps: checkout → set up Python → install a JSON Schema validator and an OpenAPI linter (`jsonschema` and `openapi-spec-validator` are fine; keep it in a small `requirements-ci.txt` or inline `pip install`).
   - Validate:
     - `docs/contracts/api.openapi.yaml` parses as a valid OpenAPI 3 document.
     - Every `*.schema.json` in `docs/contracts/` parses as valid JSON Schema.
     - `docs/contracts/predicate-catalog.yaml` parses as YAML and validates against `docs/contracts/predicate-catalog.schema.json`.

3. **`graph-smoke`**
   - Trigger: same.
   - `services: neo4j` as above.
   - Steps: checkout → wait for Neo4j → load `graph/seed.cypher` → run a Cypher query that asserts expected node and edge counts (pick counts from the current seed; hardcode them, update in the same PR if the seed changes).
   - Exits 0 on match, non-zero on mismatch, with the diff in the job output.

Keep all three jobs in one workflow file. Don't split into multiple workflows for v0.

### Branch protection

The PR body must include explicit instructions for the human to enable branch protection on `main` after merge (this cannot be done from CI): require `api-tests`, `contract-lint`, and `graph-smoke` as status checks, require PR review, disallow direct pushes. CI that doesn't block merge is decoration.

## Constraints

- Pin action versions (`actions/checkout@v4`, `actions/setup-python@vX`) — no floating `@main` refs.
- Match the Python version from `api/pyproject.toml` exactly. Don't introduce a new version.
- Use the same Neo4j major version the app targets (5.x community). Don't silently upgrade.
- Don't cache aggressively in v0. A slow but correct CI beats a fast flaky one. Add caching in a later PR if wall-time becomes a problem.
- Don't add `/ui` jobs. Feature 05 hasn't shipped; adding a job for a non-existent build is noise.
- Don't run the evaluator fixtures. Feature 04 hasn't shipped and fixtures 01/02/04/05 aren't wired.
- Don't invoke the `pr-reviewer` subagent from CI. It's a local pre-merge step per `docs/workflow.md`.
- All jobs must be deterministic and idempotent. Flaky CI is worse than no CI.

## Verification targets

- `act -j api-tests` (or equivalent local GitHub Actions runner) completes green against the current `main`. If `act` isn't available, document the exact `docker run` invocation that reproduces each job and show it working.
- Pushing the branch triggers all three jobs and all three pass. Paste the Actions run URL into the PR body.
- Introducing an obvious bug locally (e.g., bump the port in `api.openapi.yaml` to `8081`) does NOT fail CI in this PR (that's feature 10's job). Note this explicitly in the PR body so the human knows what CI does and doesn't catch yet.
- `docs/workflow.md` and `docs/reference/build-status.md` reflect the new CI surface.

## Definition of done

- `.github/workflows/ci.yml` exists and all three jobs pass on the PR.
- `.github/workflows/README.md` exists and explains each job in plain prose.
- `docs/workflow.md` has a "CI" section.
- `docs/reference/build-status.md` has a `CI` row marked `implemented`.
- `docs/build/README.md` shows feature 11 as `shipped`.
- PR body includes: Scope, Manual Test Steps, Manual Test Output (Actions run URL), and an explicit call-out to the human to enable branch protection on `main` with the three jobs as required checks.
- `pr-reviewer` subagent run; blocking feedback addressed; output posted as a PR comment.

## Out of scope

- Contract-alignment tests (OpenAPI-vs-routes, schema-vs-seed). That's feature 10.
- `/ui` build and lint jobs. Add when feature 05 ships.
- Evaluator fixture runs in CI. Add when feature 04 ships.
- Coverage reports, badges, release automation, deploy workflows.
- Caching, matrix builds, self-hosted runners.
- Migrating the `pr-reviewer` subagent into CI. It stays local.
- Any edits to `/api`, `/graph`, `/ui`, or `docs/contracts/`. This PR is CI-only.
