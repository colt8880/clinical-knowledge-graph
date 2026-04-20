"""Integration test: run harness fixture discovery and scorecard shape.

Does NOT call real LLMs — tests the harness plumbing:
fixture discovery, cache write/read, scorecard generation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from harness.config import FIXTURES_ROOT
from harness.runner import discover_fixtures, fixture_id, load_fixture


class TestFixtureDiscovery:
    def test_discovers_fixtures_with_expected_actions(self):
        """All 16 fixtures (5 statins + 4 cholesterol + 3 kdigo + 4 cross-domain) should be discoverable."""
        fixtures = discover_fixtures()
        assert len(fixtures) == 16

    def test_fixture_ids_are_readable(self):
        fixtures = discover_fixtures()
        ids = [fixture_id(f) for f in fixtures]
        assert "statins/01-high-risk-55m-smoker" in ids
        assert "statins/05-prior-mi-62m" in ids

    def test_filter_by_fixture_name(self):
        fixtures = discover_fixtures("statins/01-high-risk-55m-smoker")
        assert len(fixtures) == 1
        assert fixtures[0].name == "01-high-risk-55m-smoker"

    def test_filter_by_partial_name(self):
        fixtures = discover_fixtures("statins/01")
        assert len(fixtures) == 1
        assert "01" in fixtures[0].name


class TestLoadFixture:
    def test_loads_patient_and_expected_actions(self):
        fixtures = discover_fixtures("statins/01-high-risk-55m-smoker")
        patient, expected = load_fixture(fixtures[0])

        assert "patient" in patient
        assert "evaluation_time" in patient
        assert "actions" in expected
        assert len(expected["actions"]) > 0

    def test_expected_actions_have_required_fields(self):
        fixtures = discover_fixtures()
        for fix_dir in fixtures:
            _, expected = load_fixture(fix_dir)
            for action in expected["actions"]:
                assert "id" in action, f"Missing id in {fix_dir.name}"
                assert "label" in action, f"Missing label in {fix_dir.name}"
                assert "rationale" in action, f"Missing rationale in {fix_dir.name}"
                assert "priority" in action, f"Missing priority in {fix_dir.name}"

    def test_expected_actions_have_contraindications(self):
        fixtures = discover_fixtures()
        for fix_dir in fixtures:
            _, expected = load_fixture(fix_dir)
            assert "contraindications" in expected, f"Missing contraindications in {fix_dir.name}"


class TestScorecardShape:
    def test_braintrust_logger_formats_scorecard(self):
        from harness.braintrust_client import BraintrustLogger

        logger = BraintrustLogger()
        logger.start_experiment("test")

        # Simulate entries
        for arm_id in ["a", "b", "c"]:
            logger.log_entry(
                fixture_id="statins/01-high-risk",
                arm_id=arm_id,
                patient_context={"patient": {}},
                output={"arm": arm_id, "parsed": {"actions": []}},
                scores={
                    "rubric_scores": {
                        "completeness": {"score": 4},
                        "clinical_appropriateness": {"score": 5},
                        "prioritization": {"score": 3},
                        "integration": {"score": 5},
                        "composite": 4.25,
                    },
                    "structural_checks": {},
                },
                expected_actions={"actions": []},
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("harness.braintrust_client.RESULTS_ROOT", Path(tmpdir)):
                results_dir = logger.finish_experiment()

            assert results_dir is not None
            results_file = results_dir / "results.json"
            assert results_file.exists()

            results = json.loads(results_file.read_text())
            assert results["rubric_version"] == "v1"
            assert len(results["entries"]) == 3
            assert "summary" in results

            # Check summary has per-arm aggregates
            summary = results["summary"]
            assert "a" in summary
            assert "b" in summary
            assert "c" in summary
            assert summary["a"]["mean_scores"]["composite"] == 4.25

            # Check scorecard was written
            scorecard_file = results_dir / "scorecard.txt"
            assert scorecard_file.exists()
            scorecard = scorecard_file.read_text()
            assert "Arm A" in scorecard
            assert "Arm B" in scorecard
            assert "Arm C" in scorecard
