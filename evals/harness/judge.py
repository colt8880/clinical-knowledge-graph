"""Judge module: rubric-based LLM scoring + deterministic structural checks.

The judge uses Claude Opus 4.6 (pinned) to score each arm's output on
four dimensions (1-5). Deterministic structural checks run separately
and are logged alongside but not combined into the composite.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from harness.config import JUDGE_MODEL, RUBRIC_VERSION, TEMPERATURE


JUDGE_PROMPT = """\
You are evaluating a clinical decision support system's output. Score the \
output on four dimensions using the rubric below.

## Patient Context

{patient_context}

## Expected Actions (ground truth)

{expected_actions}

## System Output (to be scored)

{arm_output}

## Rubric

Score each dimension from 1 (worst) to 5 (best):

### Completeness (1-5)
Are all expected actions present in the output?
- 5: All expected actions present, no missing items
- 4: One minor action missing that does not affect clinical outcome
- 3: One clinically relevant action missing
- 2: Multiple expected actions missing
- 1: Most expected actions missing or output is empty/incoherent

### Clinical Appropriateness (1-5)
Are any recommendations contraindicated or clinically wrong?
- 5: All recommendations clinically appropriate; no contraindicated actions
- 4: All recommendations appropriate; minor imprecision in language
- 3: One recommendation questionable but not harmful
- 2: One contraindicated or clearly wrong recommendation present
- 1: Multiple contraindicated or dangerous recommendations

### Prioritization (1-5)
Is sequencing reasonable (most impactful first)?
- 5: Actions ordered by clinical impact; most urgent/impactful first
- 4: Ordering reasonable; one minor sequencing issue
- 3: Ordering partially correct; key action not prioritized appropriately
- 2: Ordering largely incorrect; low-priority items before high-priority
- 1: No coherent ordering; random or reversed priority

### Integration (1-5)
Does the output correctly handle cross-guideline interactions?
{integration_note}

## Response Format

