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

# Wait for it to be ready (uses the neo4j Python driver, not cypher-shell)
pip install -e "api[dev]"
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))
d.verify_connectivity(); d.close(); print('Ready')
"

# Load seed via Python driver
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))
for f in ['graph/constraints.cypher', 'graph/seed.cypher']:
    stmts = [s.strip() for s in open(f).read().split(';') if s.strip() and not all(
        l.strip().startswith('//') or l.strip() == '' for l in s.strip().splitlines())]
    with driver.session() as session:
        for s in stmts: session.run(s)
    print(f'Loaded {f}')
driver.close()
"

# Run tests
cd api && pytest tests/ -v

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

Loads `graph/constraints.cypher` and `graph/seed.cypher` into a fresh Neo4j 5 Community container using the Python `neo4j` driver, then asserts the expected node and edge counts (currently 23 nodes, 14 edges from the statin model) via exact integer comparison. Prints a detailed per-label breakdown on failure.

**Reproduce locally:**

```sh
# Start Neo4j (same as api-tests above), then load seed (see api-tests repro)
# Check counts via Python
pip install neo4j
python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))
with d.session() as s:
    print('Nodes:', s.run('MATCH (n) RETURN count(n) AS c').single()['c'])  # expect 23
    print('Edges:', s.run('MATCH ()-[r]->() RETURN count(r) AS c').single()['c'])  # expect 14
d.close()
"

docker rm -f neo4j-test
```

## Adding a new job

1. Add the job to `ci.yml` under the `jobs:` key.
2. If the job needs Neo4j, copy the `services:` block from `api-tests` or `graph-smoke`.
3. Pin all action versions (`actions/checkout@v4`, `actions/setup-python@v5`).
4. Add a "Reproduce locally" section to this README.
5. Ask the repo owner to add the job name as a required status check on `main` branch protection.
