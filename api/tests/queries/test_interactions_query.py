"""Unit tests for the interactions query module.

Cross-guideline edges re-added after clinician review (F41).
6 PREEMPTED_BY + 2 MODIFIES = 8 edges total.
"""

import pytest

from app.queries.interactions_query import fetch_interactions, VALID_DOMAINS


@pytest.mark.anyio
async def test_fetch_interactions_default(client):
    """Default parameters return all 8 clinician-validated cross-guideline edges."""
    result = await fetch_interactions()
    assert "guidelines" in result
    assert "recommendations" in result
    assert "edges" in result
    assert len(result["edges"]) == 8


@pytest.mark.anyio
async def test_fetch_interactions_preemption_only(client):
    """Preemption filter returns 6 PREEMPTED_BY edges (ACC/AHA preempts USPSTF)."""
    result = await fetch_interactions(edge_type_filter="preemption")
    assert len(result["edges"]) == 6
    for edge in result["edges"]:
        assert edge["type"] == "PREEMPTED_BY"


@pytest.mark.anyio
async def test_fetch_interactions_modifier_only(client):
    """Modifier filter returns 2 MODIFIES edges (KDIGO intensity_reduction on ACC/AHA)."""
    result = await fetch_interactions(edge_type_filter="modifier")
    assert len(result["edges"]) == 2
    for edge in result["edges"]:
        assert edge["type"] == "MODIFIES"
        assert edge["nature"] == "intensity_reduction"


@pytest.mark.anyio
async def test_fetch_interactions_all_guidelines_present(client):
    """All three guideline domains appear."""
    result = await fetch_interactions()
    guideline_ids = {g["id"] for g in result["guidelines"]}
    assert "uspstf-statin-2022" in guideline_ids
    assert "acc-aha-cholesterol-2018" in guideline_ids
    assert "kdigo-ckd-2024" in guideline_ids


@pytest.mark.anyio
async def test_valid_domains():
    """VALID_DOMAINS matches the expected set."""
    assert VALID_DOMAINS == {"USPSTF", "ACC_AHA", "KDIGO"}
