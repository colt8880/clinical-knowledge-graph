"""Shared fixtures for API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db import init_driver, close_driver, _driver
from app.main import app


@pytest.fixture
async def client():
    """AsyncClient wired to the FastAPI app with a live Neo4j driver."""
    await init_driver(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        await close_driver()
