#!/bin/bash
# seed.sh — Wait for Neo4j, apply constraints + statin seed, verify counts.
#
# Runs as a one-shot container inside docker compose. Exits 0 on success.
# Idempotent: the seed uses MERGE throughout, so re-running is a no-op.
#
# Expected environment:
#   NEO4J_URI       bolt://neo4j:7687
#   NEO4J_USER      neo4j
#   NEO4J_PASSWORD  password123

set -euo pipefail

echo "==> Applying constraints..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/constraints.cypher

echo "==> Applying statin seed..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/statins.cypher

echo "==> Verifying node count..."
NODE_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (n) RETURN count(n) AS c" | tail -1 | tr -d '[:space:]')

echo "    Node count: $NODE_COUNT (expected 23)"
if [ "$NODE_COUNT" -ne 23 ]; then
  echo "ERROR: Expected 23 nodes, got $NODE_COUNT"
  exit 1
fi

echo "==> Verifying edge count..."
EDGE_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH ()-[r]->() RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    Edge count: $EDGE_COUNT (expected 14)"
if [ "$EDGE_COUNT" -ne 14 ]; then
  echo "ERROR: Expected 14 edges, got $EDGE_COUNT"
  exit 1
fi

echo "==> Seed complete. 23 nodes, 14 edges."
