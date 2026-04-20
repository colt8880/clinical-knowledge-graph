"""GET /guidelines — guideline metadata list for the UI index page."""

from fastapi import APIRouter

from app.queries.guidelines_query import fetch_guidelines

router = APIRouter(tags=["query"])


@router.get("/guidelines")
async def get_guidelines():
    """Return metadata for all guidelines in the graph.

    Used by the UI guideline index page to render cards with title,
    version, coverage summary, and rec count.
    """
    return await fetch_guidelines()
