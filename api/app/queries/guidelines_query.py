"""Cypher query for the GET /guidelines metadata list."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import neo4j.time

from app.db import get_driver


def _to_str(val: Any) -> str:
    """Convert a Neo4j temporal value to its ISO string, or str() otherwise."""
    if isinstance(val, (neo4j.time.Date, neo4j.time.DateTime)):
        return val.iso_format()
    return str(val) if val is not None else ""

# Pre-compute seed hashes at import time — files don't change at runtime.
_SEED_DIR = Path(__file__).resolve().parents[3] / "graph" / "seeds"

_GUIDELINE_SEED_FILES: dict[str, str] = {
    "guideline:uspstf-statin-2022": "statins.cypher",
    "guideline:acc-aha-cholesterol-2018": "cholesterol.cypher",
    "guideline:kdigo-ckd-2024": "kdigo-ckd.cypher",
    "guideline:ada-diabetes-2024": "ada-diabetes.cypher",
}


def _compute_seed_hash(filename: str) -> str | None:
    path = _SEED_DIR / filename
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


_SEED_HASHES: dict[str, str | None] = {
    gid: _compute_seed_hash(fname)
    for gid, fname in _GUIDELINE_SEED_FILES.items()
}

# Domain slug mapping.
_DOMAIN_SLUGS: dict[str, str] = {
    "USPSTF": "uspstf-statin-2022",
    "ACC_AHA": "acc-aha-cholesterol-2018",
    "KDIGO": "kdigo-ckd-2024",
    "ADA": "ada-diabetes-2024",
}

_DOMAIN_LABELS: dict[str, str] = {
    "USPSTF": "USPSTF",
    "ACC_AHA": "ACC/AHA",
    "KDIGO": "KDIGO",
    "ADA": "ADA",
}

GUIDELINES_QUERY = """
MATCH (g:Guideline)
OPTIONAL MATCH (g)<-[:FROM_GUIDELINE]-(r:Recommendation)
WITH g, count(r) AS rec_count
RETURN g, rec_count
ORDER BY g.id
"""


async def fetch_guidelines() -> list[dict[str, Any]]:
    """Fetch guideline metadata for the index page."""
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(GUIDELINES_QUERY)
        records = [record async for record in result]

    guidelines: list[dict[str, Any]] = []
    for record in records:
        g = record["g"]
        props = dict(g.items())
        g_id = props.get("id", "")
        labels = g.labels

        # Determine domain from labels.
        domain = None
        for d in ("USPSTF", "ACC_AHA", "KDIGO"):
            if d in labels:
                domain = d
                break

        # Parse coverage JSON.
        coverage_raw = props.get("coverage")
        coverage = None
        if coverage_raw:
            try:
                coverage = json.loads(coverage_raw)
            except (json.JSONDecodeError, TypeError):
                coverage = None

        guidelines.append({
            "id": _DOMAIN_SLUGS.get(domain, g_id) if domain else g_id,
            "domain": _DOMAIN_LABELS.get(domain, domain) if domain else None,
            "title": props.get("title", ""),
            "version": _to_str(props.get("version", "")),
            "publication_date": _to_str(props.get("effective_date", "")),
            "citation_url": props.get("url", ""),
            "rec_count": record["rec_count"],
            "coverage": coverage,
            "seed_hash": _SEED_HASHES.get(g_id),
            "last_updated_in_graph": _to_str(
                props.get("provenance_publication_date", "")
            ),
        })

    return guidelines
