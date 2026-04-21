"""Tests for harness.fixtures — fixture discovery, loading, and dataset building."""

import json
from pathlib import Path

import pytest

from harness.fixtures import (
    classify_fixture,
    discover_fixtures,
    fixture_id,
    load_dataset,
    load_fixture,
)


class TestFixtureDiscovery:
    def test_discovers_all_fixtures(self):
        """All 16 fixtures (5 statins + 4 cholesterol + 3 kdigo + 4 cross-domain) should be discoverable."""
        fixtures = discover_fixtures()
        assert len(fixtures) == 16

    def test_fixture_ids_are_readable(self):
        fixtures = discover_fixtures()
        ids = [fixture_id(f) for f in fixtures]
        assert "statins/01-high-risk-55m-smoker" in ids
        assert "statins/05-prior-mi-62m" in ids
        assert "cross-domain/case-01" in ids

    def test_filter_by_fixture_name(self):
        fixtures = discover_fixtures("statins/01-high-risk-55m-smoker")
        assert len(fixtures) == 1
        assert fixtures[0].name == "01-high-risk-55m-smoker"

    def test_filter_by_partial_name(self):
        fixtures = discover_fixtures("statins/01")
        assert len(fixtures) == 1
        assert "01" in fixtures[0].name

    def test_filter_by_guideline(self):
        fixtures = discover_fixtures("_guideline:cholesterol")
        assert len(fixtures) == 4

    def test_filter_by_guideline_cross_domain(self):
        fixtures = discover_fixtures("_guideline:cross-domain")
        assert len(fixtures) == 4


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


class TestClassifyFixture:
    def test_single_guideline(self):
        assert classify_fixture("statins/case-01") == "single-guideline"
        assert classify_fixture("cholesterol/case-01") == "single-guideline"
        assert classify_fixture("kdigo/case-01") == "single-guideline"

    def test_multi_guideline(self):
        assert classify_fixture("cross-domain/case-01") == "multi-guideline"


class TestLoadDataset:
    def test_returns_braintrust_shape(self):
        dataset = load_dataset()
        assert len(dataset) == 16

        for entry in dataset:
            assert "input" in entry
            assert "expected" in entry
            assert "metadata" in entry
            assert "fixture_id" in entry["metadata"]
            assert "subset" in entry["metadata"]
            assert entry["metadata"]["subset"] in ("single-guideline", "multi-guideline")

    def test_multi_guideline_count(self):
        dataset = load_dataset()
        multi = [d for d in dataset if d["metadata"]["subset"] == "multi-guideline"]
        assert len(multi) == 4

    def test_filter_works(self):
        dataset = load_dataset("_guideline:statins")
        assert len(dataset) == 5
        assert all(d["metadata"]["guideline"] == "statins" for d in dataset)
