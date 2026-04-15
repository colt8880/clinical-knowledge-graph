"""Health-check and version endpoints."""

from fastapi import APIRouter

from app.config import settings
from app.db import verify_connectivity

router = APIRouter(tags=["meta"])


@router.get("/healthz")
async def healthz():
    neo4j_ok = await verify_connectivity()
    return {
        "status": "ok" if neo4j_ok else "degraded",
        "neo4j": "ok" if neo4j_ok else "unreachable",
    }


@router.get("/version")
async def version():
    return {
        "spec_tag": settings.spec_tag,
        "graph_version": settings.graph_version,
        "evaluator_version": settings.evaluator_version,
    }
