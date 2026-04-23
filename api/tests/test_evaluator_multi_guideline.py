"""Multi-guideline evaluator tests (F21).

Verification targets:
  1. All 5 v0 statin fixtures produce traces where every event carries
     guideline_id = "guideline:uspstf-statin-2022" (or null for envelope events).
  2. Running the evaluator against a synthetic two-guideline graph emits
     GUIDELINE_ENTERED events in lexical guideline_id order.
  3. Re-running any fixture twice produces byte-identical trace output.
  4. Every event in the trace has the guideline_id field.
  5. guideline_exited events are present and carry correct recommendation counts.

The synthetic second guideline (TESTGUIDE-A) lives entirely in test code —
no graph/seeds/ pollution. It exercises forest traversal ordering without
needing ACC/AHA content (which lands in F23).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.evaluator.engine import evaluate
from app.evaluator.graph import (
    GraphSnapshot,
    RecommendationNode,
    StrategyNode,
    ActionEdge,
    ClinicalEntity,
    CodeRef,
)


FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "evals" / "fixtures" / "statins"

FIXTURE_CASES = sorted([
    d.name for d in FIXTURES_DIR.iterdir()
    if d.is_dir() and (d / "patient.json").exists()
])

STATIN_GUIDELINE_ID = "guideline:uspstf-statin-2022"
CHOLESTEROL_GUIDELINE_ID = "guideline:acc-aha-cholesterol-2018"
KDIGO_GUIDELINE_ID = "guideline:kdigo-ckd-2024"
ADA_GUIDELINE_ID = "guideline:ada-diabetes-2024"
KNOWN_GUIDELINE_IDS = {STATIN_GUIDELINE_ID, CHOLESTEROL_GUIDELINE_ID, KDIGO_GUIDELINE_ID, ADA_GUIDELINE_ID}


# ---------------------------------------------------------------------------
# Helper: minimal patient context for unit tests
# ---------------------------------------------------------------------------

def _minimal_patient(age_dob: str = "1970-08-12") -> dict:
    return {
        "evaluation_time": "2026-04-15T10:00:00Z",
        "patient": {
            "date_of_birth": age_dob,
            "administrative_sex": "male",
        },
        "conditions": [],
        "observations": [],
        "medications": [],
        "social_history": {},
        "risk_scores": {},
    }


# ---------------------------------------------------------------------------
# Helper: build synthetic test guideline
# ---------------------------------------------------------------------------

def _build_test_guideline_a() -> GraphSnapshot:
    """A minimal synthetic guideline that lexically sorts before the statin guideline.

    guideline_id = "guideline:aaa-test-guide-2024" (sorts before uspstf-statin-2022).
    Contains one Recommendation with no eligibility criteria, one Strategy
    with one Medication action (always unsatisfied in the minimal patient).
    """
    entity = ClinicalEntity(
        id="med:test-drug-alpha",
        label="Medication",
        display_name="Test Drug Alpha",
        codes=[CodeRef(system="rxnorm", code="999999")],
    )
    action = ActionEdge(
        action_node_id="med:test-drug-alpha",
        action_entity_type="Medication",
    )
    strategy = StrategyNode(
        id="strategy:test-a-treatment",
        name="Test A treatment strategy",
        actions=[action],
    )
    rec = RecommendationNode(
        id="rec:test-a-recommend",
        title="Test A recommendation",
        evidence_grade="B",
        intent="treatment",
        trigger="patient_state",
        structured_eligibility=None,  # always eligible (no criteria)
        strategy_ids=["strategy:test-a-treatment"],
    )
    return GraphSnapshot(
        guideline_id="guideline:aaa-test-guide-2024",
        guideline_title="AAA Test Guideline 2024",
        recommendations=[rec],
        entities={"med:test-drug-alpha": entity},
        strategies={"strategy:test-a-treatment": strategy},
    )


def _build_test_guideline_z() -> GraphSnapshot:
    """A synthetic guideline that lexically sorts after the statin guideline.

    guideline_id = "guideline:zzz-test-guide-2024".
    Contains one Recommendation with no eligibility, one Strategy, always unsatisfied.
    """
    entity = ClinicalEntity(
        id="med:test-drug-zeta",
        label="Medication",
        display_name="Test Drug Zeta",
        codes=[CodeRef(system="rxnorm", code="888888")],
    )
    action = ActionEdge(
        action_node_id="med:test-drug-zeta",
        action_entity_type="Medication",
    )
    strategy = StrategyNode(
        id="strategy:test-z-treatment",
        name="Test Z treatment strategy",
        actions=[action],
    )
    rec = RecommendationNode(
        id="rec:test-z-recommend",
        title="Test Z recommendation",
        evidence_grade="A",
        intent="treatment",
        trigger="patient_state",
        structured_eligibility=None,
        strategy_ids=["strategy:test-z-treatment"],
    )
    return GraphSnapshot(
        guideline_id="guideline:zzz-test-guide-2024",
        guideline_title="ZZZ Test Guideline 2024",
        recommendations=[rec],
        entities={"med:test-drug-zeta": entity},
        strategies={"strategy:test-z-treatment": strategy},
    )


# ---------------------------------------------------------------------------
# Tests: guideline_id on every v0 fixture event (integration, needs Neo4j)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case_name", FIXTURE_CASES)
class TestGuidelineIdOnV0Fixtures:
    """Every event in statin fixtures carries a valid guideline_id.

    Updated for multi-guideline: both USPSTF and ACC/AHA are loaded,
    so events may carry either guideline_id.
    """

    @pytest.mark.asyncio
    async def test_every_event_has_guideline_id(self, client, case_name: str):
        case_dir = FIXTURES_DIR / case_name
        patient = json.loads((case_dir / "patient.json").read_text())

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        trace = resp.json()
        for event in trace["events"]:
            assert "guideline_id" in event, (
                f"Event seq={event['seq']} type={event['type']} missing guideline_id"
            )
            # Envelope events and cross-guideline events have guideline_id=null.
            cross_guideline_types = (
                "evaluation_started", "evaluation_completed",
                "preemption_resolved", "cross_guideline_match",
            )
            if event["type"] in cross_guideline_types:
                assert event["guideline_id"] is None, (
                    f"Cross-guideline event {event['type']} should have guideline_id=null"
                )
            else:
                assert event["guideline_id"] in KNOWN_GUIDELINE_IDS, (
                    f"Event seq={event['seq']} type={event['type']} has unknown guideline_id: "
                    f"{event['guideline_id']}"
                )

    @pytest.mark.asyncio
    async def test_guideline_exited_present(self, client, case_name: str):
        case_dir = FIXTURES_DIR / case_name
        patient = json.loads((case_dir / "patient.json").read_text())

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        events = resp.json()["events"]
        exited_events = [e for e in events if e["type"] == "guideline_exited"]
        # With three guidelines loaded, expect 3 guideline_exited events
        assert len(exited_events) == 3, f"Expected 3 guideline_exited, got {len(exited_events)}"
        exited_ids = {e["guideline_id"] for e in exited_events}
        assert STATIN_GUIDELINE_ID in exited_ids
        assert CHOLESTEROL_GUIDELINE_ID in exited_ids
        assert KDIGO_GUIDELINE_ID in exited_ids

    @pytest.mark.asyncio
    async def test_recommendations_have_guideline_id(self, client, case_name: str):
        case_dir = FIXTURES_DIR / case_name
        patient = json.loads((case_dir / "patient.json").read_text())

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        trace = resp.json()
        for rec in trace["recommendations"]:
            assert rec.get("guideline_id") in KNOWN_GUIDELINE_IDS

    @pytest.mark.asyncio
    async def test_recommendations_by_guideline_present(self, client, case_name: str):
        case_dir = FIXTURES_DIR / case_name
        patient = json.loads((case_dir / "patient.json").read_text())

        resp = await client.post("/evaluate", json={"patient_context": patient})
        assert resp.status_code == 200

        trace = resp.json()
        assert "recommendations_by_guideline" in trace


# ---------------------------------------------------------------------------
# Tests: multi-guideline forest traversal (pure unit tests, no Neo4j)
# ---------------------------------------------------------------------------

class TestMultiGuidelineForestTraversal:
    """Forest traversal with synthetic two-guideline graph."""

    def test_guidelines_visited_in_lexical_order(self):
        """guideline_entered events appear in ascending guideline_id order."""
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        # Pass them in reverse order — evaluate must sort
        trace = evaluate(patient, [test_z, test_a])

        entered_events = [
            e for e in trace["events"] if e["type"] == "guideline_entered"
        ]
        assert len(entered_events) == 2
        assert entered_events[0]["guideline_id"] == "guideline:aaa-test-guide-2024"
        assert entered_events[1]["guideline_id"] == "guideline:zzz-test-guide-2024"

    def test_guideline_exited_after_each_guideline(self):
        """Each guideline_entered has a matching guideline_exited."""
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a, test_z])

        exited_events = [
            e for e in trace["events"] if e["type"] == "guideline_exited"
        ]
        assert len(exited_events) == 2
        assert exited_events[0]["guideline_id"] == "guideline:aaa-test-guide-2024"
        assert exited_events[1]["guideline_id"] == "guideline:zzz-test-guide-2024"

    def test_evaluation_started_has_all_guidelines_in_scope(self):
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_z, test_a])

        started = trace["events"][0]
        assert started["type"] == "evaluation_started"
        assert started["guideline_id"] is None
        # Should be sorted
        assert started["guidelines_in_scope"] == [
            "guideline:aaa-test-guide-2024",
            "guideline:zzz-test-guide-2024",
        ]

    def test_evaluation_completed_is_last_and_null_guideline(self):
        test_a = _build_test_guideline_a()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a])

        last = trace["events"][-1]
        assert last["type"] == "evaluation_completed"
        assert last["guideline_id"] is None

    def test_every_event_has_guideline_id_field(self):
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a, test_z])

        for event in trace["events"]:
            assert "guideline_id" in event, (
                f"Event seq={event['seq']} type={event['type']} missing guideline_id"
            )

    def test_recommendations_include_guideline_id(self):
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a, test_z])

        for rec in trace["recommendations"]:
            assert "guideline_id" in rec

    def test_recommendations_by_guideline_keyed_correctly(self):
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a, test_z])

        by_guideline = trace["recommendations_by_guideline"]
        assert "guideline:aaa-test-guide-2024" in by_guideline
        assert "guideline:zzz-test-guide-2024" in by_guideline

    def test_total_recommendations_emitted_count(self):
        """evaluation_completed.recommendations_emitted is the sum across all guidelines."""
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a, test_z])

        completed = trace["events"][-1]
        assert completed["type"] == "evaluation_completed"
        # Both guidelines have 1 rec each (no eligibility = always emitted)
        assert completed["recommendations_emitted"] == 2

    def test_determinism_two_runs_identical(self):
        """Two identical evaluations produce byte-identical canonical JSON."""
        test_a = _build_test_guideline_a()
        test_z = _build_test_guideline_z()
        patient = _minimal_patient()

        trace1 = evaluate(patient, [test_a, test_z])
        trace2 = evaluate(patient, [test_a, test_z])

        # Strip wall-clock fields
        for t in (trace1, trace2):
            env = t.get("envelope", {})
            env.pop("started_at", None)
            env.pop("completed_at", None)
            for event in t.get("events", []):
                event.pop("at", None)
                if event.get("type") == "evaluation_completed":
                    event["duration_ms"] = 0

        canonical1 = json.dumps(trace1, sort_keys=True, separators=(",", ":"))
        canonical2 = json.dumps(trace2, sort_keys=True, separators=(",", ":"))
        assert canonical1 == canonical2

    def test_single_guideline_still_works(self):
        """Single-guideline evaluation produces correct structure."""
        test_a = _build_test_guideline_a()
        patient = _minimal_patient()

        trace = evaluate(patient, [test_a])

        assert len(trace["recommendations"]) == 1
        assert trace["recommendations"][0]["guideline_id"] == "guideline:aaa-test-guide-2024"

        # Event sequence: started -> entered -> rec_considered -> ... -> exited -> completed
        types = [e["type"] for e in trace["events"]]
        assert types[0] == "evaluation_started"
        assert types[1] == "guideline_entered"
        assert "guideline_exited" in types
        assert types[-1] == "evaluation_completed"

    def test_empty_graph_list(self):
        """Evaluating with no guidelines produces an empty but valid trace."""
        patient = _minimal_patient()

        trace = evaluate(patient, [])

        assert trace["events"][0]["type"] == "evaluation_started"
        assert trace["events"][0]["guidelines_in_scope"] == []
        assert trace["events"][-1]["type"] == "evaluation_completed"
        assert trace["events"][-1]["recommendations_emitted"] == 0
        assert trace["recommendations"] == []
