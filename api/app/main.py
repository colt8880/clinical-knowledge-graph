"""FastAPI application — entrypoint for the Clinical Knowledge Graph API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_driver, close_driver
from app.routes import health, nodes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_driver(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    yield
    await close_driver()


app = FastAPI(
    title="Clinical Knowledge Graph API",
    version=settings.spec_tag,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(nodes.router)
