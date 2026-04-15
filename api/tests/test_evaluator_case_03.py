"""Fixture test: case 03 — 35-year-old male, age-below-range exit.

Exercises the full pipeline (patient context → evaluator → trace) against
the simplest fixture. The evaluator should detect age < 40 and emit an
exit_condition_triggered event without entering any recommendation's
eligibility evaluation.

Verification targets (from docs/build/03-evaluator-case-03.md):
  1. pytest exits 0
  2. POST /evaluate returns trace terminating in exit_condition_triggered
  3. Canonical trace matches golden expected_trace.json (minus wall-clock fields)
  4. Two identical requests produce identical bytes
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "evals" / "statins" / "03-too-young-35m"


def _load_fixture() -> tuple[dict, dict]:
    """Load patient context and expected trace from the fixture directory."""
    patient = json.loads((FIXTURE_DIR / "patient.json").read_text())
    expected = json.loads((FIXTURE_DIR / "expected_trace.json").read_text())
    return patient, expected


def _strip_wall_clock(trace: dict) -> dict:
    """Remove wall-clock fields that are excluded from determinism checks.

    Strips: envelope.started_at, envelope.completed_at,
    and evaluation_completed.duration_ms, and event-level 'at' fields.
    """
    out = json.loads(json.dumps(trace))  # deep copy
    env = out.get("envelope", {})
    env.pop("started_at", None)
    env.pop("completed_at", None)
    for event in out.get("events", []):
        event.pop("at", None)
        if event.get("type") == "evaluation_completed":
            event["duration_ms"] = 0  # normalize to match golden
    return out


def _canonical_json(obj: dict) -> str:
    """Canonical JSON: sorted keys, compact separators, stable numbers."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@pytest.mark.asyncio
async def test_case_03_exit_age_below_range(client):
    """POST /evaluate with fixture 03 returns age-below-range exit trace."""
    patient, _expected = _load_fixture()

    resp = await client.post("/evaluate", json={"patient_context": patient})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    trace = resp.json()

    # The trace must contain an exit_condition_triggered event
    exit_events = [e for e in trace["events"] if e["type"] == "exit_condition_triggered"]
    assert len(exit_events) == 1
    assert exit_events[0]["exit"] == "out_of_scope_age_below_range"

    # No recommendation_emitted events
    rec_events = [e for e in trace["events"] if e["type"] == "recommendation_emitted"]
    assert len(rec_events) == 0

    # No risk_score_lookup events
    risk_events = [e for e in trace["events"] if e["type"] == "risk_score_lookup"]
    assert len(risk_events) == 0

    # recommendations list is empty
    assert trace["recommendations"] == []


@pytest.mark.asyncio
async def test_case_03_golden_trace_match(client):
    """Canonical trace (minus wall-clock) matches the golden expected_trace.json."""
    patient, expected = _load_fixture()

    resp = await client.post("/evaluate", json={"patient_context": patient})
    assert resp.status_code == 200

    actual = _strip_wall_clock(resp.json())
    expected_clean = _strip_wall_clock(expected)

    actual_canonical = _canonical_json(actual)
    expected_canonical = _canonical_json(expected_clean)

    assert actual_canonical == expected_canonical, (
        f"Trace mismatch.\n"
        f"Expected:\n{json.dumps(expected_clean, indent=2)}\n"
        f"Actual:\n{json.dumps(actual, indent=2)}"
    )


@pytest.mark.asyncio
async def test_case_03_determinism(client):
    """Two identical requests produce identical bytes (determinism contract)."""
    patient, _expected = _load_fixture()

    resp1 = await client.post("/evaluate", json={"patient_context": patient})
    resp2 = await client.post("/evaluate", json={"patient_context": patient})

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    trace1 = _strip_wall_clock(resp1.json())
    trace2 = _strip_wall_clock(resp2.json())

    assert _canonical_json(trace1) == _canonical_json(trace2)
