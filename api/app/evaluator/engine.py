"""Evaluator engine: top-level orchestration.

evaluate() is pure — no wall-clock reads, no RNG, no external I/O.
All inputs are PatientContext + a list of loaded GraphSnapshots.

Multi-guideline forest traversal (F21): the evaluator walks every
guideline in ascending lexical order of guideline_id. Each guideline
is evaluated independently; preemption (F25) and modifier handling
(F26) are not yet implemented.

For the statin model, three out-of-scope exits are checked before
iterating recommendations. See docs/reference/guidelines/statins.md §
Out-of-scope exits.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.evaluator.graph import GraphSnapshot, CodeRef, RecommendationNode
from app.evaluator.predicates.registry import get_predicate
from app.evaluator.predicates.composites import eval_all_of, eval_any_of, eval_none_of
from app.evaluator.trace import TraceBuilder, compute_age, patient_fingerprint


# ---------------------------------------------------------------------------
# Exit-condition definitions (statin guideline)
#
# Per guidelines/statins.md, these are not Recommendation nodes — they are
# evaluator-level pre-flight checks. Ordering matters: secondary
# prevention > familial hypercholesterolemia > age below range.
# ---------------------------------------------------------------------------

_STATIN_EXITS = [
    {
        "token": "out_of_scope_secondary_prevention",
        "rationale": "Established ASCVD is secondary prevention — addressed by ACC/AHA cholesterol guideline, not this USPSTF statement.",
        "check": "_check_secondary_prevention",
    },
    {
        "token": "out_of_scope_familial_hypercholesterolemia",
        "rationale": "Severe primary hypercholesterolemia falls outside the Pooled Cohort Equation calibration range and has its own management pathway.",
        "check": "_check_familial_hypercholesterolemia",
    },
    {
        "token": "out_of_scope_age_below_range",
        "rationale": "USPSTF statin primary prevention does not address adults under 40.",
        "check": "_check_age_below_range",
    },
]

# Maps guideline_id to their exit-condition definitions.
# Guidelines not in this map have no pre-flight exits.
_GUIDELINE_EXITS: dict[str, list[dict[str, Any]]] = {
    "guideline:uspstf-statin-2022": _STATIN_EXITS,
}


def _patient_has_condition_matching(
    patient_context: dict[str, Any],
    entity_codes: list[CodeRef],
) -> bool:
    """Check if any patient condition matches any code in the entity's code list."""
    conditions = patient_context.get("conditions", [])
    entity_code_set = {(c.system, c.code) for c in entity_codes}
    for cond in conditions:
        if cond.get("verification_status") not in ("confirmed",):
            continue
        for code_ref in cond.get("codes", []):
            if (code_ref["system"], code_ref["code"]) in entity_code_set:
                return True
    return False


def _get_most_recent_observation_value(
    patient_context: dict[str, Any],
    entity_codes: list[CodeRef],
) -> float | None:
    """Get the most recent observation value matching the entity codes.

    Only considers observations with status in {final, amended, corrected}.
    Returns value_quantity.value or None if no match.
    Tiebreaker on same effective_date: lexicographic by id (per docs/ISSUES.md).
    """
    observations = patient_context.get("observations", [])
    entity_code_set = {(c.system, c.code) for c in entity_codes}

    matching: list[tuple[str, str, float]] = []  # (effective_date, id, value)
    for obs in observations:
        if obs.get("status") not in ("final", "amended", "corrected"):
            continue
        codes_match = any(
            (c["system"], c["code"]) in entity_code_set
            for c in obs.get("codes", [])
        )
        if not codes_match:
            continue
        value = obs.get("value")
        if value and "value_quantity" in value:
            matching.append((
                obs.get("effective_date", ""),
                obs.get("id", ""),
                value["value_quantity"]["value"],
            ))

    if not matching:
        return None
    # Sort by effective_date desc, then id desc for deterministic tiebreak
    matching.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return matching[0][2]


