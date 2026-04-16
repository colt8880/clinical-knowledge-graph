"""Unit tests for tobacco predicates: smoking_status_is."""

from __future__ import annotations

from app.evaluator.predicates.smoking import eval_smoking_status_is


class TestSmokingStatusIs:
    def test_current_every_day_matches_current(self):
        pc = {"social_history": {"tobacco": {"status": "current_every_day"}}}
        result = eval_smoking_status_is(
            {"values": ["current"]}, pc, {}
        )
        assert result == "true"

    def test_current_some_day_matches_current(self):
        pc = {"social_history": {"tobacco": {"status": "current_some_day"}}}
        result = eval_smoking_status_is(
            {"values": ["current"]}, pc, {}
        )
        assert result == "true"

    def test_never_does_not_match_current(self):
        pc = {"social_history": {"tobacco": {"status": "never"}}}
        result = eval_smoking_status_is(
            {"values": ["current", "current_some_day", "current_every_day"]}, pc, {}
        )
        assert result == "false"

    def test_former_matches_explicit(self):
        pc = {"social_history": {"tobacco": {"status": "former"}}}
        result = eval_smoking_status_is(
            {"values": ["former"]}, pc, {}
        )
        assert result == "true"

    def test_missing_tobacco_returns_unknown(self):
        pc = {"social_history": {}}
        result = eval_smoking_status_is(
            {"values": ["current"]}, pc, {}
        )
        assert result == "unknown"

    def test_missing_social_history_returns_unknown(self):
        pc = {}
        result = eval_smoking_status_is(
            {"values": ["current"]}, pc, {}
        )
        assert result == "unknown"

    def test_never_matches_never(self):
        pc = {"social_history": {"tobacco": {"status": "never"}}}
        result = eval_smoking_status_is(
            {"values": ["never"]}, pc, {}
        )
        assert result == "true"
