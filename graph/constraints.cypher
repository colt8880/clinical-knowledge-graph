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

// ---------------------------------------------------------------------------
// Primary-key uniqueness constraints (per ADR 0017).
//
// Medication, Observation, and Procedure carry a single-system primary key
// stored as (code, code_system). These constraints prevent two nodes of the
// same type from sharing a primary code.
//
// Condition uses multi-coding (codings list); uniqueness is enforced by a
// seed-time check in clinical-entities.cypher, not a native constraint
// (Neo4j constraints can't enforce list-element uniqueness).
// ---------------------------------------------------------------------------

CREATE CONSTRAINT medication_code_unique IF NOT EXISTS
  FOR (n:Medication) REQUIRE (n.code, n.code_system) IS UNIQUE;

CREATE CONSTRAINT observation_code_unique IF NOT EXISTS
  FOR (n:Observation) REQUIRE (n.code, n.code_system) IS UNIQUE;

CREATE CONSTRAINT procedure_code_unique IF NOT EXISTS
  FOR (n:Procedure) REQUIRE (n.code, n.code_system) IS UNIQUE;

// ---------------------------------------------------------------------------
// Index on PREEMPTED_BY.priority for preemption resolution (F25, ADR 0018).
//
// Neo4j Community doesn't support relationship property indexes natively
// on all versions, so this is a range index on the relationship type.
// The evaluator loads all PREEMPTED_BY edges at query time; this index
// helps ORDER BY priority in the load query.
// ---------------------------------------------------------------------------

CREATE INDEX preempted_by_priority IF NOT EXISTS
  FOR ()-[r:PREEMPTED_BY]-() ON (r.priority);
