"""Unit tests for condition predicates: has_condition_history, has_active_condition."""

from __future__ import annotations

from app.evaluator.predicates.conditions import eval_has_condition_history, eval_has_active_condition
from app.evaluator.graph import ClinicalEntity, CodeRef


def _make_entities() -> dict:
    """Build a minimal entities dict with HTN and ASCVD."""
    return {
        "cond:hypertension": ClinicalEntity(
            id="cond:hypertension",
            label="Condition",
            display_name="Essential hypertension",
            codes=[CodeRef("snomed", "38341003"), CodeRef("icd10", "I10")],
        ),
        "cond:ascvd-established": ClinicalEntity(
            id="cond:ascvd-established",
            label="Condition",
            display_name="Established ASCVD",
            codes=[CodeRef("snomed", "22298006"), CodeRef("icd10", "I21")],
        ),
    }


def _patient_with_conditions(conditions: list[dict]) -> dict:
    return {"conditions": conditions}


class TestHasConditionHistory:
    def test_confirmed_active_matches(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "active",
            "verification_status": "confirmed",
        }])
        result = eval_has_condition_history(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_confirmed_resolved_matches(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "resolved",
            "verification_status": "confirmed",
        }])
        result = eval_has_condition_history(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_unconfirmed_does_not_match(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "active",
            "verification_status": "unconfirmed",
        }])
        result = eval_has_condition_history(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "false"

    def test_no_conditions_returns_false(self):
        pc = _patient_with_conditions([])
        result = eval_has_condition_history(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "false"

    def test_wrong_code_returns_false(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "999999"}],
            "clinical_status": "active",
            "verification_status": "confirmed",
        }])
        result = eval_has_condition_history(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "false"


class TestHasActiveCondition:
    def test_active_matches(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "active",
            "verification_status": "confirmed",
        }])
        result = eval_has_active_condition(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_recurrence_matches(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "recurrence",
            "verification_status": "confirmed",
        }])
        result = eval_has_active_condition(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "true"

    def test_resolved_does_not_match_active(self):
        pc = _patient_with_conditions([{
            "id": "c1",
            "codes": [{"system": "snomed", "code": "38341003"}],
            "clinical_status": "resolved",
            "verification_status": "confirmed",
        }])
        result = eval_has_active_condition(
            {"codes": ["cond:hypertension"]}, pc, _make_entities()
        )
        assert result == "false"
