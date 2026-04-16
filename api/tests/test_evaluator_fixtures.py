"""Parametrized fixture tests: all 5 statin fixtures must produce matching traces.

Verification targets (from docs/build/04-evaluator-full.md):
  1. cd api && pytest — all tests pass, including all 5 golden-trace fixtures.
  2. Each fixture's terminal event matches guidelines/statins.md § patient-path-summary.
  3. Re-running produces identical bytes (determinism check).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "evals" / "fixtures" / "statins"

# All 5 v0 fixture directories
FIXTURE_CASES = sorted([
    d.name for d in FIXTURES_DIR.iterdir()
    if d.is_dir() and (d / "patient.json").exists()
])


def _load_fixture(case_name: str) -> tuple[dict, dict, dict]:
    """Load patient context, expected outcome, and golden trace from a fixture directory."""
    case_dir = FIXTURES_DIR / case_name
    patient = json.loads((case_dir / "patient.json").read_text())
    expected_outcome = json.loads((case_dir / "expected-outcome.json").read_text())
    expected_trace = json.loads((case_dir / "expected_trace.json").read_text())
    return patient, expected_outcome, expected_trace


def _strip_wall_clock(trace: dict) -> dict:
    """Remove wall-clock fields excluded from determinism checks."""
    out = json.loads(json.dumps(trace))  # deep copy
    env = out.get("envelope", {})
    env.pop("started_at", None)
    env.pop("completed_at", None)
    for event in out.get("events", []):
        event.pop("at", None)
        if event.get("type") == "evaluation_completed":
            event["duration_ms"] = 0
    return out


def _canonical_json(obj: dict) -> str:
    """Canonical JSON: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _partial_match(template: dict, event: dict) -> bool:
    """Check if all fields in template match the corresponding fields in event."""
    for key, value in template.items():
        if key not in event:
            return False
        if event[key] != value:
            return False
    return True


@pytest.mark.parametrize("case_name", FIXTURE_CASES)
class TestFixtureGoldenTrace:
    """Golden trace byte-match for each fixture."""

    @pytest.mark.asyncio
    async def test_golden_trace_match(self, client, case_name: str):
        """Canonical trace (minus wall-clock) matches expected_trace.json."""
        patient, _, expected_trace = _load_fixture(case_name)

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        actual = _strip_wall_clock(resp.json())
        expected = _strip_wall_clock(expected_trace)

        actual_canonical = _canonical_json(actual)
        expected_canonical = _canonical_json(expected)

        assert actual_canonical == expected_canonical, (
            f"Trace mismatch for {case_name}.\n"
            f"Expected:\n{json.dumps(expected, indent=2)}\n"
            f"Actual:\n{json.dumps(actual, indent=2)}"
        )

    @pytest.mark.asyncio
    async def test_determinism(self, client, case_name: str):
        """Two identical requests produce identical canonical JSON."""
        patient, _, _ = _load_fixture(case_name)

        resp1 = await client.post("/evaluate", json={"patient_context": patient})
        resp2 = await client.post("/evaluate", json={"patient_context": patient})

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        trace1 = _strip_wall_clock(resp1.json())
        trace2 = _strip_wall_clock(resp2.json())

        assert _canonical_json(trace1) == _canonical_json(trace2), (
            f"Determinism failure for {case_name}"
        )


@pytest.mark.parametrize("case_name", FIXTURE_CASES)
class TestFixtureExpectedOutcome:
    """Validate expected-outcome.json assertions against actual trace."""

    @pytest.mark.asyncio
    async def test_expected_recommendations(self, client, case_name: str):
        """Every expected recommendation must appear in the derived list."""
        patient, expected_outcome, _ = _load_fixture(case_name)

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        trace = resp.json()
        recs = trace["recommendations"]

        expected_recs = expected_outcome.get("expected_recommendations", [])
        for exp_rec in expected_recs:
            matching = [r for r in recs if _partial_match(exp_rec, r)]
            assert len(matching) >= 1, (
                f"Expected recommendation not found in {case_name}: {exp_rec}\n"
                f"Actual recommendations: {recs}"
            )

        # No extra recommendations beyond what's expected
        if expected_recs is not None:
            assert len(recs) == len(expected_recs), (
                f"Extra recommendations in {case_name}: expected {len(expected_recs)}, got {len(recs)}\n"
                f"Actual: {recs}"
            )

    @pytest.mark.asyncio
    async def test_expected_trace_contains(self, client, case_name: str):
        """Every expected_trace_contains template must match at least one event."""
        patient, expected_outcome, _ = _load_fixture(case_name)

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
        patient, expected_outcome, _ = _load_fixture(case_name)

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
