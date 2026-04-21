"""Tests for harness.eval_runner — task functions and scorer integration."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from harness.judge import clinical_scorer, _normalize_score
from harness.scorecard import _denormalize_score


class TestNormalization:
    def test_normalize_1_to_0(self):
        assert _normalize_score(1.0) == 0.0

    def test_normalize_5_to_1(self):
        assert _normalize_score(5.0) == 1.0

    def test_normalize_3_to_05(self):
        assert _normalize_score(3.0) == 0.5

    def test_normalize_clamps_below(self):
        assert _normalize_score(0.0) == 0.0

    def test_normalize_clamps_above(self):
        assert _normalize_score(6.0) == 1.0


class TestDenormalization:
    def test_denormalize_0_to_1(self):
        assert _denormalize_score(0.0) == 1.0

    def test_denormalize_1_to_5(self):
        assert _denormalize_score(1.0) == 5.0

    def test_roundtrip(self):
        for val in [1.0, 2.0, 3.0, 4.0, 5.0, 3.75]:
            assert abs(_denormalize_score(_normalize_score(val)) - val) < 0.001


class TestClinicalScorer:
    @patch("harness.judge.score")
    def test_returns_five_scores(self, mock_score):
        mock_score.return_value = {
            "rubric_version": "v1.1",
            "judge_model": "test",
            "rubric_scores": {
                "completeness": {"score": 4, "rationale": "good"},
                "clinical_appropriateness": {"score": 5, "rationale": "perfect"},
                "prioritization": {"score": 3, "rationale": "ok"},
                "integration": {"score": 5, "rationale": "n/a"},
                "composite": 4.25,
            },
            "structural_checks": {"output_parseable": True},
            "judge_usage": {"input_tokens": 100, "output_tokens": 50},
        }

        result = clinical_scorer(
            input={"patient": {}},
            output={"parsed": {"actions": []}},
            expected={"actions": []},
            metadata={"subset": "single-guideline"},
        )

        assert len(result) == 5
        names = [s["name"] for s in result]
        assert names == ["completeness", "clinical_appropriateness", "prioritization", "integration", "composite"]

    @patch("harness.judge.score")
    def test_scores_normalized_to_0_1(self, mock_score):
        mock_score.return_value = {
            "rubric_version": "v1.1",
            "judge_model": "test",
            "rubric_scores": {
                "completeness": {"score": 5, "rationale": ""},
                "clinical_appropriateness": {"score": 1, "rationale": ""},
                "prioritization": {"score": 3, "rationale": ""},
                "integration": {"score": 5, "rationale": ""},
                "composite": 3.5,
            },
            "structural_checks": {},
            "judge_usage": {"input_tokens": 0, "output_tokens": 0},
        }

        result = clinical_scorer(
            input={}, output={}, expected={},
            metadata={"subset": "single-guideline"},
        )

        for s in result:
            assert 0.0 <= s["score"] <= 1.0, f"{s['name']} score out of range: {s['score']}"

    @patch("harness.judge.score")
    def test_raw_scores_in_metadata(self, mock_score):
        mock_score.return_value = {
            "rubric_version": "v1.1",
            "judge_model": "test",
            "rubric_scores": {
                "completeness": {"score": 4, "rationale": "reason"},
                "clinical_appropriateness": {"score": 4, "rationale": ""},
                "prioritization": {"score": 4, "rationale": ""},
                "integration": {"score": 4, "rationale": ""},
                "composite": 4.0,
            },
            "structural_checks": {},
            "judge_usage": {"input_tokens": 0, "output_tokens": 0},
        }

        result = clinical_scorer(
            input={}, output={}, expected={},
            metadata={"subset": "multi-guideline"},
        )

        completeness = result[0]
        assert completeness["metadata"]["raw_1_5"] == 4
        assert completeness["metadata"]["rationale"] == "reason"

    @patch("harness.judge.score")
    def test_multi_guideline_flag_passed(self, mock_score):
        mock_score.return_value = {
            "rubric_version": "v1.1",
            "judge_model": "test",
            "rubric_scores": {
                "completeness": {"score": 4, "rationale": ""},
                "clinical_appropriateness": {"score": 4, "rationale": ""},
                "prioritization": {"score": 4, "rationale": ""},
                "integration": {"score": 4, "rationale": ""},
                "composite": 4.0,
            },
            "structural_checks": {},
            "judge_usage": {"input_tokens": 0, "output_tokens": 0},
        }

        clinical_scorer(
            input={}, output={}, expected={},
            metadata={"subset": "multi-guideline"},
        )

        mock_score.assert_called_once()
        call_kwargs = mock_score.call_args[1]
        assert call_kwargs["multi_guideline"] is True
