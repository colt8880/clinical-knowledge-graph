"""Bulk subgraph endpoint for the whole-forest Explore UI."""

from fastapi import APIRouter, Query

from app.db import fetch_subgraph

router = APIRouter(tags=["query"])

VALID_DOMAINS = {"USPSTF", "ACC_AHA", "KDIGO", "ADA"}


@router.get("/subgraph")
async def get_subgraph(
    domains: str | None = Query(
        None,
        description=(
            "Comma-separated domain labels (USPSTF, ACC_AHA, KDIGO, ADA). "
            "Default (absent) returns all guidelines. "
            "Empty string returns only shared entities."
        ),
    ),
):
    """Return the full subgraph for the requested guideline domains.

    Includes all guideline-scoped nodes with the requested domain labels
    plus all shared entity nodes referenced by any of them.
    """
    if domains is None:
        # No param = all guidelines
        domain_list = sorted(VALID_DOMAINS)
    elif domains.strip() == "":
        # Empty string = shared entities only
        domain_list = []
    else:
        domain_list = sorted(
            d.strip() for d in domains.split(",") if d.strip() in VALID_DOMAINS
        )

    return await fetch_subgraph(domain_list)
