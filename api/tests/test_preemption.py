"""Unit tests for preemption resolution (F25).

Tests the pure resolve_preemptions() function and the engine integration.
No Neo4j required — uses in-memory graph snapshots.
"""

from __future__ import annotations

import json
import logging

import pytest

from app.evaluator.engine import evaluate
from app.evaluator.graph import (
    GraphSnapshot,
    PreemptionEdge,
    RecommendationNode,
    ClinicalEntity,
    CodeRef,
    StrategyNode,
    ActionEdge,
)
from app.evaluator.preemption import resolve_preemptions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_edge(preempted: str, winner: str, priority: int = 200) -> PreemptionEdge:
    return PreemptionEdge(
        preempted_rec_id=preempted,
        winning_rec_id=winner,
        priority=priority,
        rationale=f"{winner} preempts {preempted}",
    )


def _make_simple_graph(
    guideline_id: str,
    rec_ids: list[str],
) -> GraphSnapshot:
    """Build a minimal graph with recommendations that always match (no eligibility)."""
    recs = [
        RecommendationNode(
            id=rid,
            title=f"Test rec {rid}",
            evidence_grade="B",
            intent="primary_prevention",
            trigger="patient_state",
            structured_eligibility=None,  # no eligibility = always matches
            strategy_ids=[],
        )
        for rid in rec_ids
    ]
    return GraphSnapshot(
        guideline_id=guideline_id,
        guideline_title=f"Test guideline {guideline_id}",
        recommendations=recs,
        entities={},
        strategies={},
    )


BASIC_PATIENT = {
    "evaluation_time": "2026-04-15T10:00:00Z",
    "patient": {
        "date_of_birth": "1970-01-01",
        "administrative_sex": "male",
    },
    "conditions": [],
    "observations": [],
    "medications": [],
    "social_history": {},
    "risk_scores": {},
    "completeness": {},
}


# ---------------------------------------------------------------------------
# Unit tests for resolve_preemptions()
# ---------------------------------------------------------------------------

