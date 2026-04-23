"""Neo4j driver wrapper. All Cypher lives here or in per-route modules."""

from __future__ import annotations

from typing import Any

import neo4j
from neo4j import AsyncGraphDatabase, AsyncDriver

_driver: AsyncDriver | None = None


async def init_driver(uri: str, user: str, password: str) -> None:
    global _driver
    _driver = AsyncGraphDatabase.driver(uri, auth=(user, password))


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


def get_driver() -> AsyncDriver:
    if _driver is None:
        raise RuntimeError("Neo4j driver not initialised — call init_driver first")
    return _driver


async def verify_connectivity() -> bool:
    """Return True if Neo4j is reachable, False otherwise."""
    try:
        await get_driver().verify_connectivity()
        return True
    except Exception:
        return False


async def read_tx(query: str, **params: Any) -> list[dict[str, Any]]:
    """Run *query* inside a managed read transaction and return records as dicts."""
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(query, params)
        return [record.data() async for record in result]


# ── Serialisation helpers ───────────────────────────────────────────────

def _serialise_value(val: Any) -> Any:
    """Convert Neo4j temporal/spatial types to JSON-safe primitives."""
    if isinstance(val, (neo4j.time.Date, neo4j.time.DateTime)):
        return val.iso_format()
    if isinstance(val, neo4j.time.Duration):
        return str(val)
    if isinstance(val, list):
        return [_serialise_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _serialise_value(v) for k, v in val.items()}
    return val


def _serialise_props(props: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialise_value(v) for k, v in props.items()}


# ── Node helpers ────────────────────────────────────────────────────────

def _node_to_dict(node: neo4j.graph.Node) -> dict[str, Any]:
    """Convert a Neo4j Node object to the GraphNode schema shape."""
    props = dict(node.items())
    node_id = props.pop("id", None)
    codes = _extract_codes(props)
    return {
        "id": node_id,
        "labels": sorted(node.labels),
        "properties": _serialise_props(props),
        "codes": codes,
    }


def _extract_codes(props: dict[str, Any]) -> list[dict[str, str]]:
    """Pull code-list properties into the codes[] array and remove them from props."""
    code_systems = {
        "snomed_codes": "snomed",
        "icd10_codes": "icd10",
        "loinc_codes": "loinc",
        "rxnorm_codes": "rxnorm",
        "cpt_codes": "cpt",
    }
    codes: list[dict[str, str]] = []
    for prop, system in code_systems.items():
        if prop in props:
            for code in props.pop(prop):
                codes.append({"system": system, "code": code})
    return codes


def _rel_to_dict(rel: neo4j.graph.Relationship) -> dict[str, Any]:
    """Convert a Neo4j Relationship to the GraphEdge schema shape."""
    props = dict(rel.items())
    return {
        "id": str(rel.element_id),
        "type": rel.type,
        "start": rel.start_node["id"] if "id" in rel.start_node else str(rel.start_node.element_id),
        "end": rel.end_node["id"] if "id" in rel.end_node else str(rel.end_node.element_id),
        "properties": _serialise_props(props),
    }


