"""Tests for /healthz and /version endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ── Unit-style: no Neo4j dependency ─────────────────────────────────────


@pytest.mark.asyncio
async def test_version_returns_stamps():
    """GET /version returns the three required version stamps."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/version")

    assert resp.status_code == 200
    body = resp.json()
    assert "spec_tag" in body
    assert "graph_version" in body
    assert "evaluator_version" in body


# ── Integration: requires Neo4j (ckg-neo4j container) ──────────────────


@pytest.mark.asyncio
async def test_healthz_with_neo4j(client):
    """GET /healthz reports neo4j ok when the container is reachable."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["neo4j"] == "ok"
