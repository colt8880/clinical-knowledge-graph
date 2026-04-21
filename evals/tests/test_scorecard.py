"""Tests for harness.scorecard — aggregation, thesis gate, self-consistency."""

from __future__ import annotations

import pytest

from harness.scorecard import (
    DIMENSIONS,
    SELF_CONSISTENCY_SD_THRESHOLD,
    THESIS_MARGIN,
    build_scorecard,
    classify_fixture,
)


def _make_entry(
    fixture: str,
    arm: str,
    completeness: float = 4.0,
    clinical_appropriateness: float = 4.0,
    prioritization: float = 4.0,
    integration: float = 4.0,
) -> dict:
    """Helper to create a result entry matching runner output shape."""
    composite = (completeness + clinical_appropriateness + prioritization + integration) / 4
    return {
        "fixture": fixture,
        "arm": arm,
        "composite": composite,
        "scores": {
            "rubric_scores": {
                "completeness": {"score": completeness, "rationale": "test"},
                "clinical_appropriateness": {"score": clinical_appropriateness, "rationale": "test"},
                "prioritization": {"score": prioritization, "rationale": "test"},
                "integration": {"score": integration, "rationale": "test"},
                "composite": composite,
            },
        },
    }


# --- classify_fixture ---

def test_classify_single_guideline():
    assert classify_fixture("statins/01-high-risk-55m-smoker") == "single-guideline"
    assert classify_fixture("cholesterol/case-01") == "single-guideline"
    assert classify_fixture("kdigo/case-01") == "single-guideline"


def test_classify_multi_guideline():
    assert classify_fixture("cross-domain/case-01") == "multi-guideline"
    assert classify_fixture("cross-domain/case-04") == "multi-guideline"


# --- build_scorecard: basic structure ---

def test_scorecard_structure():
    run = [
        _make_entry("statins/case-01", "a"),
        _make_entry("statins/case-01", "b"),
        _make_entry("statins/case-01", "c"),
        _make_entry("cross-domain/case-01", "a"),
        _make_entry("cross-domain/case-01", "b"),
        _make_entry("cross-domain/case-01", "c"),
    ]
    sc = build_scorecard([run], run_name="test")

    assert sc["run_name"] == "test"
    assert sc["n_runs"] == 1
    assert sc["n_fixtures"] == 2
    assert sc["n_arms"] == 3
    assert "fixture_scores" in sc
    assert "arm_subset_summary" in sc
    assert "thesis_gate" in sc
    assert "self_consistency" in sc


# --- thesis gate: PASS ---

def test_thesis_gate_pass():
    """Arm C beats Arm B by >= 0.5 on multi-guideline."""
    run = [
        # Single-guideline (doesn't affect thesis)
        _make_entry("statins/case-01", "b", integration=4.0),
        _make_entry("statins/case-01", "c", integration=4.0),
        # Multi-guideline: Arm C wins by 1.0 on integration
        _make_entry("cross-domain/case-01", "b", integration=3.0),
        _make_entry("cross-domain/case-01", "c", integration=5.0),
    ]
    sc = build_scorecard([run])
    thesis = sc["thesis_gate"]

    assert thesis["result"] == "PASS"
    assert thesis["margin"] >= THESIS_MARGIN
    assert thesis["arm_c_composite"] > thesis["arm_b_composite"]


# --- thesis gate: FAIL ---

def test_thesis_gate_fail_narrow():
    """Arm C wins by < 0.5 on multi-guideline."""
    run = [
        _make_entry("cross-domain/case-01", "b", integration=4.0),
        _make_entry("cross-domain/case-01", "c", integration=4.5),
    ]
    sc = build_scorecard([run])
    thesis = sc["thesis_gate"]

    # 0.5 / 4 dimensions = 0.125 margin on composite
    assert thesis["result"] == "FAIL"
    assert thesis["margin"] < THESIS_MARGIN
    assert "failure_analysis" in thesis


