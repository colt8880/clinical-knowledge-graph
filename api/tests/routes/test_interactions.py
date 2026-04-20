"""Integration tests for GET /interactions."""

import pytest


@pytest.mark.anyio
async def test_interactions_returns_full_response(client):
    """GET /interactions returns the full cross-guideline structure."""
    resp = await client.get("/interactions")
    assert resp.status_code == 200
    data = resp.json()

    assert "guidelines" in data
    assert "recommendations" in data
    assert "shared_entities" in data
    assert "edges" in data

    # Should have edges (9 PREEMPTED_BY + 6 MODIFIES = 15 total).
    assert len(data["edges"]) == 15


@pytest.mark.anyio
async def test_interactions_preemption_filter(client):
    """type=preemption returns only PREEMPTED_BY edges."""
    resp = await client.get("/interactions?type=preemption")
    assert resp.status_code == 200
    data = resp.json()

    for edge in data["edges"]:
        assert edge["type"] == "PREEMPTED_BY"
    assert len(data["edges"]) == 9


@pytest.mark.anyio
async def test_interactions_modifier_filter(client):
    """type=modifier returns only MODIFIES edges."""
    resp = await client.get("/interactions?type=modifier")
    assert resp.status_code == 200
    data = resp.json()

    for edge in data["edges"]:
        assert edge["type"] == "MODIFIES"
    assert len(data["edges"]) == 6


@pytest.mark.anyio
async def test_interactions_guideline_filter(client):
    """guidelines=uspstf,acc-aha excludes KDIGO modifier edges."""
    resp = await client.get("/interactions?guidelines=uspstf,acc-aha")
    assert resp.status_code == 200
    data = resp.json()

    # No MODIFIES edges should be present (all originate from KDIGO).
    modifies_edges = [e for e in data["edges"] if e["type"] == "MODIFIES"]
    assert len(modifies_edges) == 0

    # PREEMPTED_BY edges between USPSTF and ACC/AHA should remain.
    preemption_edges = [e for e in data["edges"] if e["type"] == "PREEMPTED_BY"]
    assert len(preemption_edges) == 9


@pytest.mark.anyio
async def test_interactions_suppressed_modifier_flag(client):
    """Suppressed-modifier flag is set correctly."""
    resp = await client.get("/interactions?type=modifier")
    assert resp.status_code == 200
    data = resp.json()

    for edge in data["edges"]:
        assert "suppressed_by_preemption" in edge
        # MODIFIES edges targeting preempted recs should be suppressed.
        if edge["target"].startswith("rec:statin-"):
            # USPSTF recs are preempted by ACC/AHA.
            assert edge["suppressed_by_preemption"] is True


@pytest.mark.anyio
async def test_interactions_response_shape(client):
    """Response shape matches the expected structure."""
    resp = await client.get("/interactions")
    data = resp.json()

    # Guidelines.
    for g in data["guidelines"]:
        assert "id" in g
        assert "domain" in g
        assert "title" in g

    # Recommendations.
    for r in data["recommendations"]:
        assert "id" in r
        assert "title" in r
        assert "domain" in r
        assert "has_preemption_in" in r
        assert "has_preemption_out" in r
        assert "modifier_count" in r

    # Edges.
    for e in data["edges"]:
        assert "type" in e
        assert "source" in e
        assert "target" in e
        if e["type"] == "PREEMPTED_BY":
            assert "edge_priority" in e
            assert "reason" in e
        elif e["type"] == "MODIFIES":
            assert "nature" in e
            assert "note" in e
            assert "suppressed_by_preemption" in e


@pytest.mark.anyio
async def test_interactions_determinism(client):
    """Same query returns same ordering — deterministic."""
    resp1 = await client.get("/interactions")
    resp2 = await client.get("/interactions")
    assert resp1.json() == resp2.json()
