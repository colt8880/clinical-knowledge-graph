# CI workflows

All CI lives in `.github/workflows/ci.yml`. Three jobs run on every push to `main` and every pull request.

## Jobs

### `api-tests`

Runs the `/api` pytest suite against a real Neo4j 5 Community service container. Loads `graph/constraints.cypher` and `graph/seed.cypher` before running tests.

**Reproduce locally:**

```sh
# Start Neo4j (must be running before tests)
docker run -d --name neo4j-test \
  -e NEO4J_AUTH=neo4j/password123 \
  -p 7687:7687 -p 7474:7474 \
  neo4j:5-community

# Wait for it to be ready
until docker exec neo4j-test cypher-shell -u neo4j -p password123 "RETURN 1" 2>/dev/null; do sleep 2; done

# Load seed
docker exec -i neo4j-test cypher-shell -u neo4j -p password123 < graph/constraints.cypher
docker exec -i neo4j-test cypher-shell -u neo4j -p password123 < graph/seed.cypher

# Run tests
cd api && pip install -e ".[dev]" && pytest tests/ -v

# Cleanup
docker rm -f neo4j-test
```

### `contract-lint`

Validates contract files parse correctly and conform to their schemas:

- `docs/contracts/api.openapi.yaml` — valid OpenAPI 3.x document.
- `docs/contracts/*.schema.json` — each is a valid JSON Schema.
- `docs/contracts/predicate-catalog.yaml` — valid YAML that validates against `predicate-catalog.schema.json`.

**Reproduce locally:**

```sh
pip install jsonschema pyyaml openapi-spec-validator

# OpenAPI
python -c "
import yaml
from openapi_spec_validator import validate
with open('docs/contracts/api.openapi.yaml') as f:
    validate(yaml.safe_load(f))
print('OK')
"

# JSON Schemas
python -c "
import json, glob
from jsonschema import Draft7Validator
for p in sorted(glob.glob('docs/contracts/*.schema.json')):
    Draft7Validator.check_schema(json.load(open(p)))
    print(f'OK: {p}')
"

# Predicate catalog
python -c "
import json, yaml
from jsonschema import validate
validate(yaml.safe_load(open('docs/contracts/predicate-catalog.yaml')), json.load(open('docs/contracts/predicate-catalog.schema.json')))
print('OK')
"
```

### `graph-smoke`

Loads `graph/constraints.cypher` and `graph/seed.cypher` into a fresh Neo4j 5 Community container, then asserts the expected node and edge counts (currently 23 nodes, 14 edges from the statin model). Prints a detailed per-label breakdown on failure.

**Reproduce locally:**

```sh
# Start Neo4j (same as api-tests above)
docker run -d --name neo4j-test \
  -e NEO4J_AUTH=neo4j/password123 \
  -p 7687:7687 -p 7474:7474 \
  neo4j:5-community

until docker exec neo4j-test cypher-shell -u neo4j -p password123 "RETURN 1" 2>/dev/null; do sleep 2; done

docker exec -i neo4j-test cypher-shell -u neo4j -p password123 < graph/constraints.cypher
docker exec -i neo4j-test cypher-shell -u neo4j -p password123 < graph/seed.cypher

# Check counts
docker exec neo4j-test cypher-shell -u neo4j -p password123 --format plain \
  "MATCH (n) RETURN count(n)"  # expect 23

docker exec neo4j-test cypher-shell -u neo4j -p password123 --format plain \
  "MATCH ()-[r]->() RETURN count(r)"  # expect 14

docker rm -f neo4j-test
```

## Adding a new job

1. Add the job to `ci.yml` under the `jobs:` key.
2. If the job needs Neo4j, copy the `services:` block from `api-tests` or `graph-smoke`.
3. Pin all action versions (`actions/checkout@v4`, `actions/setup-python@v5`).
4. Add a "Reproduce locally" section to this README.
5. Ask the repo owner to add the job name as a required status check on `main` branch protection.
