"""Integration tests for GET /interactions.

Cross-guideline edges have been removed pending clinician review.
These tests verify the endpoint works correctly with an empty edge set.
"""

import pytest


@pytest.mark.anyio
async def test_interactions_returns_empty_response(client):
    """GET /interactions returns a valid response with no edges."""
    resp = await client.get("/interactions")
    assert resp.status_code == 200
    data = resp.json()

    assert "guidelines" in data
    assert "recommendations" in data
    assert "shared_entities" in data
    assert "edges" in data

    # No cross-guideline edges in the graph (removed pending clinician review).
    assert len(data["edges"]) == 0
    assert len(data["recommendations"]) == 0


@pytest.mark.anyio
async def test_interactions_preemption_filter(client):
    """type=preemption returns empty edge list."""
    resp = await client.get("/interactions?type=preemption")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 0


@pytest.mark.anyio
async def test_interactions_modifier_filter(client):
    """type=modifier returns empty edge list."""
    resp = await client.get("/interactions?type=modifier")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 0


@pytest.mark.anyio
async def test_interactions_guideline_filter(client):
    """guidelines= param still returns valid response."""
    resp = await client.get("/interactions?guidelines=uspstf,acc-aha")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 0


@pytest.mark.anyio
async def test_interactions_response_shape(client):
    """Response shape matches the expected structure."""
    resp = await client.get("/interactions")
    data = resp.json()

    # Guidelines should still be present (all three domains).
    assert len(data["guidelines"]) == 3
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
