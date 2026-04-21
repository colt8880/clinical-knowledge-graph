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
{cross_guideline_interactions}
### Cross-Guideline Convergence

{convergence_section}

Use the graph evaluation results to inform and validate your recommendations. \
The graph provides deterministic, guideline-based reasoning that should \
anchor your clinical recommendations.

Respond with a JSON object containing your recommended actions.
"""

# Default API base URL for the evaluator
DEFAULT_API_BASE = "http://localhost:8000"


def _get_eval_trace(
    patient_context: dict[str, Any],
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    """Call the /evaluate endpoint to get the EvalTrace for this patient."""
    with httpx.Client(timeout=30.0) as client:
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

    # Build cross-guideline interactions section (preemption + modifier prose)
    cross_guideline_interactions = _build_interactions_section(trace_summary)

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

    return PROMPT_TEMPLATE.format(
        patient_context=pc_text,
        rendered_prose=rendered_prose,
        matched_recs=matched_recs_text,
        cross_guideline_interactions=cross_guideline_interactions,
        convergence_section=convergence_section,
    )


def _build_interactions_section(trace_summary: dict[str, Any]) -> str:
    """Build the Cross-Guideline Interactions section.

    Only rendered when preemption or modifier events exist.
    Returns an empty string when there are no events (the template
    will just produce a blank line between sections).
    """
    preemption_prose = trace_summary.get("preemption_prose", "")
    modifier_prose = trace_summary.get("modifier_prose", "")

    if not preemption_prose and not modifier_prose:
        return ""

    lines = ["### Cross-Guideline Interactions", ""]
    if preemption_prose:
        lines.append(f"**Preemption:** {preemption_prose}")
        lines.append("")
    if modifier_prose:
        lines.append(f"**Modifier:** {modifier_prose}")
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
