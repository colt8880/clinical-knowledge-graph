"""Arm A: PatientContext-only prompt to Sonnet.

Tests what the LLM knows from training — no guideline material supplied.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from harness.config import ARM_MODEL, TEMPERATURE, SYSTEM_PROMPT


PROMPT_TEMPLATE = """\
Based on the following patient information, provide your clinical \
next-best-action recommendations.

## Patient Context

{patient_context}

Respond with a JSON object containing your recommended actions.
"""


def get_prompt(patient_context: dict[str, Any]) -> str:
    """Build the Arm A prompt (patient context only, no guideline material)."""
    pc_text = json.dumps(patient_context, indent=2)
    return PROMPT_TEMPLATE.format(patient_context=pc_text)


def run(patient_context: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
    """Execute Arm A: vanilla LLM with PatientContext only.

    Returns the parsed JSON output from the model.
    """
    client = Anthropic(api_key=api_key) if api_key else Anthropic()

    prompt = get_prompt(patient_context)

    response = client.messages.create(
        model=ARM_MODEL,
        max_tokens=2048,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text

    # Parse JSON from the response, handling markdown code blocks
    text = raw_text.strip()
    if text.startswith("```"):
        # Strip markdown fences
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"actions": [], "reasoning": raw_text, "_parse_error": True}

    return {
        "arm": "a",
        "model": ARM_MODEL,
        "raw_output": raw_text,
        "parsed": parsed,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
