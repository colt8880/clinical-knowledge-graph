"""Integration tests for /nodes endpoints — requires seeded Neo4j."""

import pytest


# ── GET /nodes/{id} ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_guideline_node(client):
    """Known guideline id resolves to a GraphNode with correct labels."""
    resp = await client.get("/nodes/guideline:uspstf-statin-2022")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "guideline:uspstf-statin-2022"
    assert "Guideline" in body["labels"]
    assert body["properties"]["publisher"] == "US Preventive Services Task Force"


@pytest.mark.asyncio
async def test_get_medication_node(client):
    """Medication node surfaces rxnorm codes in the codes array."""
    resp = await client.get("/nodes/med:atorvastatin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "med:atorvastatin"
    assert "Medication" in body["labels"]
    rxnorm_codes = [c["code"] for c in body["codes"] if c["system"] == "rxnorm"]
    assert "83367" in rxnorm_codes


@pytest.mark.asyncio
async def test_get_nonexistent_node_returns_404(client):
    resp = await client.get("/nodes/nonexistent:id")
    assert resp.status_code == 404


# ── GET /nodes/{id}/neighbors ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_guideline_neighbors_returns_3_recommendations(client):
    """The guideline node has 3 inbound FROM_GUIDELINE edges from the 3 Recs."""
    resp = await client.get("/nodes/guideline:uspstf-statin-2022/neighbors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["center"] == "guideline:uspstf-statin-2022"

    # 4 nodes: guideline + 3 recs
    node_ids = sorted(n["id"] for n in body["nodes"])
    assert "guideline:uspstf-statin-2022" in node_ids
    assert "rec:statin-initiate-grade-b" in node_ids
    assert "rec:statin-selective-grade-c" in node_ids
    assert "rec:statin-insufficient-evidence-grade-i" in node_ids

    # 3 FROM_GUIDELINE edges
    fg_edges = [e for e in body["edges"] if e["type"] == "FROM_GUIDELINE"]
    assert len(fg_edges) == 3


@pytest.mark.asyncio
async def test_strategy_neighbors_with_edge_type_filter(client):
    """Filtering by INCLUDES_ACTION returns only medication/procedure neighbors."""
    resp = await client.get(
        "/nodes/strategy:statin-moderate-intensity/neighbors",
        params={"edge_types": ["INCLUDES_ACTION"]},
    )
    assert resp.status_code == 200
    body = resp.json()

    edge_types = {e["type"] for e in body["edges"]}
    assert edge_types == {"INCLUDES_ACTION"}

    # 7 statin medications + the strategy itself
    non_center = [n for n in body["nodes"] if n["id"] != "strategy:statin-moderate-intensity"]
    assert len(non_center) == 7


@pytest.mark.asyncio
async def test_neighbors_nonexistent_returns_404(client):
    resp = await client.get("/nodes/nonexistent:id/neighbors")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_neighbors_deterministic_ordering(client):
    """Two identical calls return the same node and edge order."""
    url = "/nodes/guideline:uspstf-statin-2022/neighbors"
    resp1 = await client.get(url)
    resp2 = await client.get(url)
    assert resp1.json() == resp2.json()


# ── OpenAPI contract test ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openapi_schema_contains_expected_paths(client):
    """Generated OpenAPI schema includes all implemented paths."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/healthz" in paths
    assert "/version" in paths
    assert "/nodes/{node_id}/neighbors" in paths
    assert "/nodes/{node_id}" in paths
