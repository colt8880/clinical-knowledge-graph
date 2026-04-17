"""Parametrized fixture tests for KDIGO 2024 CKD fixtures.

Validates expected-outcome.json assertions against actual evaluator output.
Golden trace byte-match is deferred until golden traces are captured.

Verification targets (from docs/build/24-kdigo-ckd-subgraph.md):
  1. All 3 fixtures produce expected trace events.
  2. Re-running produces identical bytes (determinism check).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "evals" / "fixtures" / "kdigo"

# All KDIGO fixture directories
FIXTURE_CASES = sorted([
    d.name for d in FIXTURES_DIR.iterdir()
    if d.is_dir() and (d / "patient.json").exists()
])


def _load_fixture(case_name: str) -> tuple[dict, dict]:
    """Load patient context and expected outcome from a fixture directory."""
    case_dir = FIXTURES_DIR / case_name
    patient = json.loads((case_dir / "patient.json").read_text())
    expected_outcome = json.loads((case_dir / "expected-outcome.json").read_text())
    return patient, expected_outcome


def _partial_match(template: dict, event: dict) -> bool:
    """Check if all fields in template match the corresponding fields in event."""
    for key, value in template.items():
        if key not in event:
            return False
        if event[key] != value:
            return False
    return True


def _strip_wall_clock(trace: dict) -> dict:
    """Remove wall-clock fields excluded from determinism checks."""
    out = json.loads(json.dumps(trace))
    env = out.get("envelope", {})
    env.pop("started_at", None)
    env.pop("completed_at", None)
    for event in out.get("events", []):
        event.pop("at", None)
        if event.get("type") == "evaluation_completed":
            event["duration_ms"] = 0
    return out


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize("case_name", FIXTURE_CASES)
class TestKdigoFixtureExpectedOutcome:
    """Validate expected-outcome.json assertions against actual trace."""

    @pytest.mark.asyncio
    async def test_expected_recommendations(self, client, case_name: str):
        """Every expected recommendation must appear in the derived list."""
        patient, expected_outcome = _load_fixture(case_name)

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        trace = resp.json()
        recs = trace["recommendations"]

        # Filter to KDIGO recommendations only for this single-guideline gate
        kdigo_recs = [r for r in recs if r.get("guideline_id") == "guideline:kdigo-ckd-2024"]

        expected_recs = expected_outcome.get("expected_recommendations", [])
        for exp_rec in expected_recs:
            matching = [r for r in recs if _partial_match(exp_rec, r)]
            assert len(matching) >= 1, (
                f"Expected recommendation not found in {case_name}: {exp_rec}\n"
                f"Actual recommendations: {recs}"
            )

        # KDIGO rec count must match expected
        expected_kdigo_count = len([r for r in expected_recs if r.get("guideline_id") == "guideline:kdigo-ckd-2024"])
        assert len(kdigo_recs) == expected_kdigo_count, (
            f"KDIGO recommendation count mismatch in {case_name}: "
            f"expected {expected_kdigo_count}, got {len(kdigo_recs)}\n"
            f"Actual KDIGO recs: {kdigo_recs}"
        )

    @pytest.mark.asyncio
    async def test_expected_trace_contains(self, client, case_name: str):
        """Every expected_trace_contains template must match at least one event."""
        patient, expected_outcome = _load_fixture(case_name)

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        events = resp.json()["events"]
        templates = expected_outcome.get("expected_trace_contains", [])

        for template in templates:
            matching = [e for e in events if _partial_match(template, e)]
            assert len(matching) >= 1, (
                f"Expected trace event not found in {case_name}: {template}\n"
                f"Events: {json.dumps(events, indent=2)}"
            )

    @pytest.mark.asyncio
    async def test_must_not_contain(self, client, case_name: str):
        """No event may match any must_not_contain template."""
        patient, expected_outcome = _load_fixture(case_name)

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        events = resp.json()["events"]
        forbidden = expected_outcome.get("must_not_contain", [])

        for template in forbidden:
            matching = [e for e in events if _partial_match(template, e)]
            assert len(matching) == 0, (
                f"Forbidden event found in {case_name}: {template}\n"
                f"Matching events: {matching}"
            )

    @pytest.mark.asyncio
    async def test_determinism(self, client, case_name: str):
        """Two identical requests produce identical canonical JSON."""
        patient, _ = _load_fixture(case_name)

        resp1 = await client.post("/evaluate", json={"patient_context": patient})
        resp2 = await client.post("/evaluate", json={"patient_context": patient})

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        trace1 = _strip_wall_clock(resp1.json())
        trace2 = _strip_wall_clock(resp2.json())

        assert _canonical_json(trace1) == _canonical_json(trace2), (
            f"Determinism failure for {case_name}"
        )
