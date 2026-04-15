from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_healthz_returns_ok():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_version_returns_version():
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.json()
