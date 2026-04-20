"""Unit tests for the interactions query module.

Cross-guideline edges have been removed pending clinician review.
Tests verify correct behavior with an empty edge set.
"""

import pytest

from app.queries.interactions_query import fetch_interactions, VALID_DOMAINS


@pytest.mark.anyio
async def test_fetch_interactions_default(client):
    """Default parameters return empty edges (no cross-guideline edges seeded)."""
    result = await fetch_interactions()
    assert "guidelines" in result
    assert "recommendations" in result
    assert "edges" in result
    assert len(result["edges"]) == 0


@pytest.mark.anyio
async def test_fetch_interactions_preemption_only(client):
    """Preemption filter returns empty list."""
    result = await fetch_interactions(edge_type_filter="preemption")
    assert len(result["edges"]) == 0


@pytest.mark.anyio
async def test_fetch_interactions_modifier_only(client):
    """Modifier filter returns empty list."""
    result = await fetch_interactions(edge_type_filter="modifier")
    assert len(result["edges"]) == 0


@pytest.mark.anyio
async def test_fetch_interactions_all_guidelines_present(client):
    """All three guideline domains appear even with no edges."""
    result = await fetch_interactions()
    guideline_ids = {g["id"] for g in result["guidelines"]}
    assert "uspstf-statin-2022" in guideline_ids
    assert "acc-aha-cholesterol-2018" in guideline_ids
    assert "kdigo-ckd-2024" in guideline_ids


@pytest.mark.anyio
async def test_valid_domains():
    """VALID_DOMAINS matches the expected set."""
    assert VALID_DOMAINS == {"USPSTF", "ACC_AHA", "KDIGO"}