async def fetch_subgraph(domains: list[str]) -> dict[str, Any]:
    """Fetch the full subgraph for the requested guideline domains.

    Returns all guideline-scoped nodes with the requested domain labels,
    plus all shared entity nodes that any of them reference via edges.
    Edges are included only when both endpoints are in the returned node set.
    Nodes sorted by id; edges sorted by (source, target, type).
    """
    driver = get_driver()
    async with driver.session() as session:
        # Domain labels are Neo4j labels on guideline-scoped nodes (e.g. :USPSTF).
        # Shared entities (Medication, Condition, etc.) have no domain label.
        domain_labels = ["USPSTF", "ACC_AHA", "KDIGO", "ADA"]
        shared_entity_labels = ["Medication", "Condition", "Observation", "Procedure"]

        if domains:
            # Fetch guideline-scoped nodes for requested domains + shared entities they reference.
            # Build a label disjunction for the WHERE clause.
            label_checks = " OR ".join(f"n:{d}" for d in domains)
            query = f"""
                MATCH (n)
                WHERE ({label_checks})
                  AND NOT any(lbl IN labels(n) WHERE lbl IN $shared_labels)
                WITH collect(n) AS guideline_nodes
                UNWIND guideline_nodes AS gn
                OPTIONAL MATCH (gn)-[r]-(shared)
                WHERE any(lbl IN labels(shared) WHERE lbl IN $shared_labels)
                  AND NOT any(lbl IN labels(shared) WHERE lbl IN $domain_labels)
                WITH guideline_nodes, collect(DISTINCT shared) AS shared_nodes
                WITH guideline_nodes + shared_nodes AS all_nodes
                UNWIND all_nodes AS n
                WITH collect(DISTINCT n) AS nodes
                UNWIND nodes AS a
                UNWIND nodes AS b
                WITH nodes, a, b
                WHERE a <> b
                OPTIONAL MATCH (a)-[r]->(b)
                WITH nodes, collect(r) AS rels
                RETURN nodes, [r IN rels WHERE r IS NOT NULL] AS edges
            """
        else:
            # No domains requested — return only shared entities.
            query = """
                MATCH (n)
                WHERE any(lbl IN labels(n) WHERE lbl IN $shared_labels)
                  AND NOT any(lbl IN labels(n) WHERE lbl IN $domain_labels)
                WITH collect(n) AS nodes
                UNWIND nodes AS a
                UNWIND nodes AS b
                WITH nodes, a, b
                WHERE a <> b
                OPTIONAL MATCH (a)-[r]->(b)
                WITH nodes, collect(r) AS rels
                RETURN nodes, [r IN rels WHERE r IS NOT NULL] AS edges
            """

        result = await session.run(
            query,
            shared_labels=shared_entity_labels,
            domain_labels=domain_labels,
        )
        record = await result.single()

        if record is None:
            return {"nodes": [], "edges": []}

        raw_nodes = record["nodes"]
        raw_edges = record["edges"]

        # Serialise nodes with domain assignment.
        nodes_out: list[dict[str, Any]] = []
        seen_node_ids: set[str] = set()
        for n in raw_nodes:
            nd = _node_to_dict(n)
            if nd["id"] in seen_node_ids:
                continue
            seen_node_ids.add(nd["id"])
            # Determine domain from labels.
            nd["domain"] = _extract_domain(n.labels, domain_labels)
            nodes_out.append(nd)

        # Serialise edges, dedup.
        edges_out: list[dict[str, Any]] = []
        seen_edge_ids: set[str] = set()
        for r in raw_edges:
            rd = _rel_to_dict(r)
            if rd["id"] in seen_edge_ids:
                continue
            # Only include edges where both endpoints are in node set.
            if rd["start"] in seen_node_ids and rd["end"] in seen_node_ids:
                seen_edge_ids.add(rd["id"])
                edges_out.append(rd)

        nodes_out.sort(key=lambda n: n["id"])
        edges_out.sort(key=lambda e: (e["start"], e["end"], e["type"]))

        return {"nodes": nodes_out, "edges": edges_out}


def _extract_domain(labels: frozenset[str], domain_labels: list[str]) -> str | None:
    """Return the domain label if the node has one, else None (shared entity)."""
    for d in domain_labels:
        if d in labels:
            return d
    return None


async def fetch_node(node_id: str) -> dict[str, Any] | None:
    """Fetch a single node by its stable `id` property."""
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (n {id: $id}) RETURN n",
            id=node_id,
        )
        record = await result.single()
        if record is None:
            return None
        return _node_to_dict(record["n"])


async def fetch_neighbors(node_id: str, edge_types: list[str] | None = None) -> dict[str, Any] | None:
    """Fetch a node and its one-hop inbound + outbound neighbors.

    Returns a Subgraph dict (center, nodes, edges) or None if the center
    node doesn't exist. Neighbors sorted by id for determinism.
    """
    driver = get_driver()
    async with driver.session() as session:
        # First verify the center node exists.
        center_result = await session.run(
            "MATCH (n {id: $id}) RETURN n",
            id=node_id,
        )
        center_record = await center_result.single()
        if center_record is None:
            return None

        center_node = _node_to_dict(center_record["n"])

        # Fetch outbound + inbound relationships and neighbor nodes.
        if edge_types:
            type_filter = "WHERE type(r) IN $edge_types"
        else:
            type_filter = ""
        query = f"""
            MATCH (n {{id: $id}})-[r]-(m)
            {type_filter}
            RETURN n, r, m
        """
        params: dict[str, Any] = {"id": node_id}
        if edge_types:
            params["edge_types"] = edge_types

        result = await session.run(query, **params)
        records = [record async for record in result]

        seen_nodes: dict[str, dict[str, Any]] = {node_id: center_node}
        edges: list[dict[str, Any]] = []
        seen_edge_ids: set[str] = set()

        for record in records:
            neighbor = _node_to_dict(record["m"])
            if neighbor["id"] not in seen_nodes:
                seen_nodes[neighbor["id"]] = neighbor

            rel = _rel_to_dict(record["r"])
            if rel["id"] not in seen_edge_ids:
                seen_edge_ids.add(rel["id"])
                edges.append(rel)

        nodes = sorted(seen_nodes.values(), key=lambda n: n["id"])
        edges = sorted(edges, key=lambda e: (e["start"], e["end"], e["type"]))

        return {
            "center": node_id,
            "nodes": nodes,
            "edges": edges,
        }
