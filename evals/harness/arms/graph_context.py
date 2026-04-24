"""Arm C: PatientContext + graph-retrieved context (serialized EvalTrace + subgraph).

Calls the /evaluate API to get the EvalTrace, serializes it into an
LLM-friendly summary, and injects it alongside the PatientContext.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from anthropic import Anthropic

from harness.config import ARM_MODEL, SYSTEM_PROMPT, TEMPERATURE
from harness.serialization import build_arm_c_context


PROMPT_TEMPLATE = """\
Based on the following patient information and clinical knowledge graph \
evaluation results, provide your clinical next-best-action recommendations.

## Patient Context

{patient_context}

## Knowledge Graph Evaluation Results

The following is a structured summary of the clinical knowledge graph's \
evaluation of this patient against published clinical guidelines. The graph \
encodes guideline recommendations, eligibility criteria, and treatment \
strategies as structured nodes and edges.

### Evaluation Summary

{rendered_prose}

### Matched Recommendations

{matched_recs}
{satisfied_strategies_section}\
{cross_guideline_interactions}\
{negative_evidence_section}\
### Cross-Guideline Convergence

{convergence_section}

**Instructions:**

1. For therapies the patient is already receiving that align with guideline \
recommendations (listed under "Currently Satisfied Strategies" above), \
explicitly recommend continuation. Do not stay silent on satisfied \
recommendations — "Continue [therapy]" is a clinically important action.

2. When multiple guidelines apply, explicitly state which guideline takes \
precedence and why. If one guideline preempts another, name both guidelines \
and explain the hierarchy. If one guideline modifies another (e.g., reducing \
statin intensity due to CKD), state the modification and cite both guidelines.

3. Use the graph evaluation results to inform and validate your recommendations. \
The graph provides deterministic, guideline-based reasoning that should \
anchor your clinical recommendations.

4. The knowledge graph covers guideline-specific pharmacotherapy recommendations. \
For clinically relevant actions not encoded in the graph — including lifestyle \
modifications (smoking cessation, diet, exercise), monitoring follow-ups \
conditional on treatment response, and blood pressure optimization — apply \
your clinical knowledge based on the patient context. Do not limit your \
recommendations to only what the graph covers.

