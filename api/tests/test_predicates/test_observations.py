"""Unit tests for observation predicates: most_recent_observation_value."""

from __future__ import annotations

from app.evaluator.predicates.observations import eval_most_recent_observation_value
from app.evaluator.graph import ClinicalEntity, CodeRef


def _make_entities() -> dict:
    return {
        "obs:ldl-cholesterol": ClinicalEntity(
            id="obs:ldl-cholesterol",
            label="Observation",
            display_name="LDL Cholesterol",
            codes=[CodeRef("loinc", "13457-7"), CodeRef("loinc", "2089-1")],
        ),
    }


def _patient_with_obs(observations: list[dict]) -> dict:
    return {
        "evaluation_time": "2026-04-15T10:00:00Z",
        "observations": observations,
    }


class TestMostRecentObservationValue:
    def test_gte_threshold_true(self):
        pc = _patient_with_obs([{
            "id": "obs1",
            "codes": [{"system": "loinc", "code": "13457-7"}],
            "status": "final",
            "effective_date": "2026-02-01T09:00:00Z",
            "value": {"value_quantity": {"value": 200, "unit": "mg/dL"}},
        }])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "true"

    def test_below_threshold_false(self):
        pc = _patient_with_obs([{
            "id": "obs1",
            "codes": [{"system": "loinc", "code": "13457-7"}],
            "status": "final",
            "effective_date": "2026-02-01T09:00:00Z",
            "value": {"value_quantity": {"value": 150, "unit": "mg/dL"}},
        }])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "false"

    def test_no_matching_observation_returns_false(self):
        pc = _patient_with_obs([])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "false"

    def test_outside_window_returns_false(self):
        pc = _patient_with_obs([{
            "id": "obs1",
            "codes": [{"system": "loinc", "code": "13457-7"}],
            "status": "final",
            "effective_date": "2020-01-01T09:00:00Z",
            "value": {"value_quantity": {"value": 200, "unit": "mg/dL"}},
        }])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "false"

    def test_preliminary_status_excluded(self):
        pc = _patient_with_obs([{
            "id": "obs1",
            "codes": [{"system": "loinc", "code": "13457-7"}],
            "status": "preliminary",
            "effective_date": "2026-02-01T09:00:00Z",
            "value": {"value_quantity": {"value": 200, "unit": "mg/dL"}},
        }])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "false"

    def test_tiebreaker_by_id(self):
        """When two observations share effective_date, lexicographic id tiebreak (per docs/ISSUES.md)."""
        pc = _patient_with_obs([
            {
                "id": "obs-a",
                "codes": [{"system": "loinc", "code": "13457-7"}],
                "status": "final",
                "effective_date": "2026-02-01T09:00:00Z",
                "value": {"value_quantity": {"value": 150, "unit": "mg/dL"}},
            },
            {
                "id": "obs-b",
                "codes": [{"system": "loinc", "code": "13457-7"}],
                "status": "final",
                "effective_date": "2026-02-01T09:00:00Z",
                "value": {"value_quantity": {"value": 200, "unit": "mg/dL"}},
            },
        ])
        # obs-b comes last lexicographically and should win the tiebreak
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "gte", "threshold": 190, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "true"

    def test_lt_comparator(self):
        pc = _patient_with_obs([{
            "id": "obs1",
            "codes": [{"system": "loinc", "code": "13457-7"}],
            "status": "final",
            "effective_date": "2026-02-01T09:00:00Z",
            "value": {"value_quantity": {"value": 8.4, "unit": "mg/dL"}},
        }])
        result = eval_most_recent_observation_value(
            {"code": "obs:ldl-cholesterol", "window": "P2Y", "comparator": "lt", "threshold": 10, "unit": "mg/dL"},
            pc, _make_entities(),
        )
        assert result == "true"
