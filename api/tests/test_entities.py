"""Integration tests for the shared clinical entity layer (F20).

Asserts that canonical entities exist after seed with correct primary keys,
codings, domain labels, and no orphans. Requires a seeded Neo4j instance.
Uses the `client` fixture from conftest.py which initializes the Neo4j driver.
"""

from __future__ import annotations

from collections import Counter

import pytest

from app.db import read_tx


# ---------------------------------------------------------------------------
# Medication primary keys
# ---------------------------------------------------------------------------

class TestMedicationPrimaryKeys:
    """Every Medication has code_system='RxNorm' and a non-null code."""

    @pytest.mark.asyncio
    async def test_no_medication_missing_code(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) WHERE m.code IS NULL RETURN count(m) AS c",
        )
        assert rows[0]["c"] == 0, "Found Medication nodes with null code"

    @pytest.mark.asyncio
    async def test_no_medication_missing_code_system(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) WHERE m.code_system IS NULL RETURN count(m) AS c",
        )
        assert rows[0]["c"] == 0, "Found Medication nodes with null code_system"

    @pytest.mark.asyncio
    async def test_all_medications_rxnorm(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) WHERE m.code_system <> 'RxNorm' RETURN count(m) AS c",
        )
        assert rows[0]["c"] == 0, "Found Medication nodes with non-RxNorm code_system"

    @pytest.mark.asyncio
    async def test_medication_code_uniqueness(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) RETURN m.code AS code, m.code_system AS sys",
        )
        pairs = [(r["code"], r["sys"]) for r in rows]
        dupes = [p for p, count in Counter(pairs).items() if count > 1]
        assert dupes == [], f"Duplicate Medication (code, code_system) pairs: {dupes}"

    @pytest.mark.asyncio
    async def test_expected_medication_count(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) RETURN count(m) AS c",
        )
        assert rows[0]["c"] == 7, f"Expected 7 Medications, got {rows[0]['c']}"


# ---------------------------------------------------------------------------
# Observation primary keys
# ---------------------------------------------------------------------------

class TestObservationPrimaryKeys:
    """Every Observation has code_system='LOINC' and a non-null code."""

    @pytest.mark.asyncio
    async def test_no_observation_missing_code(self, client):
        rows = await read_tx(
            "MATCH (o:Observation) WHERE o.code IS NULL RETURN count(o) AS c",
        )
        assert rows[0]["c"] == 0

    @pytest.mark.asyncio
    async def test_all_observations_loinc(self, client):
        rows = await read_tx(
            "MATCH (o:Observation) WHERE o.code_system <> 'LOINC' RETURN count(o) AS c",
        )
        assert rows[0]["c"] == 0

    @pytest.mark.asyncio
    async def test_expected_observation_count(self, client):
        rows = await read_tx(
            "MATCH (o:Observation) RETURN count(o) AS c",
        )
        assert rows[0]["c"] == 4, f"Expected 4 Observations, got {rows[0]['c']}"


# ---------------------------------------------------------------------------
# Procedure primary keys
# ---------------------------------------------------------------------------

class TestProcedurePrimaryKeys:
    """Every Procedure has code_system='CPT' and a non-null code."""

    @pytest.mark.asyncio
    async def test_no_procedure_missing_code(self, client):
        rows = await read_tx(
            "MATCH (p:Procedure) WHERE p.code IS NULL RETURN count(p) AS c",
        )
        assert rows[0]["c"] == 0

    @pytest.mark.asyncio
    async def test_all_procedures_cpt(self, client):
        rows = await read_tx(
            "MATCH (p:Procedure) WHERE p.code_system <> 'CPT' RETURN count(p) AS c",
        )
        assert rows[0]["c"] == 0

    @pytest.mark.asyncio
    async def test_expected_procedure_count(self, client):
        rows = await read_tx(
            "MATCH (p:Procedure) RETURN count(p) AS c",
        )
        assert rows[0]["c"] == 1, f"Expected 1 Procedure, got {rows[0]['c']}"


# ---------------------------------------------------------------------------
# Condition multi-coding
# ---------------------------------------------------------------------------

