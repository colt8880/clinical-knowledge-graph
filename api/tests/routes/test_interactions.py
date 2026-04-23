"""Integration tests for GET /interactions.

Cross-guideline edges re-added after clinician review (F41).
6 PREEMPTED_BY + 2 MODIFIES = 8 edges total.
"""

import pytest


@pytest.mark.anyio
async def test_interactions_returns_edges(client):
    """GET /interactions returns all 8 clinician-validated cross-guideline edges."""
    resp = await client.get("/interactions")
    assert resp.status_code == 200
    data = resp.json()

    assert "guidelines" in data
    assert "recommendations" in data
    assert "shared_entities" in data
    assert "edges" in data

    assert len(data["edges"]) == 8
    # Recs involved in at least one edge should be present.
    assert len(data["recommendations"]) > 0


@pytest.mark.anyio
async def test_interactions_preemption_filter(client):
    """type=preemption returns 6 PREEMPTED_BY edges."""
    resp = await client.get("/interactions?type=preemption")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 6
    for edge in data["edges"]:
        assert edge["type"] == "PREEMPTED_BY"


@pytest.mark.anyio
async def test_interactions_modifier_filter(client):
    """type=modifier returns 2 MODIFIES edges."""
    resp = await client.get("/interactions?type=modifier")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 2
    for edge in data["edges"]:
        assert edge["type"] == "MODIFIES"


@pytest.mark.anyio
async def test_interactions_guideline_filter(client):
    """guidelines= param filters to edges involving those domains."""
    resp = await client.get("/interactions?guidelines=uspstf,acc-aha")
    assert resp.status_code == 200
    data = resp.json()
    # All 6 PREEMPTED_BY edges are USPSTF↔ACC/AHA, so they should appear.
    # The 2 MODIFIES (KDIGO→ACC/AHA) should be excluded since KDIGO not in filter.
    assert len(data["edges"]) == 6


@pytest.mark.anyio
async def test_interactions_response_shape(client):
    """Response shape matches the expected structure."""
    resp = await client.get("/interactions")
    data = resp.json()

    # Guidelines should still be present (all four domains).
    assert len(data["guidelines"]) == 4
    for g in data["guidelines"]:
        assert "id" in g
        assert "domain" in g
        assert "title" in g

    assert isinstance(data["shared_entities"], list)
    assert isinstance(data["edges"], list)


@pytest.mark.anyio
async def test_interactions_determinism(client):
    """Same query returns same result — deterministic."""
    resp1 = await client.get("/interactions")
    resp2 = await client.get("/interactions")
    assert resp1.json() == resp2.json()
