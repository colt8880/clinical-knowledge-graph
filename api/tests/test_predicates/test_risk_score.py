"""Unit tests for risk score predicates: risk_score_compares."""

from __future__ import annotations

from app.evaluator.predicates.risk_score import eval_risk_score_compares


class TestRiskScoreCompares:
    def test_gte_threshold_true(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 18.2}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "gte", "threshold": 10}, pc, {}
        )
        assert result == "true"

    def test_gte_threshold_false(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 8.4}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "gte", "threshold": 10}, pc, {}
        )
        assert result == "false"

    def test_lt_threshold_true(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 8.4}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "lt", "threshold": 10}, pc, {}
        )
        assert result == "true"

    def test_lt_threshold_false(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 18.2}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "lt", "threshold": 10}, pc, {}
        )
        assert result == "false"

    def test_missing_score_returns_unknown(self):
        pc = {"risk_scores": {}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "gte", "threshold": 10}, pc, {}
        )
        assert result == "unknown"

    def test_no_risk_scores_at_all_returns_unknown(self):
        pc = {}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "gte", "threshold": 10}, pc, {}
        )
        assert result == "unknown"

    def test_gte_boundary_exact(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 7.5}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "gte", "threshold": 7.5}, pc, {}
        )
        assert result == "true"

    def test_eq_comparator(self):
        pc = {"risk_scores": {"ascvd_10yr": {"value": 10.0}}}
        result = eval_risk_score_compares(
            {"name": "ascvd_10yr", "comparator": "eq", "threshold": 10.0}, pc, {}
        )
        assert result == "true"
