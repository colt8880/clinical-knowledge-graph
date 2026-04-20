"""Cross-guideline interactions endpoint for the Interactions view."""

from fastapi import APIRouter, Query

from app.queries.interactions_query import fetch_interactions, VALID_DOMAINS

router = APIRouter(tags=["query"])


@router.get("/interactions")
async def get_interactions(
    type: str = Query(
        "both",
        description="Edge type filter: preemption, modifier, or both.",
        pattern="^(preemption|modifier|both)$",
    ),
    guidelines: str | None = Query(
        None,
        description=(
            "Comma-separated guideline domain labels to include "
            "(uspstf, acc-aha, kdigo). Default returns all."
        ),
    ),
):
    """Return the cross-guideline interaction structure.

    Only PREEMPTED_BY and MODIFIES edges are included, with their
    participating Recommendation endpoints. Used by the /interactions UI view.
    """
    # Normalise guideline slugs to domain labels.
    slug_to_domain = {
        "uspstf": "USPSTF",
        "acc-aha": "ACC_AHA",
        "acc_aha": "ACC_AHA",
        "kdigo": "KDIGO",
    }

    guideline_list: list[str] | None = None
    if guidelines is not None:
        guideline_list = []
        for slug in guidelines.split(","):
            slug = slug.strip().lower()
            domain = slug_to_domain.get(slug)
            if domain and domain in VALID_DOMAINS:
                guideline_list.append(domain)
        if not guideline_list:
            guideline_list = None  # Fall back to all if none valid.

    return await fetch_interactions(
        edge_type_filter=type,
        guideline_filter=guideline_list,
    )
