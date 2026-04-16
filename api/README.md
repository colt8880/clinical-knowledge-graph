# /api — Clinical Knowledge Graph API

FastAPI service exposing read-only graph query endpoints over the v0 statin knowledge graph in Neo4j.

## Prerequisites

- Python 3.12+
- Neo4j 5 Community running locally (the `ckg-neo4j` Docker container)
- Graph seeded via `graph/seeds/statins.cypher`

## Setup

```sh
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Environment variables (with defaults):

| Variable | Default | Description |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt endpoint |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `password123` | Neo4j password |

## Running

```sh
uvicorn app.main:app --reload
```

The API starts on `http://localhost:8000`. Interactive docs at `/docs`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness probe (app + Neo4j connectivity) |
| GET | `/version` | Version stamps (spec_tag, graph_version, evaluator_version) |
| GET | `/nodes/{id}` | Fetch a single node by stable id |
| GET | `/nodes/{id}/neighbors` | Fetch a node with one-hop inbound/outbound neighbors |

## Running in Docker

Build the image:

```sh
docker build -t ckg-api api/
```

Run (assumes Neo4j is reachable from the container):

```sh
docker run --rm \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=password123 \
  -p 8000:8000 \
  ckg-api
```

The entrypoint waits up to 30 seconds for Neo4j to become reachable before starting the app. All configuration is via environment variables — no secrets are baked into the image.

Verify:

```sh
curl http://localhost:8000/healthz
```

## Tests

```sh
cd api
source .venv/bin/activate
python -m pytest -v
```

Requires `ckg-neo4j` running with the seed loaded. Integration tests hit the live graph.
