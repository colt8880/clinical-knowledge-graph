"""Tests for harness.report — markdown and JSON output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.scorecard import build_scorecard
from harness.report import write_report, write_readme


def _make_entry(fixture: str, arm: str, integration: float = 4.0) -> dict:
    composite = (4.0 + 4.0 + 4.0 + integration) / 4
    return {
        "fixture": fixture,
        "arm": arm,
        "composite": composite,
        "scores": {
            "rubric_scores": {
                "completeness": {"score": 4.0, "rationale": "test"},
                "clinical_appropriateness": {"score": 4.0, "rationale": "test"},
                "prioritization": {"score": 4.0, "rationale": "test"},
                "integration": {"score": integration, "rationale": "test"},
                "composite": composite,
            },
        },
    }


@pytest.fixture
def passing_scorecard():
    run = [
        _make_entry("statins/case-01", "a"),
        _make_entry("statins/case-01", "b"),
        _make_entry("statins/case-01", "c"),
        _make_entry("cross-domain/case-01", "a"),
        _make_entry("cross-domain/case-01", "b", integration=3.0),
        _make_entry("cross-domain/case-01", "c", integration=5.0),
    ]
    return build_scorecard([run], run_name="test-pass")


@pytest.fixture
def failing_scorecard():
    run = [
        _make_entry("cross-domain/case-01", "b", integration=4.0),
        _make_entry("cross-domain/case-01", "c", integration=4.2),
    ]
    return build_scorecard([run], run_name="test-fail")


def test_write_report_creates_files(tmp_path, passing_scorecard):
    md_path, json_path = write_report(passing_scorecard, tmp_path)

    assert md_path.exists()
    assert json_path.exists()
    assert md_path.name == "scorecard.md"
    assert json_path.name == "scorecard.json"


def test_scorecard_md_contains_thesis_gate(tmp_path, passing_scorecard):
    md_path, _ = write_report(passing_scorecard, tmp_path)
    content = md_path.read_text()

    assert "THESIS GATE: PASS" in content
    assert "Arm C beats Arm B" in content


def test_scorecard_md_contains_failure_analysis(tmp_path, failing_scorecard):
    md_path, _ = write_report(failing_scorecard, tmp_path)
    content = md_path.read_text()

    assert "THESIS GATE: FAIL" in content
    assert "Failure analysis" in content


def test_scorecard_json_is_valid(tmp_path, passing_scorecard):
    _, json_path = write_report(passing_scorecard, tmp_path)
    data = json.loads(json_path.read_text())

    assert data["thesis_gate"]["result"] == "PASS"
    assert "fixture_scores" in data
    assert "arm_subset_summary" in data


def test_scorecard_json_roundtrips(tmp_path, passing_scorecard):
    _, json_path = write_report(passing_scorecard, tmp_path)
    data = json.loads(json_path.read_text())

    # All values should be JSON-serializable (no custom types)
    reserialized = json.dumps(data)
    assert json.loads(reserialized) == data


def test_write_readme(tmp_path, passing_scorecard):
    readme_path = write_readme(
        passing_scorecard, tmp_path,
        commit_sha="abc1234",
        braintrust_url="https://braintrust.dev/experiment/123",
    )

    assert readme_path.exists()
    content = readme_path.read_text()
    assert "abc1234" in content
    assert "THESIS GATE: PASS" in content
    assert "braintrust.dev" in content


def test_write_readme_no_braintrust(tmp_path, passing_scorecard):
    readme_path = write_readme(passing_scorecard, tmp_path, commit_sha="abc1234")
    content = readme_path.read_text()

    assert "abc1234" in content
    # No Braintrust experiment URL should appear when none was provided
    assert "braintrust.dev" not in content


def test_scorecard_md_has_per_fixture_table(tmp_path, passing_scorecard):
    md_path, _ = write_report(passing_scorecard, tmp_path)
    content = md_path.read_text()

    assert "Per-fixture scores" in content
    assert "statins/case-01" in content
    assert "cross-domain/case-01" in content


def test_scorecard_md_has_dimension_breakdown(tmp_path, passing_scorecard):
    md_path, _ = write_report(passing_scorecard, tmp_path)
    content = md_path.read_text()

    assert "Per-dimension breakdown" in content
    assert "completeness" in content
    assert "integration" in content
