#!/bin/bash
# seed.sh — Wait for Neo4j, apply constraints + seeds, verify counts.
#
# Runs as a one-shot container inside docker compose. Exits 0 on success.
# Idempotent: all seeds use MERGE throughout, so re-running is a no-op.
#
# Load order (per ADR 0017 / F20):
#   1. constraints.cypher     — uniqueness constraints (idempotent)
#   2. clinical-entities.cypher — canonical shared entity registry (MERGE by id)
#   3. statins.cypher          — guideline-scoped nodes + edges (MERGE entities, CREATE Rec/Strategy)
#
# Expected environment:
#   NEO4J_URI       bolt://neo4j:7687
#   NEO4J_USER      neo4j
#   NEO4J_PASSWORD  password123

set -euo pipefail

echo "==> Applying constraints..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/constraints.cypher

echo "==> Applying shared clinical entities..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/clinical-entities.cypher

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

echo "==> Verifying Condition codings uniqueness..."
DUP_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (a:Condition), (b:Condition) WHERE a <> b AND ANY(c IN a.codings WHERE c IN b.codings) RETURN count(*) AS c" | tail -1 | tr -d '[:space:]')

echo "    Duplicate coding pairs: $DUP_COUNT (expected 0)"
if [ "$DUP_COUNT" -ne 0 ]; then
  echo "ERROR: Found $DUP_COUNT duplicate coding pairs across Condition nodes"
  exit 1
fi

echo "==> Verifying USPSTF domain labels..."
UNLABELED_RECS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (r:Recommendation) WHERE NOT r:USPSTF RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    Unlabeled Recommendations: $UNLABELED_RECS (expected 0)"
if [ "$UNLABELED_RECS" -ne 0 ]; then
  echo "ERROR: Found $UNLABELED_RECS Recommendation nodes without :USPSTF label"
  exit 1
fi

echo "==> Verifying no orphan medications..."
ORPHAN_MEDS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (m:Medication) WHERE NOT (m)<-[:INCLUDES_ACTION|TARGETS]-() RETURN count(m) AS c" | tail -1 | tr -d '[:space:]')

echo "    Orphan medications: $ORPHAN_MEDS (expected 0)"
if [ "$ORPHAN_MEDS" -ne 0 ]; then
  echo "ERROR: Found $ORPHAN_MEDS orphan Medication nodes with no guideline reference"
  exit 1
fi

echo "==> Seed complete. 23 nodes, 14 edges. All checks passed."