Return a JSON object with this exact structure:
{{
  "completeness": {{"score": <1-5>, "rationale": "<brief explanation>"}},
  "clinical_appropriateness": {{"score": <1-5>, "rationale": "<brief explanation>"}},
  "prioritization": {{"score": <1-5>, "rationale": "<brief explanation>"}},
  "integration": {{"score": <1-5>, "rationale": "<brief explanation>"}},
  "composite": <arithmetic mean of all four scores>
}}
"""

# Integration scoring note for single-guideline baseline (Phase 1)
INTEGRATION_NOTE_SINGLE_GUIDELINE = """\
NOTE: This evaluation is against a single guideline (USPSTF 2022 Statin). \
There are no cross-guideline interactions to evaluate. Score this dimension \
5 by default."""

INTEGRATION_NOTE_MULTI_GUIDELINE = """\
- 5: Cross-guideline interactions correctly identified and resolved
- 4: Interactions mostly correct; one minor gap
- 3: Some interactions missed but no harmful conflicts
- 2: Significant cross-guideline conflicts unresolved
- 1: Cross-guideline interactions ignored entirely"""


def _structural_checks(
    arm_output: dict[str, Any],
    expected_actions: dict[str, Any],
) -> dict[str, Any]:
    """Run deterministic structural checks against the arm output.

    Checks:
    - expected_actions_present: are expected action labels/ids present?
    - contraindications_absent: are contraindicated actions absent?
    - output_parseable: is the output valid JSON with the expected schema?
    """
    parsed = arm_output.get("parsed", {})
    actions = parsed.get("actions", [])

    # Check parseability
    output_parseable = not parsed.get("_parse_error", False)

    # Extract action labels/ids from arm output
    output_labels = set()
    output_ids = set()
    for action in actions:
        if "label" in action:
            output_labels.add(action["label"].lower())
        if "id" in action:
            output_ids.add(action["id"].lower())

    # Check expected actions
    expected = expected_actions.get("actions", [])
    expected_present = []
    for exp_action in expected:
        exp_label = exp_action.get("label", "").lower()
        exp_id = exp_action.get("id", "").lower()
        found = exp_id in output_ids or exp_label in output_labels
        # Fuzzy: also check if any output label contains the expected label
        if not found:
            for ol in output_labels:
                if exp_label and exp_label in ol:
                    found = True
                    break
            for oi in output_ids:
                if exp_id and exp_id in oi:
                    found = True
                    break
        expected_present.append({
            "id": exp_action.get("id"),
            "label": exp_action.get("label"),
            "found": found,
        })

    all_expected_present = all(ep["found"] for ep in expected_present)

    # Check contraindications
    contraindications = expected_actions.get("contraindications", [])
    contraindication_results = []
    for contra in contraindications:
        contra_label = contra.get("label", "").lower()
        contra_id = contra.get("id", "").lower()
        found = contra_id in output_ids or contra_label in output_labels
        if not found:
            for ol in output_labels:
                if contra_label and contra_label in ol:
                    found = True
                    break
        contraindication_results.append({
            "id": contra.get("id"),
            "label": contra.get("label"),
            "found_in_output": found,
        })

    all_contraindications_absent = not any(
        cr["found_in_output"] for cr in contraindication_results
    )

    return {
        "output_parseable": output_parseable,
        "expected_actions_present": all_expected_present,
        "expected_actions_detail": expected_present,
        "contraindications_absent": all_contraindications_absent,
        "contraindications_detail": contraindication_results,
    }


def score(
    patient_context: dict[str, Any],
    arm_output: dict[str, Any],
    expected_actions: dict[str, Any],
    api_key: str | None = None,
    multi_guideline: bool = False,
) -> dict[str, Any]:
    """Score an arm's output using the LLM judge + structural checks.

    Returns a combined result with rubric scores and structural check results.
    """
    # Structural checks (deterministic, no LLM)
    structural = _structural_checks(arm_output, expected_actions)

    # LLM judge scoring
    integration_note = (
        INTEGRATION_NOTE_MULTI_GUIDELINE
        if multi_guideline
        else INTEGRATION_NOTE_SINGLE_GUIDELINE
    )

    pc_text = json.dumps(patient_context, indent=2)
    ea_text = json.dumps(expected_actions, indent=2)

    parsed_output = arm_output.get("parsed", {})
    output_text = json.dumps(parsed_output, indent=2)

    prompt = JUDGE_PROMPT.format(
        patient_context=pc_text,
        expected_actions=ea_text,
        arm_output=output_text,
        integration_note=integration_note,
    )

    client = Anthropic(api_key=api_key) if api_key else Anthropic()

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1024,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text

    # Parse judge response
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        rubric_scores = json.loads(text)
    except json.JSONDecodeError:
        rubric_scores = {
            "completeness": {"score": 0, "rationale": "Judge output unparseable"},
            "clinical_appropriateness": {"score": 0, "rationale": "Judge output unparseable"},
            "prioritization": {"score": 0, "rationale": "Judge output unparseable"},
            "integration": {"score": 0, "rationale": "Judge output unparseable"},
            "composite": 0,
            "_parse_error": True,
            "_raw": raw_text,
        }

    # Recompute composite to ensure consistency
    dimensions = ["completeness", "clinical_appropriateness", "prioritization", "integration"]
    dim_scores = []
    for dim in dimensions:
        s = rubric_scores.get(dim, {})
        if isinstance(s, dict):
            dim_scores.append(s.get("score", 0))
        elif isinstance(s, (int, float)):
            dim_scores.append(s)
    if dim_scores:
        rubric_scores["composite"] = sum(dim_scores) / len(dim_scores)

    return {
        "rubric_version": RUBRIC_VERSION,
        "judge_model": JUDGE_MODEL,
        "rubric_scores": rubric_scores,
        "structural_checks": structural,
        "judge_usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


def _normalize_score(val: float) -> float:
    """Normalize a 1-5 rubric score to 0-1 for Braintrust."""
    return max(0.0, min(1.0, (val - 1) / 4))


def _extract_raw_score(rubric_entry: Any) -> float:
    """Extract the numeric score from a rubric dimension entry."""
    if isinstance(rubric_entry, dict):
        return float(rubric_entry.get("score", 0))
    if isinstance(rubric_entry, (int, float)):
        return float(rubric_entry)
    return 0.0


def clinical_scorer(
    input: dict[str, Any],
    output: dict[str, Any],
    expected: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Braintrust-compatible scorer wrapping the LLM judge + structural checks.

    Returns a list of 5 score dicts (one per dimension + composite),
    each normalized to [0, 1] for Braintrust.
    """
    metadata = metadata or {}
    multi_guideline = metadata.get("subset") == "multi-guideline"

    result = score(
        patient_context=input,
        arm_output=output,
        expected_actions=expected,
        multi_guideline=multi_guideline,
    )

    rubric = result["rubric_scores"]
    structural = result["structural_checks"]

    scores = []
    for dim in ["completeness", "clinical_appropriateness", "prioritization", "integration"]:
        raw = _extract_raw_score(rubric.get(dim, {}))
        rationale = ""
        if isinstance(rubric.get(dim), dict):
            rationale = rubric[dim].get("rationale", "")
        scores.append({
            "name": dim,
            "score": _normalize_score(raw),
            "metadata": {"raw_1_5": raw, "rationale": rationale},
        })

    composite_raw = float(rubric.get("composite", 0))
    scores.append({
        "name": "composite",
        "score": _normalize_score(composite_raw),
        "metadata": {
            "raw_1_5": composite_raw,
            "structural_checks": structural,
        },
    })

    return scores
