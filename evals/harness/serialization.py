"""Serialization utilities for Arm C context injection.

Converts an EvalTrace + subgraph into an LLM-friendly summary that the
graph-context arm injects alongside the PatientContext.

Frozen output shape (documented in evals/SPEC.md):
{
  trace_summary: {
    matched_recs: [...],
    preemption_events: [...],
    modifier_events: [...]
  },
  subgraph: {
    nodes: [...],
    edges: [...],
    rendered_prose: "..."
  }
}
"""

from __future__ import annotations

from typing import Any


def serialize_trace_summary(trace: dict[str, Any]) -> dict[str, Any]:
    """Extract a structured summary from an EvalTrace for LLM context.

    Pulls out recommendation emissions, exit conditions, and
    cross-guideline events (preemption/modifier — empty in v0/Phase 1).
    """
    events = trace.get("events", [])

    matched_recs = []
    exit_conditions = []
    preemption_events = []
    modifier_events = []

    for event in events:
        event_type = event.get("type")

        if event_type == "recommendation_emitted":
            matched_recs.append({
                "recommendation_id": event["recommendation_id"],
                "guideline_id": event.get("guideline_id"),
                "status": event["status"],
                "evidence_grade": event["evidence_grade"],
                "reason": event["reason"],
                "offered_strategies": event.get("offered_strategies", []),
                "satisfying_strategy": event.get("satisfying_strategy"),
            })

        elif event_type == "exit_condition_triggered":
            exit_conditions.append({
                "recommendation_id": event["recommendation_id"],
                "exit": event["exit"],
                "rationale": event["rationale"],
                "guideline_id": event.get("guideline_id"),
            })

        elif event_type == "preemption_resolved":
            preemption_events.append({
                "preempted_recommendation_id": event["preempted_recommendation_id"],
                "preempting_recommendation_id": event["preempting_recommendation_id"],
            })

        elif event_type == "cross_guideline_match":
            modifier_events.append({
                "source_guideline_id": event["source_guideline_id"],
                "target_guideline_id": event["target_guideline_id"],
                "match_type": event["match_type"],
            })

    return {
        "matched_recs": matched_recs,
        "exit_conditions": exit_conditions,
        "preemption_events": preemption_events,
        "modifier_events": modifier_events,
    }


