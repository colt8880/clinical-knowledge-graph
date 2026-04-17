"""Unit tests for the judge's deterministic structural checks."""

import pytest

from harness.judge import _structural_checks


class TestStructuralChecks:
    def test_all_expected_actions_present(self):
        arm_output = {
            "parsed": {
                "actions": [
                    {"id": "initiate-statin", "label": "Initiate statin therapy"},
                    {"id": "smoking-cessation", "label": "Smoking cessation"},
                ]
            }
        }
        expected = {
            "actions": [
                {"id": "initiate-statin", "label": "Initiate statin therapy"},
                {"id": "smoking-cessation", "label": "Smoking cessation"},
            ],
            "contraindications": [],
        }

        result = _structural_checks(arm_output, expected)
        assert result["expected_actions_present"] is True
        assert result["output_parseable"] is True

    def test_missing_expected_action(self):
        arm_output = {
            "parsed": {
                "actions": [
                    {"id": "initiate-statin", "label": "Initiate statin therapy"},
                ]
            }
        }
        expected = {
            "actions": [
                {"id": "initiate-statin", "label": "Initiate statin therapy"},
                {"id": "smoking-cessation", "label": "Smoking cessation"},
            ],
            "contraindications": [],
        }

        result = _structural_checks(arm_output, expected)
        assert result["expected_actions_present"] is False

    def test_contraindication_detected(self):
        arm_output = {
            "parsed": {
                "actions": [
                    {"id": "high-intensity-statin", "label": "High-intensity statin"},
                ]
            }
        }
        expected = {
            "actions": [],
            "contraindications": [
                {"id": "high-intensity-statin", "label": "High-intensity statin"},
            ],
        }

        result = _structural_checks(arm_output, expected)
        assert result["contraindications_absent"] is False

    def test_no_contraindications_found(self):
        arm_output = {
            "parsed": {
                "actions": [
                    {"id": "initiate-statin", "label": "Moderate-intensity statin"},
                ]
            }
        }
        expected = {
            "actions": [],
            "contraindications": [
                {"id": "high-intensity-statin", "label": "High-intensity statin"},
            ],
        }

        result = _structural_checks(arm_output, expected)
        assert result["contraindications_absent"] is True

    def test_parse_error_detected(self):
        arm_output = {
            "parsed": {
                "actions": [],
                "_parse_error": True,
            }
        }
        expected = {"actions": [], "contraindications": []}

        result = _structural_checks(arm_output, expected)
        assert result["output_parseable"] is False

    def test_fuzzy_matching_by_substring(self):
        arm_output = {
            "parsed": {
                "actions": [
                    {"id": "statin-init", "label": "Initiate moderate-intensity statin therapy for CVD prevention"},
                ]
            }
        }
        expected = {
            "actions": [
                {"id": "initiate-statin", "label": "moderate-intensity statin"},
            ],
            "contraindications": [],
        }

        result = _structural_checks(arm_output, expected)
        assert result["expected_actions_present"] is True