def test_thesis_gate_fail_arm_c_loss():
    """Arm B beats Arm C on multi-guideline."""
    run = [
        _make_entry("cross-domain/case-01", "b", integration=5.0),
        _make_entry("cross-domain/case-01", "c", integration=3.0),
    ]
    sc = build_scorecard([run])
    thesis = sc["thesis_gate"]

    assert thesis["result"] == "FAIL"
    assert thesis["margin"] < 0
    assert thesis["failure_analysis"]["classification"] == "arm_c_loss"


# --- self-consistency ---

def test_self_consistency_stable():
    """Three identical runs produce SD = 0."""
    run = [
        _make_entry("cross-domain/case-01", "b"),
        _make_entry("cross-domain/case-01", "c"),
    ]
    sc = build_scorecard([run, run, run])
    assert sc["self_consistency"]["stable"] is True
    assert sc["self_consistency"]["flags"] == []


def test_self_consistency_unstable():
    """Divergent runs produce high SD."""
    run1 = [
        _make_entry("cross-domain/case-01", "b", integration=2.0),
        _make_entry("cross-domain/case-01", "c", integration=2.0),
    ]
    run2 = [
        _make_entry("cross-domain/case-01", "b", integration=5.0),
        _make_entry("cross-domain/case-01", "c", integration=5.0),
    ]
    run3 = [
        _make_entry("cross-domain/case-01", "b", integration=2.0),
        _make_entry("cross-domain/case-01", "c", integration=2.0),
    ]
    sc = build_scorecard([run1, run2, run3])
    assert sc["self_consistency"]["stable"] is False
    assert len(sc["self_consistency"]["flags"]) > 0


# --- per-dimension gap analysis ---

def test_dimension_gaps_reported():
    run = [
        _make_entry("cross-domain/case-01", "b", completeness=4.0, integration=3.0),
        _make_entry("cross-domain/case-01", "c", completeness=4.0, integration=5.0),
    ]
    sc = build_scorecard([run])
    gaps = sc["thesis_gate"]["dimension_gaps"]

    assert gaps["completeness"] == 0.0
    assert gaps["integration"] == 2.0


# --- subset breakdown ---

def test_single_guideline_comparison_informational():
    run = [
        _make_entry("statins/case-01", "b", integration=4.0),
        _make_entry("statins/case-01", "c", integration=4.0),
        _make_entry("cross-domain/case-01", "b", integration=3.0),
        _make_entry("cross-domain/case-01", "c", integration=5.0),
    ]
    sc = build_scorecard([run])
    sg = sc["thesis_gate"].get("single_guideline_comparison")

    assert sg is not None
    assert "arm_b_composite" in sg
    assert "arm_c_composite" in sg


# --- incomplete data ---

def test_thesis_gate_incomplete_without_multi_guideline():
    run = [
        _make_entry("statins/case-01", "b"),
        _make_entry("statins/case-01", "c"),
    ]
    sc = build_scorecard([run])
    assert sc["thesis_gate"]["result"] == "INCOMPLETE"


# --- multiple fixtures per subset ---

def test_scorecard_skips_entries_with_no_scores():
    """Entries with empty or None scores should be silently skipped."""
    run = [
        _make_entry("cross-domain/case-01", "b"),
        _make_entry("cross-domain/case-01", "c"),
        # Entry with no scores (e.g., errored run)
        {
            "fixture": "cross-domain/case-02",
            "arm": "c",
            "composite": 0,
            "scores": {"rubric_scores": {}},
        },
    ]
    sc = build_scorecard([run])
    # Should still build without crashing
    assert sc["n_fixtures"] >= 1


def test_multiple_fixtures_aggregated():
    run = [
        _make_entry("cross-domain/case-01", "b", integration=3.0),
        _make_entry("cross-domain/case-01", "c", integration=5.0),
        _make_entry("cross-domain/case-02", "b", integration=3.0),
        _make_entry("cross-domain/case-02", "c", integration=5.0),
    ]
    sc = build_scorecard([run])
    thesis = sc["thesis_gate"]

    assert thesis["result"] == "PASS"
    # Both fixtures contribute equally
    assert thesis["arm_c_composite"] > thesis["arm_b_composite"]