def serialize_subgraph(trace: dict[str, Any]) -> dict[str, Any]:
    """Build a subgraph representation from the trace events.

    Extracts nodes and edges that were traversed during evaluation,
    based on trace events (recommendations considered, strategies checked,
    actions checked, eligibility predicates evaluated).
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    events = trace.get("events", [])

    for event in events:
        event_type = event.get("type")

        if event_type == "recommendation_considered":
            rec_id = event["recommendation_id"]
            if rec_id not in seen_node_ids:
                nodes.append({
                    "id": rec_id,
                    "type": "Recommendation",
                    "label": event.get("recommendation_title", rec_id),
                    "evidence_grade": event.get("evidence_grade"),
                    "intent": event.get("intent"),
                })
                seen_node_ids.add(rec_id)

        elif event_type == "guideline_entered":
            gid = event["guideline_id"]
            if gid not in seen_node_ids:
                nodes.append({
                    "id": gid,
                    "type": "Guideline",
                    "label": event.get("guideline_title", gid),
                })
                seen_node_ids.add(gid)

        elif event_type == "strategy_considered":
            sid = event["strategy_id"]
            if sid not in seen_node_ids:
                nodes.append({
                    "id": sid,
                    "type": "Strategy",
                    "label": event.get("strategy_name", sid),
                })
                seen_node_ids.add(sid)
            rec_id = event["recommendation_id"]
            edges.append({
                "source": rec_id,
                "target": sid,
                "type": "OFFERS",
            })

        elif event_type == "action_checked":
            action_id = event["action_node_id"]
            if action_id not in seen_node_ids:
                nodes.append({
                    "id": action_id,
                    "type": event.get("action_entity_type", "Entity"),
                    "label": action_id,
                })
                seen_node_ids.add(action_id)
            edges.append({
                "source": event["strategy_id"],
                "target": action_id,
                "type": "INCLUDES_ACTION",
                "satisfied": event.get("satisfied", False),
            })

    # Build rendered prose: a natural-language summary so the LLM
    # doesn't have to reason over JSON alone.
    rendered_prose = _render_subgraph_prose(trace)

    return {
        "nodes": nodes,
        "edges": edges,
        "rendered_prose": rendered_prose,
    }


def _render_subgraph_prose(trace: dict[str, Any]) -> str:
    """Render a natural-language summary of the evaluation for LLM context."""
    events = trace.get("events", [])
    lines: list[str] = []

    # Collect guideline info
    for event in events:
        if event["type"] == "guideline_entered":
            lines.append(
                f"Guideline evaluated: {event.get('guideline_title', event['guideline_id'])}"
            )

    # Collect exit conditions
    for event in events:
        if event["type"] == "exit_condition_triggered":
            lines.append(
                f"Exit condition triggered: {event['exit']} — {event['rationale']}"
            )

    # Collect recommendation results
    for event in events:
        if event["type"] == "recommendation_emitted":
            rec_id = event["recommendation_id"]
            status = event["status"]
            grade = event["evidence_grade"]
            reason = event["reason"]
            lines.append(
                f"Recommendation {rec_id} (Grade {grade}): status={status}. {reason}"
            )
            strategies = event.get("offered_strategies", [])
            if strategies:
                lines.append(f"  Offered strategies: {', '.join(strategies)}")
            sat = event.get("satisfying_strategy")
            if sat:
                lines.append(f"  Currently satisfied by: {sat}")

    # Collect strategy details
    for event in events:
        if event["type"] == "strategy_resolved":
            sid = event["strategy_id"]
            satisfied = event["satisfied"]
            lines.append(
                f"Strategy {sid}: {'satisfied' if satisfied else 'not satisfied'}"
            )

    # Collect key predicate results
    risk_events = [e for e in events if e["type"] == "risk_score_lookup"]
    for event in risk_events:
        name = event["score_name"]
        resolution = event["resolution"]
        value = event.get("supplied_value") or event.get("computed_value")
        if value is not None:
            lines.append(f"Risk score {name}: {value}% ({resolution})")
        else:
            lines.append(f"Risk score {name}: {resolution}")

    return "\n".join(lines)


def serialize_convergence_summary(
    trace: dict[str, Any], subgraph: dict[str, Any]
) -> dict[str, Any]:
    """Identify shared clinical entities targeted by 2+ guidelines.

    Walks action_checked events in the trace, groups by action_node_id,
    and surfaces entities where strategies from multiple guidelines converge
    on the same Medication/Condition/Observation/Procedure node.

    Args:
        trace: The full EvalTrace dict.
        subgraph: The already-serialized subgraph (from serialize_subgraph).

    Returns:
        A convergence_summary dict with shared_actions and convergence_prose.
    """
    events = trace.get("events", [])

    # Build lookup: node_id -> label from the subgraph
    node_labels: dict[str, str] = {}
    node_types: dict[str, str] = {}
    for node in subgraph.get("nodes", []):
        node_labels[node["id"]] = node.get("label", node["id"])
        node_types[node["id"]] = node.get("type", "Entity")

    # Build lookup: rec_id -> emitted rec details
    rec_details: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") == "recommendation_emitted":
            rec_details[event["recommendation_id"]] = {
                "rec_id": event["recommendation_id"],
                "guideline_id": event.get("guideline_id"),
                "evidence_grade": event["evidence_grade"],
                "status": event["status"],
            }

    # Group action_checked events by action_node_id, collecting
    # which guideline/rec/strategy chains target each entity.
    action_sources: dict[str, list[dict[str, str]]] = {}
    seen_action_guideline_rec: set[tuple[str, str, str]] = set()

    for event in events:
        if event.get("type") != "action_checked":
            continue
        action_id = event["action_node_id"]
        guideline_id = event.get("guideline_id", "")
        rec_id = event["recommendation_id"]
        strategy_id = event["strategy_id"]

        # Deduplicate: same action from same guideline+rec only counted once
        dedup_key = (action_id, guideline_id, rec_id)
        if dedup_key in seen_action_guideline_rec:
            continue
        seen_action_guideline_rec.add(dedup_key)

        if action_id not in action_sources:
            action_sources[action_id] = []
        action_sources[action_id].append({
            "guideline_id": guideline_id,
            "rec_id": rec_id,
            "strategy_id": strategy_id,
        })

    # Filter to entities with 2+ distinct guidelines
    shared_actions: list[dict[str, Any]] = []
    for action_id, sources in sorted(action_sources.items()):
        guideline_ids = {s["guideline_id"] for s in sources}
        if len(guideline_ids) < 2:
            continue

        recommended_by = []
        for source in sorted(sources, key=lambda s: (s["guideline_id"], s["rec_id"])):
            rec = rec_details.get(source["rec_id"], {})
            # Derive a short guideline label from the guideline_id
            guideline_label = _guideline_label(source["guideline_id"])
            recommended_by.append({
                "rec_id": source["rec_id"],
                "guideline": guideline_label,
                "evidence_grade": rec.get("evidence_grade", ""),
                "status": rec.get("status", ""),
                "via_strategy": source["strategy_id"],
            })

        shared_actions.append({
            "entity_id": action_id,
            "entity_label": node_labels.get(action_id, action_id),
            "entity_type": node_types.get(action_id, "Entity"),
            "recommended_by": recommended_by,
            "guideline_count": len(guideline_ids),
            "convergence_type": "reinforcing",
        })

    convergence_prose = _render_convergence_prose(shared_actions)

    return {
        "shared_actions": shared_actions,
        "convergence_prose": convergence_prose,
    }


def _guideline_label(guideline_id: str) -> str:
    """Derive a human-readable short label from a guideline id."""
    labels: dict[str, str] = {
        "guideline:uspstf-statin-2022": "USPSTF 2022 Statin",
        "guideline:acc-aha-cholesterol-2018": "ACC/AHA 2018 Cholesterol",
        "guideline:kdigo-ckd-2024": "KDIGO 2024 CKD",
    }
    return labels.get(guideline_id, guideline_id)


def _render_convergence_prose(shared_actions: list[dict[str, Any]]) -> str:
    """Render a natural-language paragraph summarising cross-guideline convergence."""
    if not shared_actions:
        return ""

    lines: list[str] = []
    # Group shared actions by entity type for readability
    by_type: dict[str, list[dict[str, Any]]] = {}
    for action in shared_actions:
        etype = action["entity_type"]
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(action)

    total = len(shared_actions)
    guideline_names = set()
    for action in shared_actions:
        for rb in action["recommended_by"]:
            guideline_names.add(rb["guideline"])

    lines.append(
        f"{total} clinical entit{'y' if total == 1 else 'ies'} "
        f"{'is' if total == 1 else 'are'} independently recommended by "
        f"{len(guideline_names)} guidelines ({', '.join(sorted(guideline_names))})."
    )

    for etype, actions in sorted(by_type.items()):
        entity_labels = [a["entity_label"] for a in actions]
        if len(entity_labels) <= 3:
            label_str = ", ".join(entity_labels)
        else:
            label_str = f"{', '.join(entity_labels[:3])}, and {len(entity_labels) - 3} more"

        # Collect the unique guideline+grade combos for this type
        grade_parts: list[str] = []
        seen_guidelines: set[str] = set()
        for action in actions:
            for rb in action["recommended_by"]:
                key = rb["guideline"]
                if key not in seen_guidelines:
                    seen_guidelines.add(key)
                    grade_parts.append(f"{rb['guideline']} (Grade {rb['evidence_grade']})")

        lines.append(
            f"{etype} convergence: {label_str}. "
            f"Recommended by: {'; '.join(sorted(grade_parts))}."
        )

    lines.append(
        "Where multiple guidelines converge on the same therapeutic action, "
        "this represents independent clinical agreement."
    )

    return " ".join(lines)


def build_arm_c_context(trace: dict[str, Any]) -> dict[str, Any]:
    """Build the full Arm C context object from an EvalTrace.

    This is the frozen output shape injected into the graph-context arm's
    prompt alongside the PatientContext.
    """
    subgraph = serialize_subgraph(trace)
    return {
        "trace_summary": serialize_trace_summary(trace),
        "subgraph": subgraph,
        "convergence_summary": serialize_convergence_summary(trace, subgraph),
    }
