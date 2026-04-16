# Clinical Knowledge Graph

A deterministic reasoning substrate for an agentic EHR/LLM system. The graph encodes published clinical guidelines as structured nodes and edges; an evaluator traverses it against a `PatientContext` and emits an auditable `EvalTrace`.

**v0 scope:** USPSTF 2022 statin primary prevention (Grade B / C / I).

## Quickstart

```sh
docker compose up --build
```

This brings up three services:

| Service | URL | Description |
|---|---|---|
| **UI** | http://localhost:3000 | Explore tab (graph traversal) + Eval tab (trace stepper) |
| **API** | http://localhost:8000 | FastAPI evaluator + graph query endpoints |
| **Neo4j** | http://localhost:7474 | Browser (neo4j / password123) |

A one-shot `seed` container automatically loads the graph schema and statin model into Neo4j on first start.

### Verify

```sh
# All services healthy
docker compose ps

# Neo4j has the expected 23 nodes
docker compose exec neo4j cypher-shell -u neo4j -p password123 "MATCH (n) RETURN count(n)"

# API is up
curl http://localhost:8000/healthz
```

### Teardown

```sh
# Stop services (data persists in the ckg-neo4j-data volume)
docker compose down

# Stop and wipe data (fresh seed on next up)
docker compose down -v
```

## Development

See component READMEs for local (non-Docker) setup:

- [`/api`](api/README.md) — Python/FastAPI evaluator
- [`/ui`](ui/README.md) — Next.js app
- [`/graph`](graph/README.md) — Neo4j schema + seed

## Architecture

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│   UI    │────▶│   API   │────▶│  Neo4j  │
│ :3000   │     │ :8000   │     │ :7687   │
└─────────┘     └─────────┘     └─────────┘
```

The UI talks to the API; the API talks to Neo4j. Zero PHI in this repo — synthetic fixtures only.

## Documentation

- [Build specs](docs/build/) — feature specs and backlog
- [Design decisions](docs/decisions/) — ADRs (append-only)
- [Specs](docs/specs/) — rationale and semantics
- [Contracts](docs/contracts/) — machine-readable schemas (OpenAPI, JSON Schema)
