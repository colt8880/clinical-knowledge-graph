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

    # Build strategy_names lookup from strategy_considered events
    strategy_names: dict[str, str] = {}
    # Build rec_intents lookup from recommendation_considered events
    rec_intents: dict[str, str] = {}

    for event in events:
        event_type = event.get("type")
        if event_type == "strategy_considered":
            strategy_names[event["strategy_id"]] = event.get(
                "strategy_name", event["strategy_id"]
            )
        elif event_type == "recommendation_considered":
            rec_intents[event["recommendation_id"]] = event.get("intent", "")

    return {
        "matched_recs": matched_recs,
        "exit_conditions": exit_conditions,
        "preemption_events": preemption_events,
        "modifier_events": modifier_events,
        "preemption_prose": _render_preemption_prose(preemption_events),
        "modifier_prose": _render_modifier_prose(modifier_events),
        "strategy_names": strategy_names,
        "rec_intents": rec_intents,
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
        "guideline:ada-diabetes-2024": "ADA 2024 Diabetes",
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


def serialize_satisfied_strategies(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract strategies with status up_to_date from the trace.

    These represent therapies the patient is already receiving that satisfy
    guideline recommendations. Surfacing them explicitly tells the LLM to
    recommend continuation rather than staying silent on satisfied recs.
    """
    events = trace.get("events", [])

    # Build lookup: strategy_id -> strategy_name
    strategy_names: dict[str, str] = {}
    for event in events:
        if event.get("type") == "strategy_considered":
            strategy_names[event["strategy_id"]] = event.get(
                "strategy_name", event["strategy_id"]
            )

    # Build lookup: strategy_id -> satisfied actions (from action_checked)
    strategy_actions: dict[str, list[str]] = {}
    for event in events:
        if event.get("type") == "action_checked" and event.get("satisfied"):
            sid = event["strategy_id"]
            if sid not in strategy_actions:
                strategy_actions[sid] = []
            strategy_actions[sid].append(event["action_node_id"])

    # Collect recs with status up_to_date and their satisfying strategy
    satisfied: list[dict[str, Any]] = []
    for event in events:
        if (
            event.get("type") == "recommendation_emitted"
            and event.get("status") == "up_to_date"
        ):
            sat_strategy = event.get("satisfying_strategy")
            if not sat_strategy:
                continue
            guideline_id = event.get("guideline_id", "")
            satisfied.append({
                "recommendation_id": event["recommendation_id"],
                "guideline_id": guideline_id,
                "guideline_label": _guideline_label(guideline_id),
                "evidence_grade": event["evidence_grade"],
                "strategy_id": sat_strategy,
                "strategy_name": strategy_names.get(sat_strategy, sat_strategy),
                "satisfied_by": strategy_actions.get(sat_strategy, []),
            })

    return satisfied


def serialize_negative_evidence(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract guidelines that were evaluated but produced no actionable recs.

    Two cases:
    1. A guideline was entered but zero recommendation_emitted events exist
       for it (all recs exited or were ineligible).
    2. A guideline emitted recs but all were preempted by another guideline.

    Returns a list of {"guideline_id", "guideline_label", "reason"} dicts.
    """
    events = trace.get("events", [])

    # Track guideline enter/exit pairs
    guideline_ids_entered: list[str] = []
    for event in events:
        if event.get("type") == "guideline_entered":
            guideline_ids_entered.append(event["guideline_id"])

    # Collect recs emitted per guideline
    recs_by_guideline: dict[str, list[str]] = {}
    for event in events:
        if event.get("type") == "recommendation_emitted":
            gid = event.get("guideline_id", "")
            if gid not in recs_by_guideline:
                recs_by_guideline[gid] = []
            recs_by_guideline[gid].append(event["recommendation_id"])

    # Collect exit reasons per guideline
    exits_by_guideline: dict[str, list[str]] = {}
    for event in events:
        if event.get("type") == "exit_condition_triggered":
            gid = event.get("guideline_id", "")
            if gid not in exits_by_guideline:
                exits_by_guideline[gid] = []
            exits_by_guideline[gid].append(
                f"{event['exit']}: {event['rationale']}"
            )

    # Collect preempted rec IDs and the preempting guideline
    preempted_recs: dict[str, str] = {}  # rec_id -> preempting_rec_id
    for event in events:
        if event.get("type") == "preemption_resolved":
            preempted_recs[event["preempted_recommendation_id"]] = (
                event["preempting_recommendation_id"]
            )

    result: list[dict[str, Any]] = []

    for gid in guideline_ids_entered:
        emitted = recs_by_guideline.get(gid, [])
        exits = exits_by_guideline.get(gid, [])

        if not emitted:
            # Case 1: guideline entered, zero recs emitted
            if exits:
                reason = "; ".join(exits)
            else:
                reason = "No eligible recommendations"
            result.append({
                "guideline_id": gid,
                "guideline_label": _guideline_label(gid),
                "reason": reason,
            })
        else:
            # Case 2: all emitted recs were preempted
            all_preempted = all(rid in preempted_recs for rid in emitted)
            if all_preempted:
                # Find the preempting guideline(s)
                preempting_rec_ids = {preempted_recs[rid] for rid in emitted}
                # Resolve preempting rec -> guideline
                preempting_guidelines = set()
                for event in events:
                    if (
                        event.get("type") == "recommendation_emitted"
                        and event.get("recommendation_id") in preempting_rec_ids
                    ):
                        preempting_guidelines.add(
                            _guideline_label(event.get("guideline_id", ""))
                        )
                if preempting_guidelines:
                    reason = (
                        f"All recommendations preempted by "
                        f"{', '.join(sorted(preempting_guidelines))}"
                    )
                else:
                    reason = "All recommendations preempted"
                result.append({
                    "guideline_id": gid,
                    "guideline_label": _guideline_label(gid),
                    "reason": reason,
                })

    return result


def classify_guideline_relevance(trace: dict[str, Any]) -> dict[str, set[str]]:
    """Classify each guideline in the trace as relevant or irrelevant.

    A guideline is **relevant** if any of these hold:
    1. It has a recommendation_emitted event with status != 'not_applicable'.
    2. It has an exit_condition_triggered event (clinically meaningful exit).
    3. It appears in a cross_guideline_match event as source or target.

    A guideline is **irrelevant** if it was entered but none of the above
    conditions hold — all its recs were not_applicable, no exit, no cross-match.

    Returns:
        {"relevant": set of guideline_ids, "irrelevant": set of guideline_ids}
    """
    events = trace.get("events", [])

    entered: set[str] = set()
    relevant: set[str] = set()

    for event in events:
        event_type = event.get("type")
        gid = event.get("guideline_id", "")

        if event_type == "guideline_entered" and gid:
            entered.add(gid)

        elif event_type == "recommendation_emitted" and gid:
            if event.get("status") != "not_applicable":
                relevant.add(gid)

        elif event_type == "exit_condition_triggered" and gid:
            relevant.add(gid)

        elif event_type == "cross_guideline_match":
            source = event.get("source_guideline_id", "")
            target = event.get("target_guideline_id", "")
            if source:
                relevant.add(source)
            if target:
                relevant.add(target)

    irrelevant = entered - relevant

    return {"relevant": relevant, "irrelevant": irrelevant}


def _filter_trace_by_relevance(
    trace: dict[str, Any], irrelevant_ids: set[str]
) -> dict[str, Any]:
    """Return a new trace with events from irrelevant guidelines removed.

    Preserves:
    - Events with no guideline_id (evaluation_started, evaluation_completed).
    - Cross-guideline interaction events (preemption_resolved, cross_guideline_match)
      even if they reference an irrelevant guideline.
    """
    if not irrelevant_ids:
        return trace

    # Event types that are always preserved regardless of guideline_id
    always_keep = {
        "evaluation_started",
        "evaluation_completed",
        "preemption_resolved",
        "cross_guideline_match",
    }

    filtered_events = []
    for event in trace.get("events", []):
        event_type = event.get("type", "")
        gid = event.get("guideline_id", "")

        if event_type in always_keep:
            filtered_events.append(event)
        elif gid and gid in irrelevant_ids:
            continue  # Drop events from irrelevant guidelines
        else:
            filtered_events.append(event)

    return {**trace, "events": filtered_events}


def _count_relevant_guidelines(trace: dict[str, Any]) -> int:
    """Count distinct relevant guidelines in a (scoped) trace.

    Counts guideline_entered events, which survive scoping only for
    relevant guidelines.
    """
    return sum(
        1
        for event in trace.get("events", [])
        if event.get("type") == "guideline_entered"
    )


# Compression threshold: >= 3 relevant guidelines triggers compressed format.
COMPRESSION_THRESHOLD = 3


def _render_compressed_prose(trace: dict[str, Any]) -> str:
    """Render a one-line-per-guideline prose summary for compressed mode.

    Replaces the multi-line trace walk with a compact summary:
    one sentence per guideline with rec count, status, and key detail.
    """
    events = trace.get("events", [])

    # Gather per-guideline info
    guideline_info: dict[str, dict[str, Any]] = {}
    for event in events:
        gid = event.get("guideline_id", "")
        etype = event.get("type", "")

        if etype == "guideline_entered" and gid:
            guideline_info.setdefault(gid, {
                "title": event.get("guideline_title", gid),
                "recs": [],
                "exits": [],
                "risk_scores": [],
            })

        elif etype == "recommendation_emitted" and gid:
            info = guideline_info.get(gid)
            if info:
                info["recs"].append({
                    "status": event.get("status", ""),
                    "grade": event.get("evidence_grade", ""),
                    "reason": event.get("reason", ""),
                })

        elif etype == "exit_condition_triggered" and gid:
            info = guideline_info.get(gid)
            if info:
                info["exits"].append(event.get("exit", ""))

        elif etype == "risk_score_lookup" and gid:
            info = guideline_info.get(gid)
            if info:
                value = event.get("supplied_value") or event.get("computed_value")
                if value is not None:
                    info["risk_scores"].append(
                        f"{event['score_name']} {value}%"
                    )

    lines: list[str] = []
    for gid, info in guideline_info.items():
        title = info["title"]
        recs = info["recs"]
        exits = info["exits"]

        if exits and not recs:
            lines.append(f"{title}: exited ({', '.join(exits)}).")
            continue

        # Count by status
        indicated = [r for r in recs if r["status"] in ("due", "indicated")]
        up_to_date = [r for r in recs if r["status"] == "up_to_date"]

        parts: list[str] = []
        if indicated:
            grades = ", ".join(f"Grade {r['grade']}" for r in indicated)
            parts.append(f"{len(indicated)} rec{'s' if len(indicated) != 1 else ''} indicated ({grades})")
        if up_to_date:
            parts.append(f"{len(up_to_date)} satisfied")

        risk_str = ""
        if info["risk_scores"]:
            risk_str = f", {', '.join(info['risk_scores'])}"

        lines.append(f"{title}: {', '.join(parts)}{risk_str}.")

    return "\n".join(lines)


INTENT_PRIORITY: dict[str, int] = {
    "secondary_prevention": 0,
    "primary_prevention": 1,
    "treatment": 2,
    "monitoring": 3,
}

EVIDENCE_GRADE_SORT: dict[str, int] = {
    "COR I, LOE A": 0,
    "A": 1,
    "1A": 2,
    "B": 3,
    "1B": 4,
    "COR I, LOE B-R": 5,
    "COR IIa, LOE B-R": 6,
    "C": 7,
    "1C": 8,
    "2A": 9,
    "2B": 10,
    "2C": 11,
}


def render_compressed_matched_recs(
    trace_summary: dict[str, Any],
) -> str:
    """Render matched recs as a priority-ordered markdown table.

    Fix 1 (F59): Key Action column shows strategy name instead of reason.
    Fix 2 (F59): Recs sorted by clinical priority with explicit # column.
    """
    recs = trace_summary.get("matched_recs", [])
    if not recs:
        return "No matched recommendations."

    strategy_names = trace_summary.get("strategy_names", {})
    rec_intents = trace_summary.get("rec_intents", {})
    preempted_rec_ids = {
        pe["preempted_recommendation_id"]
        for pe in trace_summary.get("preemption_events", [])
    }

    # Sort by (is_preempted ASC, intent_priority ASC, evidence_grade_sort ASC)
    def sort_key(rec: dict[str, Any]) -> tuple[int, int, int]:
        rec_id = rec["recommendation_id"]
        is_preempted = 1 if rec_id in preempted_rec_ids else 0
        intent = rec_intents.get(rec_id, "")
        intent_order = INTENT_PRIORITY.get(intent, 99)
        grade = rec.get("evidence_grade", "")
        grade_order = EVIDENCE_GRADE_SORT.get(grade, 50)
        return (is_preempted, intent_order, grade_order)

    sorted_recs = sorted(recs, key=sort_key)

    lines = [
        "| # | Guideline | Rec | Grade | Status | Key Action |",
        "|---|-----------|-----|-------|--------|------------|",
    ]
    for i, rec in enumerate(sorted_recs, 1):
        guideline = _guideline_label(rec.get("guideline_id", ""))
        rec_id = rec["recommendation_id"]
        short_id = rec_id.replace("rec:", "") if rec_id.startswith("rec:") else rec_id
        grade = rec.get("evidence_grade", "")

        if rec_id in preempted_rec_ids:
            status = "preempted"
        else:
            status = rec.get("status", "")

        # Key Action: strategy name (not evaluator reason)
        key_action = ""
        offered = rec.get("offered_strategies", [])
        if offered:
            key_action = strategy_names.get(offered[0], "")
        if not key_action:
            reason = rec.get("reason", "")
            key_action = reason[:47] + "..." if len(reason) > 50 else reason

        lines.append(
            f"| {i} | {guideline} | {short_id} | {grade} | {status} | {key_action} |"
        )

    return "\n".join(lines)


def render_compact_strategy_summary(trace: dict[str, Any]) -> str:
    """Render a compact strategy summary for compressed mode (F59).

    One line per indicated (non-preempted) rec showing strategy name and
    top 3 action options. Adds ~3-5 lines vs ~20+ in uncompressed format.
    """
    events = trace.get("events", [])

    # Build lookups
    strategy_names: dict[str, str] = {}
    rec_intents: dict[str, str] = {}
    for event in events:
        etype = event.get("type")
        if etype == "strategy_considered":
            strategy_names[event["strategy_id"]] = event.get(
                "strategy_name", event["strategy_id"]
            )
        elif etype == "recommendation_considered":
            rec_intents[event["recommendation_id"]] = event.get("intent", "")

    # Collect preempted rec IDs
    preempted_rec_ids: set[str] = set()
    for event in events:
        if event.get("type") == "preemption_resolved":
            preempted_rec_ids.add(event["preempted_recommendation_id"])

    # Collect actions per strategy (deduplicated, preserving order)
    strategy_actions: dict[str, list[str]] = {}
    for event in events:
        if event.get("type") == "action_checked":
            sid = event["strategy_id"]
            if sid not in strategy_actions:
                strategy_actions[sid] = []
            action_id = event["action_node_id"]
            if action_id not in strategy_actions[sid]:
                strategy_actions[sid].append(action_id)

    # Collect indicated recs (not not_applicable, not preempted)
    indicated_recs: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") == "recommendation_emitted":
            rec_id = event["recommendation_id"]
            if event.get("status") == "not_applicable":
                continue
            if rec_id in preempted_rec_ids:
                continue
            indicated_recs.append(event)

    if not indicated_recs:
        return ""

    # Sort by priority (same order as the recs table)
    def sort_key(rec_event: dict[str, Any]) -> tuple[int, int]:
        intent = rec_intents.get(rec_event["recommendation_id"], "")
        intent_order = INTENT_PRIORITY.get(intent, 99)
        grade = rec_event.get("evidence_grade", "")
        grade_order = EVIDENCE_GRADE_SORT.get(grade, 50)
        return (intent_order, grade_order)

    indicated_recs.sort(key=sort_key)

    lines: list[str] = ["### Key Therapies", ""]
    for i, rec in enumerate(indicated_recs, 1):
        offered = rec.get("offered_strategies", [])
        if not offered:
            continue
        strategy_name = strategy_names.get(offered[0], offered[0])
        guideline = _guideline_label(rec.get("guideline_id", ""))
        grade = rec.get("evidence_grade", "")

        # Top 3 actions from the first offered strategy
        actions = strategy_actions.get(offered[0], [])[:3]
        action_str = ", ".join(actions) if actions else "see strategy"

        lines.append(
            f"{i}. **{strategy_name}** ({guideline}, {grade}): {action_str}"
        )

    lines.append("")
    return "\n".join(lines)


def build_arm_c_context(trace: dict[str, Any]) -> dict[str, Any]:
    """Build the full Arm C context object from an EvalTrace.

    This is the frozen output shape injected into the graph-context arm's
    prompt alongside the PatientContext.

    Applies serialization scoping (F57): classifies each guideline as
    relevant or irrelevant based on trace events, then filters irrelevant
    guidelines from the serialized context to reduce noise.

    Applies serialization compression (F58): when 3+ relevant guidelines
    remain after scoping, switches to a compressed format that reduces
    per-guideline verbosity while preserving cross-guideline signal.
    """
    relevance = classify_guideline_relevance(trace)
    scoped_trace = _filter_trace_by_relevance(trace, relevance["irrelevant"])

    n_guidelines = _count_relevant_guidelines(scoped_trace)
    compressed = n_guidelines >= COMPRESSION_THRESHOLD

    subgraph = serialize_subgraph(scoped_trace)
    trace_summary = serialize_trace_summary(scoped_trace)

    # In compressed mode, replace rendered_prose with one-line-per-guideline
    # and build a compact strategy summary (F59)
    strategy_summary = ""
    if compressed:
        subgraph["rendered_prose"] = _render_compressed_prose(scoped_trace)
        strategy_summary = render_compact_strategy_summary(scoped_trace)

    return {
        "trace_summary": trace_summary,
        "subgraph": subgraph,
        "convergence_summary": serialize_convergence_summary(scoped_trace, subgraph),
        "satisfied_strategies": serialize_satisfied_strategies(scoped_trace),
        "negative_evidence": serialize_negative_evidence(scoped_trace),
        "compressed": compressed,
        "strategy_summary": strategy_summary,
    }