{output_format_instruction}
"""

# Default API base URL for the evaluator
DEFAULT_API_BASE = "http://localhost:8000"


def _get_eval_trace(
    patient_context: dict[str, Any],
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    """Call the /evaluate endpoint to get the EvalTrace for this patient."""
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{api_base}/evaluate",
            json={"patient_context": patient_context},
        )
        response.raise_for_status()
        return response.json()


def get_prompt(
    patient_context: dict[str, Any],
    graph_context: dict[str, Any],
) -> str:
    """Build the Arm C prompt with patient context and graph evaluation results."""
    pc_text = json.dumps(patient_context, indent=2)

    trace_summary = graph_context["trace_summary"]
    subgraph = graph_context["subgraph"]

    rendered_prose = subgraph.get("rendered_prose", "No evaluation results available.")

    matched_recs_text = json.dumps(trace_summary.get("matched_recs", []), indent=2)

    # Build satisfied strategies section
    satisfied_strategies = graph_context.get("satisfied_strategies", [])
    satisfied_strategies_section = _build_satisfied_strategies_section(satisfied_strategies)

    # Build cross-guideline interactions section (preemption + modifier prose)
    cross_guideline_interactions = _build_interactions_section(trace_summary)

    # Build negative evidence section
    negative_evidence = graph_context.get("negative_evidence", [])
    negative_evidence_section = _build_negative_evidence_section(negative_evidence)

    # Build convergence section — v2 uses grouped therapeutic classes
    convergence = graph_context.get("convergence_summary", {})
    convergence_prose = convergence.get("convergence_prose", "")

    if convergence_prose:
        convergence_section = (
            f"{convergence_prose}\n\n"
            "Where multiple guidelines converge on the same therapeutic action, "
            "this represents independent clinical agreement that should strengthen "
            "your confidence in that recommendation."
        )
    else:
        convergence_section = "No cross-guideline convergence detected (single guideline or no shared actions)."

    # Build output format instruction — extended schema when cross-guideline
    # interactions or negative evidence are present
    has_interactions = bool(
        trace_summary.get("preemption_events")
        or trace_summary.get("modifier_events")
    )
    has_negative = bool(negative_evidence)
    output_format_instruction = _build_output_format_instruction(
        has_interactions, has_negative
    )

    return PROMPT_TEMPLATE.format(
        patient_context=pc_text,
        rendered_prose=rendered_prose,
        matched_recs=matched_recs_text,
        satisfied_strategies_section=satisfied_strategies_section,
        cross_guideline_interactions=cross_guideline_interactions,
        negative_evidence_section=negative_evidence_section,
        convergence_section=convergence_section,
        output_format_instruction=output_format_instruction,
    )


def _build_satisfied_strategies_section(
    satisfied_strategies: list[dict[str, Any]],
) -> str:
    """Build the Currently Satisfied Strategies section.

    Surfaces strategies with status up_to_date so the LLM knows to
    recommend continuing these therapies rather than staying silent.
    Returns an empty string when no strategies are satisfied.
    """
    if not satisfied_strategies:
        return ""

    lines = ["### Currently Satisfied Strategies", ""]
    lines.append(
        "The following guideline recommendations are **already satisfied** by the "
        "patient's current therapies. These are clinically important maintenance "
        "actions — recommend continuing them."
    )
    lines.append("")

    for ss in satisfied_strategies:
        guideline = ss.get("guideline_label") or ss.get("guideline_id", "")
        grade = ss["evidence_grade"]
        strategy_name = ss["strategy_name"]
        satisfied_by = ss.get("satisfied_by", [])

        lines.append(
            f"- **{strategy_name}** ({guideline}, Grade {grade}): "
            f"satisfied by current therapy"
        )
        if satisfied_by:
            med_list = ", ".join(satisfied_by)
            lines.append(f"  - Active: {med_list}")
        lines.append("")

    return "\n".join(lines) + "\n"


def _build_negative_evidence_section(
    negative_evidence: list[dict[str, Any]],
) -> str:
    """Build the Guidelines Evaluated Without Recommendations section.

    Surfaces guidelines the graph evaluated but that produced no actionable
    recs for this patient. This is negative evidence: clinically significant
    because it tells the LLM what *didn't* apply.
    Returns an empty string when no negative evidence exists.
    """
    if not negative_evidence:
        return ""

    lines = ["### Guidelines Evaluated Without Recommendations", ""]
    lines.append(
        "The following guidelines were evaluated for this patient but produced "
        "no applicable recommendations:"
    )
    lines.append("")

    for ne in negative_evidence:
        label = ne.get("guideline_label") or ne.get("guideline_id", "")
        reason = ne.get("reason", "")
        lines.append(f"- **{label}**: {reason}")

    lines.append("")
    lines.append(
        "When a guideline was evaluated and did not fire, this is clinically "
        "significant. Do not attribute actions to guidelines that did not "
        "produce recommendations for this patient."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def _build_output_format_instruction(
    has_interactions: bool,
    has_negative_evidence: bool,
) -> str:
    """Build the output format instruction for Arm C.

    When cross-guideline interactions or negative evidence are present,
    requests an extended schema with cross_guideline_resolutions and/or
    guidelines_without_recommendations sections. Otherwise, requests
    the standard actions-only JSON.
    """
    if not has_interactions and not has_negative_evidence:
        return "Respond with a JSON object containing your recommended actions."

    parts = [
        "Respond with a JSON object using this extended schema:\n"
        "```json\n{\n"
        '  "actions": [...],'
    ]

    if has_interactions:
        parts.append(
            '\n  "cross_guideline_resolutions": [\n'
            "    {\n"
            '      "type": "preemption | modification | convergence",\n'
            '      "guidelines_involved": ["Guideline A", "Guideline B"],\n'
            '      "resolution": "How the interaction was resolved",\n'
            '      "impact_on_actions": "How this affects the recommended actions"\n'
            "    }\n"
            "  ],"
        )

    if has_negative_evidence:
        parts.append(
            '\n  "guidelines_without_recommendations": [\n'
            "    {\n"
            '      "guideline": "Guideline name",\n'
            '      "reason": "Why no recommendations were produced"\n'
            "    }\n"
            "  ],"
        )

    parts.append(
        '\n  "reasoning": "..."\n'
        "}\n```"
    )

    return "".join(parts)


def _build_interactions_section(trace_summary: dict[str, Any]) -> str:
    """Build the Cross-Guideline Interactions section.

    Only rendered when preemption or modifier events exist. Uses directive
    language so the LLM articulates the reasoning about guideline hierarchy,
    not just the resulting action.
    Returns an empty string when there are no events (the template
    will just produce a blank line between sections).
    """
    preemption_prose = trace_summary.get("preemption_prose", "")
    modifier_prose = trace_summary.get("modifier_prose", "")

    if not preemption_prose and not modifier_prose:
        return ""

    lines = ["### Cross-Guideline Interactions", ""]
    lines.append(
        "**IMPORTANT:** When recommending actions below, you MUST explicitly "
        "state the guideline hierarchy reasoning — name both guidelines and "
        "explain which takes precedence and why."
    )
    lines.append("")
    if preemption_prose:
        lines.append(f"**Preemption:** {preemption_prose}")
        lines.append(
            "→ In your output, explicitly state that this preemption applies "
            "and cite both the preempted and preempting guidelines."
        )
        lines.append("")
    if modifier_prose:
        lines.append(f"**Modifier:** {modifier_prose}")
        lines.append(
            "→ In your output, explicitly explain this modification — state "
            "what the original guideline recommends, what the modifying "
            "guideline changes, and why (e.g., altered pharmacokinetics in CKD)."
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def run(
    patient_context: dict[str, Any],
    anthropic_api_key: str | None = None,
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    """Execute Arm C: graph-context LLM with EvalTrace + subgraph.

    1. Calls /evaluate to get the trace.
    2. Serializes trace into LLM-friendly context.
    3. Prompts the LLM with patient context + graph context.

    Returns the parsed JSON output from the model.
    """
    # Get the evaluation trace from the API
    trace = _get_eval_trace(patient_context, api_base=api_base)
    graph_context = build_arm_c_context(trace)

    prompt = get_prompt(patient_context, graph_context)

    client = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else Anthropic()

    response = client.messages.create(
        model=ARM_MODEL,
        max_tokens=2048,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"actions": [], "reasoning": raw_text, "_parse_error": True}

    return {
        "arm": "c",
        "model": ARM_MODEL,
        "graph_context": graph_context,
        "raw_output": raw_text,
        "parsed": parsed,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
