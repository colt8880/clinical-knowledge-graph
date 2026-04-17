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


def build_arm_c_context(trace: dict[str, Any]) -> dict[str, Any]:
    """Build the full Arm C context object from an EvalTrace.

    This is the frozen output shape injected into the graph-context arm's
    prompt alongside the PatientContext.
    """
    return {
        "trace_summary": serialize_trace_summary(trace),
        "subgraph": serialize_subgraph(trace),
    }
