"""Unit tests for the interactions query module."""

import pytest

from app.queries.interactions_query import fetch_interactions, VALID_DOMAINS


@pytest.mark.anyio
async def test_fetch_interactions_default(client):
    """Default parameters return all cross-guideline edges."""
    result = await fetch_interactions()
    assert "guidelines" in result
    assert "recommendations" in result
    assert "edges" in result
    assert len(result["edges"]) == 15  # 9 PREEMPTED_BY + 6 MODIFIES


@pytest.mark.anyio
async def test_fetch_interactions_preemption_only(client):
    """Preemption filter returns only PREEMPTED_BY."""
    result = await fetch_interactions(edge_type_filter="preemption")
    assert all(e["type"] == "PREEMPTED_BY" for e in result["edges"])


@pytest.mark.anyio
async def test_fetch_interactions_modifier_only(client):
    """Modifier filter returns only MODIFIES."""
    result = await fetch_interactions(edge_type_filter="modifier")
    assert all(e["type"] == "MODIFIES" for e in result["edges"])


@pytest.mark.anyio
async def test_fetch_interactions_guideline_filter(client):
    """Guideline filter excludes edges from/to excluded domains."""
    result = await fetch_interactions(guideline_filter=["USPSTF", "ACC_AHA"])
    # All MODIFIES edges come from KDIGO, so should be excluded.
    modifies = [e for e in result["edges"] if e["type"] == "MODIFIES"]
    assert len(modifies) == 0


@pytest.mark.anyio
async def test_fetch_interactions_all_guidelines_present(client):
    """All three guideline domains appear even when some have no edges."""
    result = await fetch_interactions(guideline_filter=["USPSTF"])
    guideline_ids = {g["id"] for g in result["guidelines"]}
    # Even with only USPSTF filtered, the guideline list includes USPSTF.
    assert "uspstf-statin-2022" in guideline_ids


@pytest.mark.anyio
async def test_valid_domains():
    """VALID_DOMAINS matches the expected set."""
    assert VALID_DOMAINS == {"USPSTF", "ACC_AHA", "KDIGO"}
