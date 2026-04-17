"""Graph snapshot: an in-memory representation of the knowledge graph
that the evaluator consumes.

The evaluator is pure — no I/O during evaluate(). This module handles
the Neo4j loading that happens *before* evaluate() is called.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.db import get_driver


@dataclass(frozen=True)
class CodeRef:
    system: str
    code: str


@dataclass
class ClinicalEntity:
    id: str
    label: str  # Neo4j label: Condition, Observation, Medication, Procedure
    display_name: str
    codes: list[CodeRef] = field(default_factory=list)


@dataclass
class ActionEdge:
    """An INCLUDES_ACTION edge from a Strategy to a clinical entity node."""
    action_node_id: str
    action_entity_type: str  # Medication, Procedure, Observation
    cadence: str | None = None
    lookback: str | None = None
    priority: str | None = None
    intent: str | None = None


@dataclass
class StrategyNode:
    id: str
    name: str
    actions: list[ActionEdge] = field(default_factory=list)


@dataclass
class RecommendationNode:
    id: str
    title: str
    evidence_grade: str
    intent: str
    trigger: str
    structured_eligibility: dict[str, Any] | None = None
    strategy_ids: list[str] = field(default_factory=list)


@dataclass
class GraphSnapshot:
    guideline_id: str
    guideline_title: str
    recommendations: list[RecommendationNode] = field(default_factory=list)
    entities: dict[str, ClinicalEntity] = field(default_factory=dict)
    strategies: dict[str, StrategyNode] = field(default_factory=dict)


def _extract_codes(props: dict[str, Any]) -> list[CodeRef]:
    """Pull code-list properties into CodeRef objects."""
    code_systems = {
        "snomed_codes": "snomed",
        "icd10_codes": "icd10",
        "loinc_codes": "loinc",
        "rxnorm_codes": "rxnorm",
        "cpt_codes": "cpt",
    }
    codes: list[CodeRef] = []
    for prop, system in code_systems.items():
        for code in props.get(prop, []):
            codes.append(CodeRef(system=system, code=code))
    return codes


async def load_all_guidelines() -> list[GraphSnapshot]:
    """Load all guideline subgraphs from Neo4j.

    Returns a list of GraphSnapshots, one per Guideline node in the database.
    The caller (engine.evaluate) sorts by guideline_id for deterministic
    traversal order. Each snapshot includes the guideline's recommendations,
    strategies, and the full set of shared clinical entities.
    """
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(
            "MATCH (g:Guideline) RETURN g.id AS gid ORDER BY g.id"
        )
        records = [r async for r in result]
        guideline_ids = [r["gid"] for r in records]

    snapshots = []
    for gid in guideline_ids:
        snapshot = await load_graph(gid)
        snapshots.append(snapshot)
    return snapshots


async def load_graph(guideline_id: str = "guideline:uspstf-statin-2022") -> GraphSnapshot:
    """Load a guideline and its full subgraph from Neo4j into a GraphSnapshot.

    For v0 this is the only guideline. The snapshot includes:
    - Guideline metadata
    - Recommendation nodes (ordered by id for determinism)
    - Strategy links per recommendation
    - Clinical entity nodes with their code lists
    """
    import json

    driver = get_driver()
    async with driver.session() as session:
        # Load guideline
        result = await session.run(
            "MATCH (g:Guideline {id: $id}) RETURN g", id=guideline_id
        )
        g_record = await result.single()
        if g_record is None:
            raise ValueError(f"Guideline {guideline_id} not found in graph")
        g_props = dict(g_record["g"].items())
        guideline_title = g_props.get("title") or g_props.get("publisher") or guideline_id

        # Load recommendations linked to guideline, ordered by id
        result = await session.run(
            """
            MATCH (r:Recommendation)-[:FROM_GUIDELINE]->(g:Guideline {id: $id})
            RETURN r ORDER BY r.id
            """,
            id=guideline_id,
        )
        rec_records = [record async for record in result]

        recommendations: list[RecommendationNode] = []
        for rec_record in rec_records:
            r_props = dict(rec_record["r"].items())
            se_raw = r_props.get("structured_eligibility")
            se = json.loads(se_raw) if se_raw else None

            # Fetch strategy ids for this rec
            strat_result = await session.run(
                """
                MATCH (r:Recommendation {id: $rid})-[:OFFERS_STRATEGY]->(s:Strategy)
                RETURN s.id AS sid ORDER BY s.id
                """,
                rid=r_props["id"],
            )
            strat_records = [s async for s in strat_result]
            strategy_ids = [s["sid"] for s in strat_records]

            recommendations.append(
                RecommendationNode(
                    id=r_props["id"],
                    title=r_props.get("title", ""),
                    evidence_grade=r_props.get("evidence_grade", ""),
                    intent=r_props.get("intent", ""),
                    trigger=r_props.get("trigger", ""),
                    structured_eligibility=se,
                    strategy_ids=strategy_ids,
                )
            )

        # Load all clinical entity nodes
        entities: dict[str, ClinicalEntity] = {}
        for label in ("Condition", "Observation", "Medication", "Procedure"):
            result = await session.run(f"MATCH (n:{label}) RETURN n")
            records = [record async for record in result]
            for record in records:
                n_props = dict(record["n"].items())
                node_id = n_props["id"]
                entities[node_id] = ClinicalEntity(
                    id=node_id,
                    label=label,
                    display_name=n_props.get("display_name", ""),
                    codes=_extract_codes(n_props),
                )

        # Load Strategy nodes with their INCLUDES_ACTION edges.
        # Strategies are ordered by id for determinism.
        strategies: dict[str, StrategyNode] = {}
        strat_result = await session.run(
            """
            MATCH (s:Strategy)
            RETURN s ORDER BY s.id
            """
        )
        strat_records = [record async for record in strat_result]
        for strat_record in strat_records:
            s_props = dict(strat_record["s"].items())
            sid = s_props["id"]

            # Load INCLUDES_ACTION edges for this strategy, ordered by target id
            action_result = await session.run(
                """
                MATCH (s:Strategy {id: $sid})-[e:INCLUDES_ACTION]->(t)
                RETURN e, t, labels(t) AS target_labels
                ORDER BY t.id
                """,
                sid=sid,
            )
            action_records = [a async for a in action_result]
            actions: list[ActionEdge] = []
            for a_rec in action_records:
                e_props = dict(a_rec["e"].items())
                t_props = dict(a_rec["t"].items())
                target_labels = a_rec["target_labels"]
                # Pick the clinical entity label (Medication, Procedure, etc.)
                entity_type = next(
                    (l for l in target_labels if l in ("Medication", "Procedure", "Observation")),
                    "Unknown",
                )
                actions.append(ActionEdge(
                    action_node_id=t_props["id"],
                    action_entity_type=entity_type,
                    cadence=e_props.get("cadence"),
                    lookback=e_props.get("lookback"),
                    priority=e_props.get("priority"),
                    intent=e_props.get("intent"),
                ))

            strategies[sid] = StrategyNode(
                id=sid,
                name=s_props.get("name", ""),
                actions=actions,
            )

        return GraphSnapshot(
            guideline_id=guideline_id,
            guideline_title=guideline_title,
            recommendations=recommendations,
            entities=entities,
            strategies=strategies,
        )
