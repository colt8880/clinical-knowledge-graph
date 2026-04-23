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
#   4. cholesterol.cypher      — ACC/AHA 2018 subgraph
#   5. kdigo-ckd.cypher        — KDIGO 2024 CKD subgraph
#   6. ada-diabetes.cypher     — ADA 2024 Diabetes subgraph
#   7. cross-edges-uspstf-accaha.cypher — PREEMPTED_BY edges (F25)
#   8. cross-edges-kdigo.cypher — MODIFIES edges (F26)
#   9. cross-edges-ada.cypher — MODIFIES edges (F53)
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

echo "==> Applying cholesterol seed..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/cholesterol.cypher

echo "==> Applying KDIGO CKD seed..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/kdigo-ckd.cypher

echo "==> Applying ADA Diabetes seed..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/ada-diabetes.cypher

echo "==> Applying cross-edges USPSTF ↔ ACC/AHA..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/cross-edges-uspstf-accaha.cypher

echo "==> Applying cross-edges KDIGO → USPSTF/ACC-AHA..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/cross-edges-kdigo.cypher

echo "==> Applying cross-edges KDIGO → ADA..."
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" < /graph/seeds/cross-edges-ada.cypher

echo "==> Verifying node count..."
NODE_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (n) RETURN count(n) AS c" | tail -1 | tr -d '[:space:]')

# 50 (previous) + 10 ADA entities + 14 ADA guideline-scoped = 74
echo "    Node count: $NODE_COUNT (expected 74)"
if [ "$NODE_COUNT" -ne 74 ]; then
  echo "ERROR: Expected 74 nodes, got $NODE_COUNT"
  exit 1
fi

echo "==> Verifying edge count..."
EDGE_COUNT=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH ()-[r]->() RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

# 70 (previous) + 42 ADA edges + 2 ADA cross-edges (MODIFIES) = 114
echo "    Edge count: $EDGE_COUNT (expected 114)"
if [ "$EDGE_COUNT" -ne 114 ]; then
  echo "ERROR: Expected 114 edges, got $EDGE_COUNT"
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

echo "==> Verifying domain labels..."
UNLABELED_RECS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (r:Recommendation) WHERE NOT r:USPSTF AND NOT r:ACC_AHA AND NOT r:KDIGO AND NOT r:ADA RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    Unlabeled Recommendations: $UNLABELED_RECS (expected 0)"
if [ "$UNLABELED_RECS" -ne 0 ]; then
  echo "ERROR: Found $UNLABELED_RECS Recommendation nodes without a domain label"
  exit 1
fi

echo "==> Verifying ACC/AHA Recommendation count..."
ACCAHA_RECS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (r:Recommendation:ACC_AHA) RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    ACC/AHA Recommendations: $ACCAHA_RECS (expected 4)"
if [ "$ACCAHA_RECS" -ne 4 ]; then
  echo "ERROR: Expected 4 ACC/AHA Recommendation nodes, got $ACCAHA_RECS"
  exit 1
fi

echo "==> Verifying ACC/AHA Guideline node..."
ACCAHA_GUIDELINE=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (g:Guideline {id: 'guideline:acc-aha-cholesterol-2018'}) RETURN count(g) AS c" | tail -1 | tr -d '[:space:]')

echo "    ACC/AHA Guideline: $ACCAHA_GUIDELINE (expected 1)"
if [ "$ACCAHA_GUIDELINE" -ne 1 ]; then
  echo "ERROR: Expected 1 ACC/AHA Guideline node, got $ACCAHA_GUIDELINE"
  exit 1
fi

echo "==> Verifying KDIGO Recommendation count..."
KDIGO_RECS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (r:Recommendation:KDIGO) RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    KDIGO Recommendations: $KDIGO_RECS (expected 4)"
if [ "$KDIGO_RECS" -ne 4 ]; then
  echo "ERROR: Expected 4 KDIGO Recommendation nodes, got $KDIGO_RECS"
  exit 1
fi

echo "==> Verifying KDIGO Guideline node..."
KDIGO_GUIDELINE=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (g:Guideline {id: 'guideline:kdigo-ckd-2024'}) RETURN count(g) AS c" | tail -1 | tr -d '[:space:]')

echo "    KDIGO Guideline: $KDIGO_GUIDELINE (expected 1)"
if [ "$KDIGO_GUIDELINE" -ne 1 ]; then
  echo "ERROR: Expected 1 KDIGO Guideline node, got $KDIGO_GUIDELINE"
  exit 1
fi

echo "==> Verifying ADA Recommendation count..."
ADA_RECS=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (r:Recommendation:ADA) RETURN count(r) AS c" | tail -1 | tr -d '[:space:]')

echo "    ADA Recommendations: $ADA_RECS (expected 5)"
if [ "$ADA_RECS" -ne 5 ]; then
  echo "ERROR: Expected 5 ADA Recommendation nodes, got $ADA_RECS"
  exit 1
fi

echo "==> Verifying ADA Guideline node..."
ADA_GUIDELINE=$(cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  --format plain "MATCH (g:Guideline {id: 'guideline:ada-diabetes-2024'}) RETURN count(g) AS c" | tail -1 | tr -d '[:space:]')

echo "    ADA Guideline: $ADA_GUIDELINE (expected 1)"
if [ "$ADA_GUIDELINE" -ne 1 ]; then
  echo "ERROR: Expected 1 ADA Guideline node, got $ADA_GUIDELINE"
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

echo "==> Seed complete. 74 nodes, 114 edges. All checks passed."
