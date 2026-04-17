"""Integration tests for GET /subgraph endpoint."""

import pytest


@pytest.mark.anyio
async def test_subgraph_no_domains_returns_full_forest(client):
    """No domains param = all three guidelines + shared entities."""
    resp = await client.get("/subgraph")
    assert resp.status_code == 200
    data = resp.json()

    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0

    # Should include nodes from all three domains.
    domains_found = {n.get("domain") for n in data["nodes"]}
    assert "USPSTF" in domains_found
    assert "ACC_AHA" in domains_found
    assert "KDIGO" in domains_found
    # Shared entities have domain=null.
    assert None in domains_found


@pytest.mark.anyio
async def test_subgraph_single_domain(client):
    """Single domain returns that guideline + shared entities only."""
    resp = await client.get("/subgraph?domains=USPSTF")
    assert resp.status_code == 200
    data = resp.json()

    domains_found = {n.get("domain") for n in data["nodes"] if n.get("domain") is not None}
    assert domains_found == {"USPSTF"}

    # Should still include shared entities (domain=None).
    shared = [n for n in data["nodes"] if n.get("domain") is None]
    assert len(shared) > 0


@pytest.mark.anyio
async def test_subgraph_two_domains_returns_union(client):
    """Two domains returns their union + shared entities."""
    resp = await client.get("/subgraph?domains=USPSTF,ACC_AHA")
    assert resp.status_code == 200
    data = resp.json()

    domains_found = {n.get("domain") for n in data["nodes"] if n.get("domain") is not None}
    assert "USPSTF" in domains_found
    assert "ACC_AHA" in domains_found
    assert "KDIGO" not in domains_found


@pytest.mark.anyio
async def test_subgraph_empty_domains_returns_shared_only(client):
    """Empty domains= returns only shared entities."""
    resp = await client.get("/subgraph?domains=")
    assert resp.status_code == 200
    data = resp.json()

    # All nodes should be shared entities (domain=None).
    for n in data["nodes"]:
        assert n.get("domain") is None, f"Expected shared entity, got domain={n.get('domain')} for {n['id']}"


@pytest.mark.anyio
async def test_subgraph_shared_entities_not_duplicated(client):
    """Shared entities appear exactly once regardless of how many guidelines reference them."""
    resp = await client.get("/subgraph")
    assert resp.status_code == 200
    data = resp.json()

    node_ids = [n["id"] for n in data["nodes"]]
    assert len(node_ids) == len(set(node_ids)), "Duplicate node ids found"


@pytest.mark.anyio
async def test_subgraph_response_shape(client):
    """Response shape matches the OpenAPI contract."""
    resp = await client.get("/subgraph?domains=USPSTF")
    assert resp.status_code == 200
    data = resp.json()

    # Top-level keys.
    assert set(data.keys()) >= {"nodes", "edges"}

    # Node shape.
    for n in data["nodes"]:
        assert "id" in n
        assert "labels" in n
        assert isinstance(n["labels"], list)
        assert "properties" in n
        assert "domain" in n

    # Edge shape.
    for e in data["edges"]:
        assert "id" in e
        assert "start" in e
        assert "end" in e
        assert "type" in e
        assert "properties" in e


@pytest.mark.anyio
async def test_subgraph_deterministic_ordering(client):
    """Nodes sorted by id, edges sorted by (start, end, type)."""
    resp = await client.get("/subgraph")
    assert resp.status_code == 200
    data = resp.json()

    node_ids = [n["id"] for n in data["nodes"]]
    assert node_ids == sorted(node_ids), "Nodes not sorted by id"

    edge_keys = [(e["start"], e["end"], e["type"]) for e in data["edges"]]
    assert edge_keys == sorted(edge_keys), "Edges not sorted by (start, end, type)"


@pytest.mark.anyio
async def test_subgraph_edges_have_both_endpoints_in_nodeset(client):
    """Every edge has both start and end in the returned node set."""
    resp = await client.get("/subgraph?domains=KDIGO")
    assert resp.status_code == 200
    data = resp.json()

    node_ids = {n["id"] for n in data["nodes"]}
    for e in data["edges"]:
        assert e["start"] in node_ids, f"Edge start {e['start']} not in node set"
        assert e["end"] in node_ids, f"Edge end {e['end']} not in node set"
