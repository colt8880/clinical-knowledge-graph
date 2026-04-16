// Uniqueness constraints for the v0 statin knowledge graph.
//
// One constraint per node label on `id`. Idempotent: CREATE CONSTRAINT
// IF NOT EXISTS is a no-op once the constraint exists, so this file can be
// applied against a fresh or a populated database safely.
//
// Schema source of truth: docs/specs/schema.md and docs/reference/schema-reference.md.
// Apply before seeds/statins.cypher — MERGE in the seed relies on these uniqueness
// guarantees to be truly idempotent.

CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
  FOR (n:Guideline) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT recommendation_id_unique IF NOT EXISTS
  FOR (n:Recommendation) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT strategy_id_unique IF NOT EXISTS
  FOR (n:Strategy) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT condition_id_unique IF NOT EXISTS
  FOR (n:Condition) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT observation_id_unique IF NOT EXISTS
  FOR (n:Observation) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT medication_id_unique IF NOT EXISTS
  FOR (n:Medication) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT procedure_id_unique IF NOT EXISTS
  FOR (n:Procedure) REQUIRE n.id IS UNIQUE;