def _check_secondary_prevention(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient has established ASCVD (cond:ascvd-established)."""
    entity = graph.entities.get("cond:ascvd-established")
    if entity is None:
        return False
    return _patient_has_condition_matching(patient_context, entity.codes)


def _check_familial_hypercholesterolemia(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient has FH condition or LDL >= 190 mg/dL."""
    # Check FH condition
    fh_entity = graph.entities.get("cond:familial-hypercholesterolemia")
    if fh_entity and _patient_has_condition_matching(patient_context, fh_entity.codes):
        return True
    # Check LDL >= 190
    ldl_entity = graph.entities.get("obs:ldl-cholesterol")
    if ldl_entity:
        ldl_value = _get_most_recent_observation_value(patient_context, ldl_entity.codes)
        if ldl_value is not None and ldl_value >= 190:
            return True
    return False


def _check_age_below_range(
    patient_context: dict[str, Any], age: int, graph: GraphSnapshot
) -> bool:
    """Exit if patient age < 40."""
    return age < 40


_EXIT_CHECKERS = {
    "_check_secondary_prevention": _check_secondary_prevention,
    "_check_familial_hypercholesterolemia": _check_familial_hypercholesterolemia,
    "_check_age_below_range": _check_age_below_range,
}


# ---------------------------------------------------------------------------
# Predicate tree evaluation
# ---------------------------------------------------------------------------

# Composite operators — tuple, not set, for deterministic iteration order.
_COMPOSITE_OPS = ("all_of", "any_of", "none_of")

# Map composite names to evaluator functions
_COMPOSITE_EVALUATORS = {
    "all_of": eval_all_of,
    "any_of": eval_any_of,
    "none_of": eval_none_of,
}


def _evaluate_expression(
    expr: dict[str, Any],
    path: list[str | int],
    recommendation_id: str,
    patient_context: dict[str, Any],
    entities: dict[str, Any],
    trace: TraceBuilder,
) -> str:
    """Evaluate a predicate expression tree node (DFS, left-to-right).

    Returns "true", "false", or "unknown".
    Emits predicate_evaluated and composite_resolved trace events.
    """
    # Check if this is a composite (all_of, any_of, none_of)
    composite_key = None
    for key in _COMPOSITE_OPS:
        if key in expr:
            composite_key = key
            break

    if composite_key is not None:
        return _evaluate_composite(
            composite_key, expr[composite_key], path, recommendation_id,
            patient_context, entities, trace,
        )

    # It's a leaf predicate atom — find the predicate name
    return _evaluate_predicate_atom(
        expr, path, recommendation_id, patient_context, entities, trace,
    )


def _evaluate_composite(
    operator: str,
    children: list[dict[str, Any]],
    path: list[str | int],
    recommendation_id: str,
    patient_context: dict[str, Any],
    entities: dict[str, Any],
    trace: TraceBuilder,
) -> str:
    """Evaluate a composite operator with short-circuit semantics.

    Evaluates children left-to-right, short-circuiting when possible per
    three-valued logic (docs/specs/eval-trace.md § Short-circuit semantics).
    """
    composite_path = path + [operator]
    child_results: list[str] = []
    short_circuited = False

    for i, child in enumerate(children):
        child_path = composite_path + [i]
        result = _evaluate_expression(
            child, child_path, recommendation_id,
            patient_context, entities, trace,
        )
        child_results.append(result)

        # Check if we can short-circuit after evaluating this child
        if operator == "all_of" and result == "false":
            short_circuited = (i < len(children) - 1)
            break
        elif operator == "any_of" and result == "true":
            short_circuited = (i < len(children) - 1)
            break
        elif operator == "none_of" and result == "true":
            short_circuited = (i < len(children) - 1)
            break

    # Compute final result
    evaluator_fn = _COMPOSITE_EVALUATORS[operator]
    final_result, _ = evaluator_fn(child_results)

    trace.composite_resolved(
        recommendation_id=recommendation_id,
        path=composite_path,
        operator=operator,
        result=final_result,
        short_circuited=short_circuited,
    )

    return final_result


def _evaluate_predicate_atom(
    expr: dict[str, Any],
    path: list[str | int],
    recommendation_id: str,
    patient_context: dict[str, Any],
    entities: dict[str, Any],
    trace: TraceBuilder,
) -> str:
    """Evaluate a leaf predicate and emit a predicate_evaluated trace event."""
    # Find the predicate name — it's the single key that isn't a composite
    predicate_name = None
    predicate_args = None
    for key, value in expr.items():
        if key not in _COMPOSITE_OPS:
            predicate_name = key
            predicate_args = value if isinstance(value, dict) else {"value": value}
            break

    if predicate_name is None:
        raise ValueError(f"No predicate found in expression: {expr}")

    # Look up and execute the predicate function
    predicate_fn = get_predicate(predicate_name)
    result = predicate_fn(predicate_args, patient_context, entities)

    # Build inputs_read based on predicate type
    inputs_read = _build_inputs_read(predicate_name, predicate_args, patient_context, entities)

    # Determine if missing_data_policy was applied
    missing_data_policy = None
    note = None
    if result == "unknown":
        # Determine the policy from the predicate type
        missing_data_policy = _get_default_policy(predicate_name)
        note = f"Missing data; applied {missing_data_policy} policy"

    trace.predicate_evaluated(
        recommendation_id=recommendation_id,
        path=path,
        predicate=predicate_name,
        args=predicate_args,
        inputs_read=inputs_read,
        result=result,
        missing_data_policy_applied=missing_data_policy,
        note=note,
    )

    return result


def _get_default_policy(predicate_name: str) -> str:
    """Return the default missing-data policy for a predicate."""
    policies = {
        "age_between": "require",
        "age_less_than": "require",
        "age_greater_than_or_equal": "require",
        "administrative_sex_is": "require",
        "has_ancestry_matching": "fail_open",
        "has_condition_history": "fail_open",
        "has_active_condition": "fail_open",
        "smoking_status_is": "fail_closed",
        "most_recent_observation_value": "fail_open",
        "has_medication_active": "fail_open",
        "risk_score_compares": "fail_closed",
    }
    return policies.get(predicate_name, "fail_open")


def _build_inputs_read(
    predicate_name: str,
    args: dict[str, Any],
    patient_context: dict[str, Any],
    entities: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the inputs_read array for a predicate evaluation trace event."""
    inputs: list[dict[str, Any]] = []

    if predicate_name in ("age_between", "age_less_than", "age_greater_than_or_equal"):
        dob = patient_context.get("patient", {}).get("date_of_birth")
        inputs.append({
            "source": "patient.demographics",
            "locator": "patient.date_of_birth",
            "value": dob,
            "present": dob is not None,
        })
        eval_time = patient_context.get("evaluation_time")
        inputs.append({
            "source": "derived",
            "locator": "evaluation_time",
            "value": eval_time,
            "present": eval_time is not None,
        })

    elif predicate_name in ("has_condition_history", "has_active_condition"):
        conditions = patient_context.get("conditions", [])
        inputs.append({
            "source": "patient.conditions",
            "locator": "conditions[]",
            "value": None,
            "present": len(conditions) > 0,
        })

    elif predicate_name == "smoking_status_is":
        tobacco = patient_context.get("social_history", {}).get("tobacco")
        inputs.append({
            "source": "patient.social_history",
            "locator": "social_history.tobacco.status",
            "value": tobacco.get("status") if tobacco else None,
            "present": tobacco is not None and tobacco.get("status") is not None,
        })

    elif predicate_name == "most_recent_observation_value":
        code_node_id = args.get("code", "")
        observations = patient_context.get("observations", [])
        inputs.append({
            "source": "patient.observations",
            "locator": f"observations[code={code_node_id}]",
            "value": None,
            "present": len(observations) > 0,
        })

    elif predicate_name == "has_medication_active":
        medications = patient_context.get("medications", [])
        inputs.append({
            "source": "patient.medications",
            "locator": "medications[]",
            "value": None,
            "present": len(medications) > 0,
        })

    elif predicate_name == "risk_score_compares":
        score_name = args.get("name", "")
        risk_scores = patient_context.get("risk_scores", {})
        score_data = risk_scores.get(score_name)
        inputs.append({
            "source": "patient.risk_scores",
            "locator": f"risk_scores.{score_name}",
            "value": score_data.get("value") if score_data else None,
            "present": score_data is not None,
        })

    return inputs


# ---------------------------------------------------------------------------
# Risk score lookup (emits trace event)
# ---------------------------------------------------------------------------

def _emit_risk_score_lookup(
    score_name: str,
    patient_context: dict[str, Any],
    trace: TraceBuilder,
) -> None:
    """Emit a risk_score_lookup trace event for the given score.

    v0: only reads supplied scores; does not compute via PCE.
    """
    risk_scores = patient_context.get("risk_scores", {})
    score_data = risk_scores.get(score_name)

    if score_data is not None:
        trace.risk_score_lookup(
            score_name=score_name,
            resolution="supplied",
            supplied_value=score_data.get("value"),
            supplied_computed_date=score_data.get("computed_date"),
            method=score_data.get("method_version"),
        )
    else:
        trace.risk_score_lookup(
            score_name=score_name,
            resolution="unavailable",
            note="Risk score not supplied in patient context; v0 does not compute ASCVD via PCE.",
        )


# ---------------------------------------------------------------------------
# Strategy satisfaction
# ---------------------------------------------------------------------------

def _check_strategy_satisfaction(
    rec: RecommendationNode,
    strategy_id: str,
    patient_context: dict[str, Any],
    graph: GraphSnapshot,
    trace: TraceBuilder,
) -> bool:
    """Check if a strategy is satisfied by the patient's current state.

    For Medication strategies: any active medication matching any action's codes.
    For Procedure strategies: not checked in v0 (SDM procedure always unsatisfied
    since v0 fixtures don't carry procedure records).
    """
    strategy = graph.strategies.get(strategy_id)
    if strategy is None:
        return False

    trace.strategy_considered(
        recommendation_id=rec.id,
        strategy_id=strategy_id,
        strategy_name=strategy.name,
    )

    all_satisfied = True
    for action in strategy.actions:
        entity = graph.entities.get(action.action_node_id)
        satisfied = False
        inputs_read: list[dict[str, Any]] = []
        note: str | None = None

        if action.action_entity_type == "Medication":
            # Check if patient has an active medication matching the entity's codes
            if entity is not None:
                entity_code_set = {(c.system, c.code) for c in entity.codes}
                medications = patient_context.get("medications", [])
                for med in medications:
                    if med.get("status") != "active":
                        continue
                    for code_ref in med.get("codes", []):
                        if (code_ref["system"], code_ref["code"]) in entity_code_set:
                            satisfied = True
                            inputs_read.append({
                                "source": "patient.medications",
                                "locator": f"medications[id={med['id']}]",
                                "value": {"id": med["id"], "codes": med.get("codes", [])},
                                "present": True,
                            })
                            break
                    if satisfied:
                        break

                if not satisfied:
                    inputs_read.append({
                        "source": "patient.medications",
                        "locator": "medications[]",
                        "value": None,
                        "present": len(medications) > 0,
                    })
                    note = f"No active medication matching {action.action_node_id}"

        elif action.action_entity_type == "Procedure":
            # v0: procedure satisfaction not fully modeled; check if any matching
            # procedure exists (for SDM encounter). Fixtures don't carry procedure
            # records in v0 so this will always be unsatisfied.
            inputs_read.append({
                "source": "patient.completeness",
                "locator": "completeness",
                "value": None,
                "present": False,
            })
            note = f"No procedure record matching {action.action_node_id}"

        elif action.action_entity_type == "Observation":
            inputs_read.append({
                "source": "patient.observations",
                "locator": "observations[]",
                "value": None,
                "present": False,
            })
            note = f"No observation action check implemented for {action.action_node_id}"

        trace.action_checked(
            recommendation_id=rec.id,
            strategy_id=strategy_id,
            action_node_id=action.action_node_id,
            action_entity_type=action.action_entity_type,
            cadence=action.cadence,
            lookback=action.lookback,
            inputs_read=inputs_read,
            satisfied=satisfied,
            note=note,
        )

        if not satisfied:
            all_satisfied = False

    # Determine strategy satisfaction:
    # Per guidelines/statins.md: statin strategy is satisfied if ANY statin is active.
    # The schema says strategies are conjunction, but class-level medication strategies
    # use "any one member satisfies" per the guideline spec.
    # Check if this is a medication-only strategy (any-match semantics).
    is_medication_only = all(a.action_entity_type == "Medication" for a in strategy.actions)
    if is_medication_only:
        # Any-match: satisfied if any action was satisfied
        any_satisfied = any(
            e.get("satisfied", False)
            for e in trace.events
            if e.get("type") == "action_checked"
            and e.get("strategy_id") == strategy_id
            and e.get("recommendation_id") == rec.id
        )
        strategy_satisfied = any_satisfied
    else:
        strategy_satisfied = all_satisfied

    trace.strategy_resolved(
        recommendation_id=rec.id,
        strategy_id=strategy_id,
        satisfied=strategy_satisfied,
    )

    return strategy_satisfied


# ---------------------------------------------------------------------------
# Full recommendation evaluation
# ---------------------------------------------------------------------------

def _evaluate_recommendation(
    rec: RecommendationNode,
    patient_context: dict[str, Any],
    graph: GraphSnapshot,
    trace: TraceBuilder,
    risk_score_emitted: set[str],
) -> bool:
    """Evaluate a single recommendation's eligibility and emit events.

    Returns True if a recommendation_emitted event was produced.
    """
    # 1. recommendation_considered
    trace.recommendation_considered(
        recommendation_id=rec.id,
        recommendation_title=rec.title,
        evidence_grade=rec.evidence_grade,
        intent=rec.intent,
        trigger=rec.trigger,
    )

    # 2. Evaluate structured_eligibility if present
    if rec.structured_eligibility is not None:
        trace.eligibility_evaluation_started(recommendation_id=rec.id)

        # Check if the eligibility tree references risk_score_compares —
        # emit the risk_score_lookup event before evaluating the tree.
        risk_scores_needed = _find_risk_scores_in_tree(rec.structured_eligibility)
        for score_name in risk_scores_needed:
            if score_name not in risk_score_emitted:
                _emit_risk_score_lookup(score_name, patient_context, trace)
                risk_score_emitted.add(score_name)

        # Walk the eligibility tree
        eligibility_result = _evaluate_expression(
            rec.structured_eligibility,
            [],  # root path
            rec.id,
            patient_context,
            graph.entities,
            trace,
        )

        # Map three-valued result to eligibility outcome
        if eligibility_result == "true":
            elig_outcome = "eligible"
        elif eligibility_result == "false":
            elig_outcome = "ineligible"
        else:
            elig_outcome = "unknown"

        trace.eligibility_evaluation_completed(
            recommendation_id=rec.id,
            result=elig_outcome,
            final_value=eligibility_result,
        )

        if elig_outcome != "eligible":
            return False

    # 3. Eligible — check strategies and emit recommendation
    strategy_ids = rec.strategy_ids
    satisfying_strategy: str | None = None

    for sid in strategy_ids:
        satisfied = _check_strategy_satisfaction(rec, sid, patient_context, graph, trace)
        if satisfied:
            satisfying_strategy = sid
            break

    # 4. Determine status and emit recommendation
    if rec.evidence_grade == "I":
        # Grade I: insufficient evidence, no strategies
        status = "insufficient_evidence"
        reason = (
            f"USPSTF Grade I: {rec.title}. "
            "Current evidence is insufficient to assess the balance of benefits and harms."
        )
        trace.recommendation_emitted(
            recommendation_id=rec.id,
            status=status,
            evidence_grade=rec.evidence_grade,
            reason=reason,
        )
    elif satisfying_strategy is not None:
        status = "up_to_date"
        reason = f"Strategy {satisfying_strategy} is satisfied."
        trace.recommendation_emitted(
            recommendation_id=rec.id,
            status=status,
            evidence_grade=rec.evidence_grade,
            reason=reason,
            offered_strategies=strategy_ids,
            satisfying_strategy=satisfying_strategy,
        )
    else:
        status = "due"
        reason = f"Patient is eligible per {rec.evidence_grade}-grade evidence; no offered strategy is currently satisfied."
        trace.recommendation_emitted(
            recommendation_id=rec.id,
            status=status,
            evidence_grade=rec.evidence_grade,
            reason=reason,
            offered_strategies=strategy_ids,
        )

    return True


def _find_risk_scores_in_tree(tree: dict[str, Any]) -> list[str]:
    """Find all risk_score_compares predicate names referenced in the tree.

    Returns a deduplicated, ordered list of score names.
    """
    names: list[str] = []
    _walk_tree_for_risk_scores(tree, names)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def _walk_tree_for_risk_scores(node: dict[str, Any], names: list[str]) -> None:
    """Recursively walk a predicate tree to find risk_score_compares nodes."""
    for key, value in node.items():
        if key == "risk_score_compares" and isinstance(value, dict):
            name = value.get("name")
            if name:
                names.append(name)
        elif key in ("all_of", "any_of", "none_of") and isinstance(value, list):
            for child in value:
                if isinstance(child, dict):
                    _walk_tree_for_risk_scores(child, names)


# ---------------------------------------------------------------------------
# Per-guideline evaluation
# ---------------------------------------------------------------------------

def _evaluate_guideline(
    patient_context: dict[str, Any],
    graph: GraphSnapshot,
    trace: TraceBuilder,
    age: int,
) -> int:
    """Evaluate a single guideline's recommendations within a forest traversal.

    Sets the guideline context on the trace, emits guideline_entered/exited,
    and returns the count of recommendations emitted.
    """
    trace.set_guideline_context(graph.guideline_id)

    trace.guideline_entered(graph.guideline_id, graph.guideline_title)

    # Exit-condition scan (guideline-specific)
    exit_defs = _GUIDELINE_EXITS.get(graph.guideline_id, [])
    exit_rec_id = graph.recommendations[0].id if graph.recommendations else graph.guideline_id
    exit_fired = False

    for exit_def in exit_defs:
        checker = _EXIT_CHECKERS[exit_def["check"]]
        if checker(patient_context, age, graph):
            trace.exit_condition_triggered(
                recommendation_id=exit_rec_id,
                exit=exit_def["token"],
                rationale=exit_def["rationale"],
            )
            exit_fired = True
            break

    recommendations_emitted = 0
    risk_score_emitted: set[str] = set()

    if not exit_fired:
        for rec in graph.recommendations:
            emitted = _evaluate_recommendation(
                rec, patient_context, graph, trace, risk_score_emitted,
            )
            if emitted:
                recommendations_emitted += 1

    trace.guideline_exited(graph.guideline_id, recommendations_emitted)
    return recommendations_emitted


# ---------------------------------------------------------------------------
# Forest traversal — multi-guideline entry point
# ---------------------------------------------------------------------------

def evaluate(
    patient_context: dict[str, Any],
    graphs: list[GraphSnapshot],
) -> dict[str, Any]:
    """Run the trace-first evaluator across all guidelines (forest traversal).

    Pure function: same (patient_context, graphs) -> same trace.
    Guidelines are visited in ascending lexical order of guideline_id
    (deterministic traversal order per F21 spec).

    Wall-clock fields (envelope.started_at, envelope.completed_at,
    evaluation_completed.duration_ms) are NOT set here — the caller
    (route handler) stamps them after evaluate() returns. This keeps
    evaluate() free of datetime.now() calls.
    """
    # Sort graphs by guideline_id for deterministic traversal
    sorted_graphs = sorted(graphs, key=lambda g: g.guideline_id)

    trace = TraceBuilder()

    # Compute patient demographics
    dob = patient_context["patient"]["date_of_birth"]
    eval_time = patient_context["evaluation_time"]
    age = compute_age(dob, eval_time)
    sex = patient_context["patient"]["administrative_sex"]
    fingerprint = patient_fingerprint(patient_context)

    # 1. evaluation_started (envelope-level, guideline_id=None)
    guideline_ids = [g.guideline_id for g in sorted_graphs]
    trace.evaluation_started(age, sex, guideline_ids)

    # 2. Walk each guideline in lexical order
    total_recommendations_emitted = 0
    for graph in sorted_graphs:
        count = _evaluate_guideline(patient_context, graph, trace, age)
        total_recommendations_emitted += count

    # 3. evaluation_completed (envelope-level, guideline_id=None)
    trace.set_guideline_context(None)
    trace.evaluation_completed(total_recommendations_emitted, duration_ms=0)

    # Build the envelope
    envelope: dict[str, Any] = {
        "spec_tag": settings.spec_tag,
        "graph_version": settings.graph_version,
        "evaluator_version": settings.evaluator_version,
        "evaluation_time": eval_time,
        "patient_fingerprint": fingerprint,
    }

    # Derive flat recommendation list from trace events
    flat_recommendations = [
        {
            "recommendation_id": e["recommendation_id"],
            "guideline_id": e["guideline_id"],
            "status": e["status"],
            "evidence_grade": e["evidence_grade"],
            "reason": e["reason"],
            **({"offered_strategies": e["offered_strategies"]} if "offered_strategies" in e else {}),
            **({"satisfying_strategy": e["satisfying_strategy"]} if "satisfying_strategy" in e else {}),
        }
        for e in trace.events
        if e["type"] == "recommendation_emitted"
    ]

    # Derive per-guideline recommendation breakdown
    per_guideline: dict[str, list[dict[str, Any]]] = {}
    for rec in flat_recommendations:
        gid = rec["guideline_id"]
        if gid not in per_guideline:
            per_guideline[gid] = []
        per_guideline[gid].append(rec)

    return {
        "envelope": envelope,
        "events": trace.events,
        "recommendations": flat_recommendations,
        "recommendations_by_guideline": per_guideline,
    }
