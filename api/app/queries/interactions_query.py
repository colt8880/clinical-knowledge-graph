"""Cypher query for the GET /interactions cross-guideline view.

Returns PREEMPTED_BY and MODIFIES edges with their endpoint Recs,
guideline metadata, and shared entity references. One round-trip.
"""

from __future__ import annotations

from typing import Any

from app.db import get_driver

VALID_DOMAINS = {"USPSTF", "ACC_AHA", "KDIGO"}

# Domain slug and human-readable label mappings (shared with guidelines_query).
_DOMAIN_SLUGS: dict[str, str] = {
    "USPSTF": "uspstf-statin-2022",
    "ACC_AHA": "acc-aha-cholesterol-2018",
    "KDIGO": "kdigo-ckd-2024",
}
_DOMAIN_LABELS: dict[str, str] = {
    "USPSTF": "USPSTF",
    "ACC_AHA": "ACC/AHA",
    "KDIGO": "KDIGO",
}


def _extract_domain(labels: frozenset[str] | set[str]) -> str | None:
    for d in ("USPSTF", "ACC_AHA", "KDIGO"):
        if d in labels:
            return d
    return None


INTERACTIONS_QUERY = """
MATCH (source:Recommendation)-[edge]->(target:Recommendation)
WHERE type(edge) IN $edge_types
RETURN source, edge, target, type(edge) AS edge_type
ORDER BY source.id, target.id, type(edge)
"""

# Always fetch preempted IDs for suppression flag, regardless of edge filter.
PREEMPTED_IDS_QUERY = """
MATCH (source:Recommendation)-[:PREEMPTED_BY]->(target:Recommendation)
RETURN source.id AS preempted_id
"""


async def fetch_interactions(
    edge_type_filter: str = "both",
    guideline_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch cross-guideline interaction edges and their participating Recs.

    Parameters
    ----------
    edge_type_filter : str
        "preemption", "modifier", or "both".
    guideline_filter : list[str] | None
        Domain labels to include. None = all.

    Returns the spec'd InteractionsResponse shape.
    """
    edge_types: list[str] = []
    if edge_type_filter in ("preemption", "both"):
        edge_types.append("PREEMPTED_BY")
    if edge_type_filter in ("modifier", "both"):
        edge_types.append("MODIFIES")

    allowed_domains = set(guideline_filter) if guideline_filter else VALID_DOMAINS

    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(INTERACTIONS_QUERY, edge_types=edge_types)
        records = [record async for record in result]

        # Always fetch preempted IDs for suppression flag computation.
        preemption_result = await session.run(PREEMPTED_IDS_QUERY)
        preemption_records = [r async for r in preemption_result]

    # Collect unique guidelines, recs, edges, and shared entities.
    guidelines_map: dict[str, dict[str, Any]] = {}
    recs_map: dict[str, dict[str, Any]] = {}
    edges_out: list[dict[str, Any]] = []

    # Track preemption state for suppression flag computation.
    preempted_rec_ids: set[str] = set()
    for r in preemption_records:
        preempted_rec_ids.add(r["preempted_id"])

    for record in records:
        source_node = record["source"]
        target_node = record["target"]
        edge = record["edge"]
        edge_type = record["edge_type"]

        source_props = dict(source_node.items())
        target_props = dict(target_node.items())
        source_id = source_props.get("id", "")
        target_id = target_props.get("id", "")

        source_domain = _extract_domain(source_node.labels)
        target_domain = _extract_domain(target_node.labels)

        # Filter by guideline domains.
        if source_domain not in allowed_domains or target_domain not in allowed_domains:
            continue

        # Register guidelines.
        for domain in (source_domain, target_domain):
            if domain and domain not in guidelines_map:
                guidelines_map[domain] = {
                    "id": _DOMAIN_SLUGS.get(domain, domain),
                    "domain": _DOMAIN_LABELS.get(domain, domain),
                    "title": _DOMAIN_LABELS.get(domain, domain),
                }

        # Register recs.
        for node, props, domain in [
            (source_node, source_props, source_domain),
            (target_node, target_props, target_domain),
        ]:
            rec_id = props.get("id", "")
            if rec_id not in recs_map:
                recs_map[rec_id] = {
                    "id": rec_id,
                    "title": props.get("title", props.get("name", rec_id)),
                    "domain": _DOMAIN_LABELS.get(domain, domain) if domain else None,
                    "evidence_grade": props.get("evidence_grade"),
                    "has_preemption_in": False,
                    "has_preemption_out": False,
                    "modifier_count": 0,
                }

        # Build edge.
        edge_props = dict(edge.items())
        edge_data: dict[str, Any] = {
            "type": edge_type,
            "source": source_id,
            "target": target_id,
        }

        if edge_type == "PREEMPTED_BY":
            edge_data["edge_priority"] = edge_props.get("edge_priority", edge_props.get("priority"))
            edge_data["reason"] = edge_props.get("reason", "")
            # Source is preempted, target is winner.
            recs_map[source_id]["has_preemption_out"] = True
            recs_map[target_id]["has_preemption_in"] = True
        elif edge_type == "MODIFIES":
            edge_data["nature"] = edge_props.get("nature", "")
            edge_data["note"] = edge_props.get("note", "")
            # A modifier is suppressed if its target Rec is preempted.
            edge_data["suppressed_by_preemption"] = target_id in preempted_rec_ids
            recs_map[target_id]["modifier_count"] = recs_map[target_id].get("modifier_count", 0) + 1

        edges_out.append(edge_data)

    # Ensure all domains are represented in guidelines even if no edges match.
    for domain in allowed_domains:
        if domain not in guidelines_map:
            guidelines_map[domain] = {
                "id": _DOMAIN_SLUGS.get(domain, domain),
                "domain": _DOMAIN_LABELS.get(domain, domain),
                "title": _DOMAIN_LABELS.get(domain, domain),
            }

    return {
        "guidelines": sorted(guidelines_map.values(), key=lambda g: g["id"]),
        "recommendations": sorted(recs_map.values(), key=lambda r: r["id"]),
        "shared_entities": [],  # v1 MODIFIES targets are Recs, not shared entities.
        "edges": edges_out,
    }
