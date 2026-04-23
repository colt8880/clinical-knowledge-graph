"""Integration tests for GET /guidelines."""

import pytest


@pytest.mark.anyio
async def test_guidelines_returns_list(client):
    """GET /guidelines returns a JSON list."""
    resp = await client.get("/guidelines")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_guidelines_returns_four(client):
    """The seeded graph has four guidelines (USPSTF, ACC/AHA, KDIGO, ADA)."""
    resp = await client.get("/guidelines")
    data = resp.json()
    assert len(data) == 4


@pytest.mark.anyio
async def test_guidelines_shape(client):
    """Each guideline has the expected fields."""
    resp = await client.get("/guidelines")
    data = resp.json()
    required_keys = {
        "id", "domain", "title", "version", "publication_date",
        "citation_url", "rec_count", "coverage", "seed_hash",
        "last_updated_in_graph",
    }
    for g in data:
        assert required_keys.issubset(g.keys()), f"Missing keys in {g.get('id')}: {required_keys - g.keys()}"


@pytest.mark.anyio
async def test_guidelines_coverage_block_present(client):
    """Each guideline has a non-null coverage block with modeled/deferred/exit_only."""
    resp = await client.get("/guidelines")
    data = resp.json()
    for g in data:
        assert g["coverage"] is not None, f"coverage is null for {g['id']}"
        assert "modeled" in g["coverage"]
        assert "deferred" in g["coverage"]
        assert "exit_only" in g["coverage"]


@pytest.mark.anyio
async def test_guidelines_rec_counts(client):
    """USPSTF has 3 recs, ACC/AHA has 4, KDIGO has 4, ADA has 5."""
    resp = await client.get("/guidelines")
    data = resp.json()
    by_domain = {g["domain"]: g for g in data}
    assert by_domain["USPSTF"]["rec_count"] == 3
    assert by_domain["ACC/AHA"]["rec_count"] == 4
    assert by_domain["KDIGO"]["rec_count"] == 4
    assert by_domain["ADA"]["rec_count"] == 5


@pytest.mark.anyio
async def test_guidelines_seed_hash_present(client):
    """Each guideline has a non-null seed_hash (sha256 string)."""
    resp = await client.get("/guidelines")
    data = resp.json()
    for g in data:
        assert g["seed_hash"] is not None, f"seed_hash is null for {g['id']}"
        assert len(g["seed_hash"]) == 64, f"seed_hash wrong length for {g['id']}"
