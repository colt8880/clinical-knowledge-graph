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
  },
  convergence_summary: {
    shared_actions: [...],
    convergence_prose: "..."
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
                "preempted_guideline": _guideline_label(event.get("guideline_id", "")),
                "preempting_guideline": _guideline_label(
                    _rec_to_guideline(event["preempting_recommendation_id"], events)
                ),
            })

        elif event_type == "cross_guideline_match":
            modifier_events.append({
                "source_guideline_id": event["source_guideline_id"],
                "target_guideline_id": event["target_guideline_id"],
                "match_type": event.get("nature", "unknown"),
                "note": event.get("note", ""),
            })

    return {
        "matched_recs": matched_recs,
        "exit_conditions": exit_conditions,
        "preemption_events": preemption_events,
        "modifier_events": modifier_events,
        "preemption_prose": _render_preemption_prose(preemption_events),
        "modifier_prose": _render_modifier_prose(modifier_events),
    }


def _rec_to_guideline(rec_id: str, events: list[dict[str, Any]]) -> str:
    """Find the guideline_id for a recommendation from trace events."""
    for event in events:
        if (
            event.get("type") in ("recommendation_emitted", "recommendation_considered")
            and event.get("recommendation_id") == rec_id
        ):
            return event.get("guideline_id", "")
    return ""


def _render_preemption_prose(preemption_events: list[dict[str, Any]]) -> str:
    """Render preemption events as prose sentences."""
    if not preemption_events:
        return ""
    lines = []
    for pe in preemption_events:
        preempted = pe.get("preempted_guideline") or pe["preempted_recommendation_id"]
        preempting = pe.get("preempting_guideline") or pe["preempting_recommendation_id"]
        lines.append(
            f"{preempting} preempts {preempted} for this patient — "
            f"follow {preempting} recommendation instead."
        )
    return " ".join(lines)