class TestResolvePreemptions:
    """Test the pure preemption resolution function."""

    def test_no_edges(self):
        """No preemption edges → no results."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a", "rec:b"},
            preemption_edges=[],
            guideline_published_at={},
            rec_to_guideline={},
        )
        assert result == []

    def test_no_emitted_recs(self):
        """No emitted recs → no results even with edges."""
        result = resolve_preemptions(
            emitted_rec_ids=set(),
            preemption_edges=[_make_edge("rec:a", "rec:b")],
            guideline_published_at={},
            rec_to_guideline={},
        )
        assert result == []

    def test_winner_not_emitted(self):
        """Winner not emitted → preemption does not activate."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a"},
            preemption_edges=[_make_edge("rec:a", "rec:b")],
            guideline_published_at={},
            rec_to_guideline={},
        )
        assert result == []

    def test_loser_not_emitted(self):
        """Loser not emitted → preemption does not activate."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:b"},
            preemption_edges=[_make_edge("rec:a", "rec:b")],
            guideline_published_at={},
            rec_to_guideline={},
        )
        assert result == []

    def test_basic_preemption(self):
        """Both sides emitted → preemption fires."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a", "rec:b"},
            preemption_edges=[_make_edge("rec:a", "rec:b", priority=200)],
            guideline_published_at={},
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2"},
        )
        assert len(result) == 1
        assert result[0].preempted_rec_id == "rec:a"
        assert result[0].winning_rec_id == "rec:b"
        assert result[0].edge_priority == 200

    def test_higher_priority_wins(self):
        """Multiple winners for same loser → highest priority wins."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a", "rec:b", "rec:c"},
            preemption_edges=[
                _make_edge("rec:a", "rec:b", priority=100),
                _make_edge("rec:a", "rec:c", priority=200),
            ],
            guideline_published_at={},
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2", "rec:c": "g3"},
        )
        assert len(result) == 1
        assert result[0].winning_rec_id == "rec:c"
        assert result[0].edge_priority == 200

    def test_priority_tie_published_at_tiebreak(self):
        """Same priority → newer published_at wins."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a", "rec:b", "rec:c"},
            preemption_edges=[
                _make_edge("rec:a", "rec:b", priority=200),
                _make_edge("rec:a", "rec:c", priority=200),
            ],
            guideline_published_at={"g2": "2018-11-10", "g3": "2022-08-23"},
            rec_to_guideline={"rec:a": "g1", "rec:b": "g2", "rec:c": "g3"},
        )
        assert len(result) == 1
        # g3 has newer published_at, but sort_key uses -priority then pub_at
        # With same priority, we sort by pub_at ascending (lexicographic),
        # so "2018-11-10" < "2022-08-23" → rec:b comes first
        assert result[0].winning_rec_id == "rec:b"

    def test_multiple_preemptions(self):
        """Multiple losers, each with their own winner."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:a", "rec:b", "rec:c"},
            preemption_edges=[
                _make_edge("rec:a", "rec:c", priority=200),
                _make_edge("rec:b", "rec:c", priority=200),
            ],
            guideline_published_at={},
            rec_to_guideline={"rec:a": "g1", "rec:b": "g1", "rec:c": "g2"},
        )
        assert len(result) == 2
        preempted_ids = {r.preempted_rec_id for r in result}
        assert preempted_ids == {"rec:a", "rec:b"}
        assert all(r.winning_rec_id == "rec:c" for r in result)

    def test_transitive_chain_logged(self, caplog):
        """Transitive chain (A→B, B→C) is detected and logged."""
        with caplog.at_level(logging.WARNING):
            result = resolve_preemptions(
                emitted_rec_ids={"rec:a", "rec:b", "rec:c"},
                preemption_edges=[
                    _make_edge("rec:a", "rec:b", priority=200),
                    _make_edge("rec:b", "rec:c", priority=200),
                ],
                guideline_published_at={},
                rec_to_guideline={"rec:a": "g1", "rec:b": "g2", "rec:c": "g3"},
            )
        # Both preemptions still resolve
        assert len(result) == 2
        # Warning logged about transitive chain
        assert any("Transitive preemption detected" in msg for msg in caplog.messages)

    def test_deterministic_ordering(self):
        """Results are in deterministic order (sorted by preempted_rec_id)."""
        result = resolve_preemptions(
            emitted_rec_ids={"rec:z", "rec:a", "rec:m", "rec:winner"},
            preemption_edges=[
                _make_edge("rec:z", "rec:winner", priority=200),
                _make_edge("rec:a", "rec:winner", priority=200),
                _make_edge("rec:m", "rec:winner", priority=200),
            ],
            guideline_published_at={},
            rec_to_guideline={
                "rec:z": "g1", "rec:a": "g1", "rec:m": "g1", "rec:winner": "g2",
            },
        )
        preempted_ids = [r.preempted_rec_id for r in result]
        assert preempted_ids == sorted(preempted_ids)


# ---------------------------------------------------------------------------
# Engine integration tests (in-memory, no Neo4j)
# ---------------------------------------------------------------------------

class TestEnginePreemptionIntegration:
    """Test preemption integration in the evaluate() function."""

    def test_no_preemption_edges_no_change(self):
        """Without preemption edges, evaluate behaves as before."""
        graphs = [_make_simple_graph("guideline:aaa", ["rec:a1"])]
        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=[])

        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["preempted_by"] is None
        # No preemption_resolved events
        preemption_events = [
            e for e in result["events"] if e["type"] == "preemption_resolved"
        ]
        assert len(preemption_events) == 0

    def test_preemption_fires_when_both_match(self):
        """When both Recs match and an edge exists, preemption fires."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        edges = [_make_edge("rec:loser", "rec:winner", priority=200)]

        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        # Both recs emitted
        assert len(result["recommendations"]) == 2

        # preemption_resolved event present
        preemption_events = [
            e for e in result["events"] if e["type"] == "preemption_resolved"
        ]
        assert len(preemption_events) == 1
        pe = preemption_events[0]
        assert pe["preempted_recommendation_id"] == "rec:loser"
        assert pe["preempting_recommendation_id"] == "rec:winner"
        assert pe["edge_priority"] == 200
        assert pe["guideline_id"] is None  # envelope-level

        # Derived recommendation has preempted_by field
        loser_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:loser"
        )
        assert loser_rec["preempted_by"] == "rec:winner"

        winner_rec = next(
            r for r in result["recommendations"]
            if r["recommendation_id"] == "rec:winner"
        )
        assert winner_rec["preempted_by"] is None

    def test_preemption_event_before_evaluation_completed(self):
        """preemption_resolved events come after guideline_exited but before evaluation_completed."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        edges = [_make_edge("rec:loser", "rec:winner")]

        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        event_types = [e["type"] for e in result["events"]]
        preemption_idx = event_types.index("preemption_resolved")
        completed_idx = event_types.index("evaluation_completed")
        last_exited_idx = max(
            i for i, t in enumerate(event_types) if t == "guideline_exited"
        )

        assert preemption_idx > last_exited_idx
        assert preemption_idx < completed_idx

    def test_preemption_does_not_fire_when_winner_unmatched(self):
        """If the winner Rec is not emitted, no preemption."""
        # Only one graph with the loser; winner is not in any graph
        graphs = [_make_simple_graph("guideline:aaa", ["rec:loser"])]
        edges = [_make_edge("rec:loser", "rec:winner")]

        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["preempted_by"] is None
        preemption_events = [
            e for e in result["events"] if e["type"] == "preemption_resolved"
        ]
        assert len(preemption_events) == 0

    def test_determinism_with_preemption(self):
        """Two runs with same inputs produce byte-identical traces."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        edges = [_make_edge("rec:loser", "rec:winner")]

        r1 = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)
        r2 = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        j1 = json.dumps(r1, sort_keys=True, separators=(",", ":"))
        j2 = json.dumps(r2, sort_keys=True, separators=(",", ":"))
        assert j1 == j2

    def test_preempted_by_in_recommendations_by_guideline(self):
        """preempted_by field appears in recommendations_by_guideline too."""
        graphs = [
            _make_simple_graph("guideline:aaa", ["rec:loser"]),
            _make_simple_graph("guideline:zzz", ["rec:winner"]),
        ]
        edges = [_make_edge("rec:loser", "rec:winner")]

        result = evaluate(BASIC_PATIENT, graphs, preemption_edges=edges)

        aaa_recs = result["recommendations_by_guideline"]["guideline:aaa"]
        assert len(aaa_recs) == 1
        assert aaa_recs[0]["preempted_by"] == "rec:winner"