class TestConditionCodings:
    """Every Condition has a non-empty codings list with at least one SNOMED entry."""

    @pytest.mark.asyncio
    async def test_no_condition_missing_codings(self, client):
        rows = await read_tx(
            "MATCH (c:Condition) WHERE c.codings IS NULL OR size(c.codings) = 0 RETURN count(c) AS c",
        )
        assert rows[0]["c"] == 0, "Found Condition nodes with null or empty codings"

    @pytest.mark.asyncio
    async def test_all_conditions_have_snomed(self, client):
        """Every Condition has at least one SNOMED entry in codings."""
        rows = await read_tx(
            """
            MATCH (c:Condition)
            WHERE NONE(coding IN c.codings WHERE coding STARTS WITH 'SNOMED:')
            RETURN c.id AS id
            """,
        )
        missing = [r["id"] for r in rows]
        assert missing == [], f"Conditions without SNOMED coding: {missing}"

    @pytest.mark.asyncio
    async def test_all_conditions_have_icd10(self, client):
        """Every v0 Condition also carries ICD-10-CM."""
        rows = await read_tx(
            """
            MATCH (c:Condition)
            WHERE NONE(coding IN c.codings WHERE coding STARTS WITH 'ICD10:')
            RETURN c.id AS id
            """,
        )
        missing = [r["id"] for r in rows]
        assert missing == [], f"Conditions without ICD-10 coding: {missing}"

    @pytest.mark.asyncio
    async def test_condition_coding_uniqueness(self, client):
        """No two Condition nodes share any (system, code) pair."""
        rows = await read_tx(
            """
            MATCH (a:Condition), (b:Condition)
            WHERE a <> b AND ANY(c IN a.codings WHERE c IN b.codings)
            RETURN count(*) AS c
            """,
        )
        assert rows[0]["c"] == 0, "Found Condition nodes sharing coding entries"

    @pytest.mark.asyncio
    async def test_expected_condition_count(self, client):
        rows = await read_tx(
            "MATCH (c:Condition) RETURN count(c) AS c",
        )
        assert rows[0]["c"] == 5, f"Expected 5 Conditions, got {rows[0]['c']}"


# ---------------------------------------------------------------------------
# Domain labels
# ---------------------------------------------------------------------------

class TestDomainLabels:
    """Guideline-scoped nodes carry :USPSTF; shared entities do not."""

    @pytest.mark.asyncio
    async def test_all_recommendations_labeled(self, client):
        rows = await read_tx(
            "MATCH (r:Recommendation) WHERE NOT r:USPSTF RETURN count(r) AS c",
        )
        assert rows[0]["c"] == 0, "Found Recommendation nodes without :USPSTF"

    @pytest.mark.asyncio
    async def test_all_strategies_labeled(self, client):
        rows = await read_tx(
            "MATCH (s:Strategy) WHERE NOT s:USPSTF RETURN count(s) AS c",
        )
        assert rows[0]["c"] == 0, "Found Strategy nodes without :USPSTF"

    @pytest.mark.asyncio
    async def test_guideline_labeled(self, client):
        rows = await read_tx(
            "MATCH (g:Guideline) WHERE NOT g:USPSTF RETURN count(g) AS c",
        )
        assert rows[0]["c"] == 0, "Found Guideline nodes without :USPSTF"

    @pytest.mark.asyncio
    async def test_entities_not_labeled(self, client):
        """Clinical entity nodes must NOT carry domain labels."""
        rows = await read_tx(
            """
            MATCH (n)
            WHERE (n:Medication OR n:Condition OR n:Observation OR n:Procedure)
              AND n:USPSTF
            RETURN count(n) AS c
            """,
        )
        assert rows[0]["c"] == 0, "Found clinical entity nodes with :USPSTF label"


# ---------------------------------------------------------------------------
# Orphan check
# ---------------------------------------------------------------------------

class TestNoOrphans:
    """Every shared entity is referenced by at least one guideline seed."""

    @pytest.mark.asyncio
    async def test_no_orphan_medications(self, client):
        rows = await read_tx(
            "MATCH (m:Medication) WHERE NOT (m)<-[:INCLUDES_ACTION|TARGETS]-() RETURN m.id AS id",
        )
        orphans = [r["id"] for r in rows]
        assert orphans == [], f"Orphan Medication nodes: {orphans}"

    @pytest.mark.asyncio
    async def test_no_orphan_procedures(self, client):
        rows = await read_tx(
            "MATCH (p:Procedure) WHERE NOT (p)<-[:INCLUDES_ACTION|TARGETS]-() RETURN p.id AS id",
        )
        orphans = [r["id"] for r in rows]
        assert orphans == [], f"Orphan Procedure nodes: {orphans}"