def _render_modifier_prose(modifier_events: list[dict[str, Any]]) -> str:
    """Render modifier events as prose sentences."""
    if not modifier_events:
        return ""
    lines = []
    for me in modifier_events:
        source = _guideline_label(me["source_guideline_id"])
        target = _guideline_label(me["target_guideline_id"])
        match_type = me["match_type"].replace("_", " ")
        note = me.get("note", "")
        base = f"{source} modifies {target} ({match_type})"
        if note:
            lines.append(f"{base} — {note}.")
        else:
            lines.append(f"{base}.")
    return " ".join(lines)


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

    v2: Groups convergent entities by therapeutic class (derived from the
    strategy label) instead of listing each medication individually. This
    reduces noise (7 statins × 3 guidelines = 21 rows → 1 row per class).

    Args:
        trace: The full EvalTrace dict.
        subgraph: The already-serialized subgraph (from serialize_subgraph).

    Returns:
        A convergence_summary dict with shared_actions, grouped_convergence,
        and convergence_prose.
    """
    events = trace.get("events", [])

    # Build lookup: node_id -> label from the subgraph
    node_labels: dict[str, str] = {}
    node_types: dict[str, str] = {}
    for node in subgraph.get("nodes", []):
        node_labels[node["id"]] = node.get("label", node["id"])
        node_types[node["id"]] = node.get("type", "Entity")

    # Build lookup: strategy_id -> strategy_name from trace events
    strategy_names: dict[str, str] = {}
    for event in events:
        if event.get("type") == "strategy_considered":
            strategy_names[event["strategy_id"]] = event.get("strategy_name", event["strategy_id"])

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

    # v2: Group shared actions by therapeutic class (strategy label)
    grouped = _group_by_therapeutic_class(shared_actions, strategy_names)
    convergence_prose = _render_convergence_prose_v2(grouped)

    return {
        "shared_actions": shared_actions,
        "grouped_convergence": grouped,
        "convergence_prose": convergence_prose,
    }


def _derive_therapeutic_class(strategy_name: str, entity_type: str) -> str:
    """Derive a therapeutic class label from a strategy name.

    Uses the strategy name as the primary signal for grouping.
    Falls back to entity_type if no meaningful class can be derived.
    """
    name_lower = strategy_name.lower()
    # Extract intensity + therapy type from strategy names
    if "statin" in name_lower:
        if "high" in name_lower:
            return "High-intensity statin therapy"
        elif "moderate" in name_lower:
            return "Moderate-intensity statin therapy"
        elif "low" in name_lower:
            return "Low-intensity statin therapy"
        else:
            return "Statin therapy"
    return strategy_name or entity_type


def _group_by_therapeutic_class(
    shared_actions: list[dict[str, Any]],
    strategy_names: dict[str, str],
) -> list[dict[str, Any]]:
    """Group convergent shared_actions by therapeutic class.

    Instead of one row per medication, produces one row per therapeutic
    class (e.g. "Moderate-intensity statin therapy") with all the
    individual medications listed as members.
    """
    # Group: (therapeutic_class, entity_type) -> list of shared_actions
    class_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for action in shared_actions:
        # Collect unique strategy names across all recommending guidelines
        strat_ids = {rb["via_strategy"] for rb in action["recommended_by"]}
        strat_name_set = {strategy_names.get(sid, sid) for sid in strat_ids}

        # Use the most common strategy name for class derivation
        # (they typically share a class — "moderate-intensity statin therapy")
        representative_name = sorted(strat_name_set)[0] if strat_name_set else ""
        therapeutic_class = _derive_therapeutic_class(
            representative_name, action["entity_type"]
        )

        key = (therapeutic_class, action["entity_type"])
        if key not in class_groups:
            class_groups[key] = []
        class_groups[key].append(action)

    grouped: list[dict[str, Any]] = []
    for (tc, etype), actions in sorted(class_groups.items()):
        # Collect unique guideline recommendations across all members
        guidelines_seen: dict[str, dict[str, str]] = {}
        for action in actions:
            for rb in action["recommended_by"]:
                gl_key = rb["guideline"]
                if gl_key not in guidelines_seen:
                    guidelines_seen[gl_key] = {
                        "guideline": rb["guideline"],
                        "evidence_grade": rb["evidence_grade"],
                        "via_strategy": rb["via_strategy"],
                    }

        # Collect strategy-level intensity context
        intensity_details = []
        seen_strats: set[str] = set()
        for action in actions:
            for rb in action["recommended_by"]:
                sid = rb["via_strategy"]
                if sid not in seen_strats:
                    seen_strats.add(sid)
                    sname = strategy_names.get(sid, sid)
                    intensity_details.append({
                        "strategy_id": sid,
                        "strategy_name": sname,
                        "guideline": rb["guideline"],
                    })

        member_labels = sorted(a["entity_label"] for a in actions)
        grouped.append({
            "therapeutic_class": tc,
            "entity_type": etype,
            "members": member_labels,
            "member_count": len(member_labels),
            "recommended_by": sorted(
                guidelines_seen.values(), key=lambda g: g["guideline"]
            ),
            "guideline_count": len(guidelines_seen),
            "intensity_details": sorted(
                intensity_details, key=lambda d: d["guideline"]
            ),
        })

    return grouped


def _guideline_label(guideline_id: str) -> str:
    """Derive a human-readable short label from a guideline id."""
    labels: dict[str, str] = {
        "guideline:uspstf-statin-2022": "USPSTF 2022 Statin",
        "guideline:acc-aha-cholesterol-2018": "ACC/AHA 2018 Cholesterol",
        "guideline:kdigo-ckd-2024": "KDIGO 2024 CKD",
    }
    return labels.get(guideline_id, guideline_id)


def _render_convergence_prose_v2(grouped: list[dict[str, Any]]) -> str:
    """Render grouped convergence as concise prose.

    v2: One line per therapeutic class instead of one per medication.
    Includes intensity context from strategy labels.
    """
    if not grouped:
        return ""

    lines: list[str] = []

    # Collect all guideline names across groups
    all_guidelines: set[str] = set()
    for group in grouped:
        for rb in group["recommended_by"]:
            all_guidelines.add(rb["guideline"])

    lines.append(
        f"{len(grouped)} therapeutic convergence point{'s' if len(grouped) != 1 else ''} "
        f"across {len(all_guidelines)} guidelines "
        f"({', '.join(sorted(all_guidelines))})."
    )

    for group in grouped:
        tc = group["therapeutic_class"]
        members = group["members"]
        recs = group["recommended_by"]

        # Build guideline attribution: "USPSTF (Grade C), ACC/AHA (COR I, LOE A)"
        gl_parts = [
            f"{rb['guideline']} (Grade {rb['evidence_grade']})"
            for rb in recs
        ]

        # Member list
        if len(members) <= 5:
            member_str = ", ".join(members)
        else:
            member_str = f"{', '.join(members[:4])}, and {len(members) - 4} more"

        lines.append(
            f"{tc}: recommended by {'; '.join(gl_parts)}. "
            f"Any of: {member_str}."
        )

        # Intensity details if strategies differ across guidelines
        if len(group["intensity_details"]) > 1:
            unique_names = {d["strategy_name"] for d in group["intensity_details"]}
            if len(unique_names) > 1:
                intensity_parts = [
                    f"{d['guideline']}: {d['strategy_name']}"
                    for d in group["intensity_details"]
                ]
                lines.append(f"  Intensity context: {'; '.join(intensity_parts)}.")

    return "\n".join(lines)


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
